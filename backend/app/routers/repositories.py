from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import get_settings
from app.db import get_db
from app.services.github import GitHubClient

router = APIRouter(prefix="/repositories", tags=["repositories"])


class SyncBody(BaseModel):
    user_id: str
    access_token: str


class ConnectBody(BaseModel):
    user_id: str


@router.post("/sync")
async def sync_repos(body: SyncBody):
    """
    Upsert the user's GitHub repos into DB. Called by frontend after OAuth.
    """
    db = get_db()
    gh = GitHubClient(token=body.access_token)
    gh_repos = await gh.list_user_repos()

    existing = await db.user.find_unique(where={"id": body.user_id})
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")

    await db.user.update(
        where={"id": body.user_id},
        data={"accessToken": body.access_token},
    )

    for r in gh_repos:
        await db.repository.upsert(
            where={"githubId": r["id"]},
            data={
                "create": {
                    "githubId": r["id"],
                    "owner": r["owner"]["login"],
                    "name": r["name"],
                    "fullName": r["full_name"],
                    "private": r.get("private", False),
                    "connected": False,
                    "userId": body.user_id,
                },
                "update": {
                    "owner": r["owner"]["login"],
                    "name": r["name"],
                    "fullName": r["full_name"],
                    "private": r.get("private", False),
                    "userId": body.user_id,
                },
            },
        )
    return {"ok": True, "count": len(gh_repos)}


@router.get("")
async def list_repos(user_id: str):
    db = get_db()
    rows = await db.repository.find_many(
        where={"userId": user_id},
        order={"updatedAt": "desc"},
    )
    return {
        "items": [
            {
                "id": r.id,
                "full_name": r.fullName,
                "owner": r.owner,
                "name": r.name,
                "private": r.private,
                "connected": r.connected,
                "webhook_id": r.webhookId,
            }
            for r in rows
        ]
    }


@router.post("/{repo_id}/connect")
async def connect_repo(repo_id: str, body: ConnectBody):
    db = get_db()
    settings = get_settings()

    r = await db.repository.find_unique(where={"id": repo_id})
    if not r or r.userId != body.user_id:
        raise HTTPException(status_code=404, detail="Repository not found")

    user = await db.user.find_unique(where={"id": body.user_id})
    if not user or not user.accessToken:
        raise HTTPException(status_code=400, detail="User has no access token")

    gh = GitHubClient(token=user.accessToken)
    try:
        hook = await gh.create_webhook(
            r.owner,
            r.name,
            webhook_url=settings.public_webhook_url,
            secret=settings.github_webhook_secret,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"GitHub webhook create failed: {e}")

    await db.repository.update(
        where={"id": repo_id},
        data={"connected": True, "webhookId": hook.get("id")},
    )
    return {"ok": True, "webhook_id": hook.get("id")}


@router.post("/{repo_id}/disconnect")
async def disconnect_repo(repo_id: str, body: ConnectBody):
    db = get_db()
    r = await db.repository.find_unique(where={"id": repo_id})
    if not r or r.userId != body.user_id:
        raise HTTPException(status_code=404, detail="Repository not found")

    user = await db.user.find_unique(where={"id": body.user_id})
    if user and user.accessToken and r.webhookId:
        try:
            gh = GitHubClient(token=user.accessToken)
            await gh.delete_webhook(r.owner, r.name, int(r.webhookId))
        except Exception:
            pass

    await db.repository.update(
        where={"id": repo_id},
        data={"connected": False, "webhookId": None},
    )
    return {"ok": True}
