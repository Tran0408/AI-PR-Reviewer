from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import get_settings

log = logging.getLogger(__name__)


@dataclass
class PullRequest:
    owner: str
    repo: str
    number: int
    title: str
    body: str | None
    author: str
    head_sha: str
    html_url: str


class GitHubClient:
    """
    Async GitHub REST client. Uses a PAT or installation token provided at construction.
    """

    def __init__(self, token: str, base_url: str | None = None) -> None:
        self.token = token
        self.base_url = (base_url or get_settings().github_api_base).rstrip("/")

    def _headers(self, accept: str = "application/vnd.github+json") -> dict[str, str]:
        return {
            "Accept": accept,
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ai-pr-reviewer/1.0",
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True,
    )
    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any | None = None,
        accept: str = "application/vnd.github+json",
    ) -> httpx.Response:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.request(
                method,
                f"{self.base_url}{path}",
                headers=self._headers(accept),
                json=json,
            )
            if resp.status_code >= 400:
                log.error("GitHub %s %s -> %s: %s", method, path, resp.status_code, resp.text[:500])
            resp.raise_for_status()
            return resp

    async def get_pull_request(self, owner: str, repo: str, number: int) -> PullRequest:
        r = await self._request("GET", f"/repos/{owner}/{repo}/pulls/{number}")
        d = r.json()
        return PullRequest(
            owner=owner,
            repo=repo,
            number=number,
            title=d["title"],
            body=d.get("body"),
            author=d["user"]["login"],
            head_sha=d["head"]["sha"],
            html_url=d["html_url"],
        )

    async def get_pr_diff(self, owner: str, repo: str, number: int) -> str:
        r = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/pulls/{number}",
            accept="application/vnd.github.v3.diff",
        )
        return r.text

    async def post_review(
        self,
        owner: str,
        repo: str,
        number: int,
        *,
        commit_id: str,
        body: str,
        event: str,  # "APPROVE" | "REQUEST_CHANGES" | "COMMENT"
        comments: list[dict[str, Any]],
    ) -> dict[str, Any]:
        payload = {
            "commit_id": commit_id,
            "body": body,
            "event": event,
            "comments": comments,
        }
        r = await self._request(
            "POST",
            f"/repos/{owner}/{repo}/pulls/{number}/reviews",
            json=payload,
        )
        return r.json()

    async def list_user_repos(self, *, per_page: int = 100) -> list[dict[str, Any]]:
        repos: list[dict[str, Any]] = []
        page = 1
        while True:
            r = await self._request(
                "GET",
                f"/user/repos?per_page={per_page}&page={page}&sort=updated&affiliation=owner,collaborator",
            )
            batch = r.json()
            if not batch:
                break
            repos.extend(batch)
            if len(batch) < per_page:
                break
            page += 1
            if page > 10:
                break
        return repos

    async def create_webhook(
        self,
        owner: str,
        repo: str,
        *,
        webhook_url: str,
        secret: str,
        events: list[str] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "name": "web",
            "active": True,
            "events": events or ["pull_request"],
            "config": {
                "url": webhook_url,
                "content_type": "json",
                "secret": secret,
                "insecure_ssl": "0",
            },
        }
        r = await self._request("POST", f"/repos/{owner}/{repo}/hooks", json=payload)
        return r.json()

    async def delete_webhook(self, owner: str, repo: str, hook_id: int) -> None:
        await self._request("DELETE", f"/repos/{owner}/{repo}/hooks/{hook_id}")


def map_assessment_to_event(assessment: str) -> str:
    return {
        "approve": "APPROVE",
        "request_changes": "REQUEST_CHANGES",
        "comment": "COMMENT",
    }.get(assessment, "COMMENT")
