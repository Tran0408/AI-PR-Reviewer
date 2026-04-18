from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Provider
    review_provider: Literal["mock", "openrouter"] = "mock"
    openrouter_api_key: str | None = None
    openrouter_model: str = "qwen/qwen-2.5-coder-32b-instruct:free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # GitHub
    github_client_id: str | None = None
    github_client_secret: str | None = None
    github_webhook_secret: str = "change-me"
    github_api_base: str = "https://api.github.com"
    public_webhook_url: str = "http://localhost:8000/webhooks/github"

    # Infra
    database_url: str = "postgresql://postgres:postgres@localhost:5432/prreviewer"
    redis_url: str = "redis://localhost:6379/0"

    # Tuning
    diff_max_chars: int = Field(default=32000, ge=1000)
    llm_max_retries: int = 2
    llm_timeout_seconds: float = 90.0
    log_level: str = "INFO"

    # CORS
    frontend_origin: str = "http://localhost:3000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
