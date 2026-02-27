from redis.asyncio import Redis

from runledger_api.core.config import settings

# Module-level client — connects lazily on first use
redis_client: Redis = Redis.from_url(
    settings.redis_url,
    encoding="utf-8",
    decode_responses=True,
)


async def get_redis() -> Redis:
    return redis_client
