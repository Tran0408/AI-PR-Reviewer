from app.config import get_settings
from app.services.review.base import ReviewProvider
from app.services.review.mock import MockProvider
from app.services.review.openrouter import OpenRouterProvider


def get_provider() -> ReviewProvider:
    settings = get_settings()
    if settings.review_provider == "openrouter":
        if not settings.openrouter_api_key:
            raise RuntimeError("OPENROUTER_API_KEY not set but REVIEW_PROVIDER=openrouter")
        return OpenRouterProvider(
            api_key=settings.openrouter_api_key,
            model=settings.openrouter_model,
            base_url=settings.openrouter_base_url,
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )
    return MockProvider()
