from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.db import get_db
from app.services.github import GitHubClient

router = APIRouter(prefix="/reviews", tags=["reviews"])


class MergeBody(BaseModel):
    user_id: str
    method: str = "merge"  # merge | squash | rebase


@router.get("")
async def list_reviews(
    repository_id: str | None = Query(default=None),
    assessment: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    db = get_db()
    where: dict = {}
    if repository_id:
        where["repositoryId"] = repository_id
    if assessment in ("approve", "request_changes", "comment"):
        where["assessment"] = assessment
    if user_id:
        where["repository"] = {"is": {"userId": user_id}}

    items = await db.review.find_many(
        where=where or None,
        take=limit,
        skip=offset,
        order={"createdAt": "desc"},
        include={"repository": True},
    )
    total = await db.review.count(where=where or None)

    return {
        "items": [_serialize(r) for r in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{review_id}")
async def get_review(review_id: str):
    db = get_db()
    r = await db.review.find_unique(
        where={"id": review_id},
        include={"repository": True},
    )
    if not r:
        raise HTTPException(status_code=404, detail="Review not found")
    return _serialize(r, full=True)


@router.get("/{review_id}/pr-details")
async def get_pr_details(review_id: str, user_id: str = Query(...)):
    db = get_db()
    r = await db.review.find_unique(
        where={"id": review_id}, include={"repository": True}
    )
    if not r or not r.repository or r.repository.userId != user_id:
        raise HTTPException(status_code=404, detail="Review not found")

    user = await db.user.find_unique(where={"id": user_id})
    if not user or not user.accessToken:
        raise HTTPException(status_code=400, detail="User has no access token")

    gh = GitHubClient(token=user.accessToken)
    try:
        pr = await gh.get_pr_full(r.repository.owner, r.repository.name, r.prNumber)
        files = await gh.list_pr_files(r.repository.owner, r.repository.name, r.prNumber)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"GitHub fetch failed: {e}")

    return {
        "pr_author": pr.get("user", {}).get("login"),
        "pr_author_avatar": pr.get("user", {}).get("avatar_url"),
        "state": pr.get("state"),
        "merged": pr.get("merged", False),
        "mergeable": pr.get("mergeable"),
        "mergeable_state": pr.get("mergeable_state"),
        "base_ref": pr.get("base", {}).get("ref"),
        "head_ref": pr.get("head", {}).get("ref"),
        "additions": pr.get("additions", 0),
        "deletions": pr.get("deletions", 0),
        "changed_files": pr.get("changed_files", 0),
        "files": [
            {
                "filename": f.get("filename"),
                "status": f.get("status"),
                "additions": f.get("additions", 0),
                "deletions": f.get("deletions", 0),
                "blob_url": f.get("blob_url"),
            }
            for f in files
        ],
    }


@router.post("/{review_id}/merge")
async def merge_review_pr(review_id: str, body: MergeBody):
    if body.method not in ("merge", "squash", "rebase"):
        raise HTTPException(status_code=400, detail="Invalid merge method")

    db = get_db()
    r = await db.review.find_unique(
        where={"id": review_id}, include={"repository": True}
    )
    if not r or not r.repository or r.repository.userId != body.user_id:
        raise HTTPException(status_code=404, detail="Review not found")

    user = await db.user.find_unique(where={"id": body.user_id})
    if not user or not user.accessToken:
        raise HTTPException(status_code=400, detail="User has no access token")

    gh = GitHubClient(token=user.accessToken)
    try:
        result = await gh.merge_pr(
            r.repository.owner,
            r.repository.name,
            r.prNumber,
            method=body.method,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Merge failed: {e}")

    return {"ok": True, "merged": result.get("merged", False), "sha": result.get("sha")}


def _serialize(r, full: bool = False) -> dict:
    base = {
        "id": r.id,
        "repository_id": r.repositoryId,
        "repository_full_name": r.repository.fullName if r.repository else None,
        "pr_number": r.prNumber,
        "pr_title": r.prTitle,
        "pr_author": r.prAuthor,
        "pr_url": r.prUrl,
        "commit_sha": r.commitSha,
        "score": r.score,
        "assessment": r.assessment,
        "summary": r.summary,
        "posted_to_github": r.postedToGithub,
        "error": r.error,
        "created_at": r.createdAt.isoformat(),
    }
    if full:
        base["payload"] = r.payload
    return base
