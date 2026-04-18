from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.db import get_db

router = APIRouter(prefix="/reviews", tags=["reviews"])


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
