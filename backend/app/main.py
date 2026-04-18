from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import connect, disconnect
from app.routers import repositories, reviews, users, webhooks

logging.basicConfig(
    level=get_settings().log_level,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await connect()
    yield
    await disconnect()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="AI PR Reviewer API",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(webhooks.router)
    app.include_router(reviews.router)
    app.include_router(repositories.router)
    app.include_router(users.router)

    @app.get("/health")
    async def health():
        return {"status": "ok", "provider": settings.review_provider}

    @app.get("/")
    async def root():
        return {"service": "ai-pr-reviewer", "docs": "/docs"}

    return app


app = create_app()
