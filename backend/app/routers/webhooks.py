from __future__ import annotations

import json
import logging

from arq import create_pool
from fastapi import APIRouter, Header, HTTPException, Request, status

from app.config import get_settings
from app.db import get_db
from app.queue.redis_settings import redis_settings_from_url
from app.utils.crypto import verify_github_signature

log = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

RELEVANT_ACTIONS = {"opened", "synchronize", "reopened", "ready_for_review"}


@router.post("/github", status_code=status.HTTP_200_OK)
async def github_webhook(
    request: Request,
    x_github_event: str | None = Header(default=None),
    x_hub_signature_256: str | None = Header(default=None),
    x_github_delivery: str | None = Header(default=None),
):
    settings = get_settings()
    body = await request.body()

    if not verify_github_signature(settings.github_webhook_secret, body, x_hub_signature_256):
        log.warning("Invalid webhook signature (delivery=%s)", x_github_delivery)
        raise HTTPException(status_code=401, detail="Invalid signature")

    if x_github_event == "ping":
        return {"ok": True, "pong": True}

    if x_github_event != "pull_request":
        return {"ok": True, "ignored": x_github_event}

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    action = payload.get("action")
    if action not in RELEVANT_ACTIONS:
        return {"ok": True, "ignored_action": action}

    pr = payload.get("pull_request") or {}
    repo = payload.get("repository") or {}

    repo_full_name = repo.get("full_name")
    pr_number = pr.get("number")
    head_sha = (pr.get("head") or {}).get("sha")
    if not (repo_full_name and pr_number and head_sha):
        raise HTTPException(status_code=400, detail="Malformed pull_request payload")

    db = get_db()
    db_repo = await db.repository.find_unique(where={"fullName": repo_full_name})
    if db_repo is None or not db_repo.connected:
        return {"ok": True, "ignored_repo": repo_full_name}

    user = await db.user.find_unique(where={"id": db_repo.userId})
    installation_token = user.accessToken if user else None
    if not installation_token:
        log.error("No access token for user behind %s", repo_full_name)
        return {"ok": True, "warning": "no_token"}

    pool = await create_pool(redis_settings_from_url(settings.redis_url))
    try:
        await pool.enqueue_job(
            "process_pr_event",
            {
                "repo_full_name": repo_full_name,
                "pr_number": pr_number,
                "commit_sha": head_sha,
                "pr_title": pr.get("title", ""),
                "pr_body": pr.get("body"),
                "pr_author": (pr.get("user") or {}).get("login", "unknown"),
                "pr_url": pr.get("html_url", ""),
                "repository_id": db_repo.id,
                "installation_token": installation_token,
            },
            _job_id=f"pr:{repo_full_name}:{pr_number}:{head_sha}",
        )
    finally:
        await pool.close()

    return {"ok": True, "enqueued": True}
