from urllib.parse import urlparse

from arq.connections import RedisSettings


def redis_settings_from_url(url: str) -> RedisSettings:
    """
    arq's RedisSettings.from_dsn does not support rediss:// (TLS).
    Parse the URL manually and set ssl=True when needed.
    """
    u = urlparse(url)
    scheme = (u.scheme or "redis").lower()
    if scheme not in ("redis", "rediss"):
        raise ValueError(f"Unsupported redis scheme: {scheme}")
    database = 0
    if u.path and u.path.strip("/"):
        try:
            database = int(u.path.strip("/"))
        except ValueError:
            database = 0
    return RedisSettings(
        host=u.hostname or "localhost",
        port=u.port or 6379,
        username=u.username or None,
        password=u.password or None,
        database=database,
        ssl=(scheme == "rediss"),
    )
