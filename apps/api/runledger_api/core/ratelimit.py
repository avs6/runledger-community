"""
Tiered Redis sliding-window rate limiter.

Key format: rl:ratelimit:{tier}:{token[:16]}:{epoch_minute}

Fail open: any Redis exception is caught and the request is allowed through.
"""

from __future__ import annotations

import time

import structlog
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from runledger_api.core.redis import get_redis

log = structlog.get_logger()

_bearer = HTTPBearer(auto_error=False)

try:
    from redis.asyncio import Redis
except ImportError:
    Redis = object  # type: ignore[misc,assignment]

_LIMITS: dict[str, int] = {
    "ingest": 600,
    "analytics": 120,
    "management": 60,
}


async def _check_rate_limit(tier: str, request: Request, redis: Redis) -> None:
    credentials: HTTPAuthorizationCredentials | None = await _bearer(request)
    token = credentials.credentials if credentials else (request.client.host if request.client else "anon")
    token_key = token[:16]
    epoch_minute = int(time.time() // 60)
    key = f"rl:ratelimit:{tier}:{token_key}:{epoch_minute}"
    limit = _LIMITS[tier]

    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 60)
        if count > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": "60"},
            )
    except HTTPException:
        raise
    except Exception as exc:
        log.warning("rate_limit_redis_error", tier=tier, error=str(exc))
        # Fail open — do not block the request on Redis failure


async def ingest_rate_limit(
    request: Request,
    redis: Redis = Depends(get_redis),
) -> None:
    """600 requests/min per API key — high-volume ingest."""
    await _check_rate_limit("ingest", request, redis)


async def analytics_rate_limit(
    request: Request,
    redis: Redis = Depends(get_redis),
) -> None:
    """120 requests/min per API key — analytics queries."""
    await _check_rate_limit("analytics", request, redis)


async def management_rate_limit(
    request: Request,
    redis: Redis = Depends(get_redis),
) -> None:
    """60 requests/min per API key — CRUD management endpoints."""
    await _check_rate_limit("management", request, redis)
