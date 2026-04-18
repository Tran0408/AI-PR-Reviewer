from arq.connections import RedisSettings

from app.config import get_settings
from app.db import connect, disconnect
from app.queue.redis_settings import redis_settings_from_url
from app.queue.tasks import process_pr_event


def _redis_settings() -> RedisSettings:
    return redis_settings_from_url(get_settings().redis_url)


async def startup(ctx: dict) -> None:
    await connect()


async def shutdown(ctx: dict) -> None:
    await disconnect()


class WorkerSettings:
    functions = [process_pr_event]
    redis_settings = _redis_settings()
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 5
    job_timeout = 300
    keep_result = 3600
