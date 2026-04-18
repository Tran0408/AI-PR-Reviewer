from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db import get_db

router = APIRouter(prefix="/users", tags=["users"])


class UpsertUserBody(BaseModel):
    github_id: str
    login: str
    email: str | None = None
    avatar_url: str | None = None
    access_token: str | None = None


@router.post("/upsert")
async def upsert_user(body: UpsertUserBody):
    """
    Idempotent user upsert. Called by NextAuth signIn callback.
    """
    db = get_db()
    user = await db.user.upsert(
        where={"githubId": body.github_id},
        data={
            "create": {
                "githubId": body.github_id,
                "login": body.login,
                "email": body.email,
                "avatarUrl": body.avatar_url,
                "accessToken": body.access_token,
            },
            "update": {
                "login": body.login,
                "email": body.email,
                "avatarUrl": body.avatar_url,
                "accessToken": body.access_token,
            },
        },
    )
    return {
        "id": user.id,
        "github_id": user.githubId,
        "login": user.login,
        "email": user.email,
        "avatar_url": user.avatarUrl,
    }


@router.get("/{user_id}")
async def get_user(user_id: str):
    db = get_db()
    u = await db.user.find_unique(where={"id": user_id})
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": u.id,
        "github_id": u.githubId,
        "login": u.login,
        "email": u.email,
        "avatar_url": u.avatarUrl,
    }
