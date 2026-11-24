"""
Tiered Redis sliding-window rate limiter (review P-17).

Each request is counted in a Redis sorted set scored by its timestamp; members older
than the 60-second window are trimmed before counting, so a burst at a minute boundary
can't get twice the limit the way the old fixed epoch-minute bucket allowed.

Identity (the "who" a limit applies to):
  * an authenticated caller is keyed by its API key id when the auth dependency has
    already resolved it (``request.state.api_key``, cached by core/deps), otherwise by a SHA-256 digest
    of the bearer token. Never by the token prefix: every dev key starts ``rl_dev_``,
    so the old ``token[:16]`` key lumped unrelated keys into one bucket.
  * an anonymous caller is keyed by its client IP, resolved through TRUSTED_PROXIES
    (rightmost untrusted X-Forwarded-For hop), so one proxy's address isn't shared by
    every user behind it and a client can't spoof its own address.

Key format: rl:ratelimit:{tier}:{identity}

Fail open: any Redis exception is caught and the request is allowed through.

Rate limit info is stored on request.state for the RateLimitHeaderMiddleware
to inject X-RateLimit-* response headers.
"""

from __future__ import annotations

import hashlib
import time
import uuid

import structlog
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from runledger_api.core.config import settings
from runledger_api.core.redis import get_redis

log = structlog.get_logger()

_bearer = HTTPBearer(auto_error=False)

WINDOW_SECONDS = 60

try:
    from redis.asyncio import Redis
except ImportError:
    Redis = object  # type: ignore[misc,assignment]


def _limits() -> dict[str, int]:
    return {
        "ingest": settings.ingest_rate_limit_per_minute,
        "analytics": settings.analytics_rate_limit_per_minute,
        "management": settings.management_rate_limit_per_minute,
        "system": settings.system_rate_limit_per_minute,
    }


async def rate_limit_identity(request: Request) -> str:
    """Stable identity for the caller: ``key:<id>``, ``tok:<digest>`` or ``ip:<addr>``."""
    key_id = getattr(request.state, "api_key_id", None)
    cached_key = getattr(request.state, "api_key", None)
    if not key_id and cached_key is not None:
        key_id = getattr(cached_key, "id", None)
    if key_id:
        return f"key:{key_id}"
    credentials: HTTPAuthorizationCredentials | None = await _bearer(request)
    if credentials and credentials.credentials:
        digest = hashlib.sha256(credentials.credentials.encode()).hexdigest()[:32]
        return f"tok:{digest}"
    from runledger_api.services.security import get_client_ip  # noqa: PLC0415

    ip = get_client_ip(
        request.headers.get("x-forwarded-for"),
        request.client.host if request.client else None,
    )
    return f"ip:{ip or 'anon'}"


async def sliding_window_hit(
    redis: Redis, key: str, limit: int, now: float | None = None
) -> tuple[int, float]:
    """Record one hit and return ``(count_in_window, oldest_hit_ts)``."""
    now = time.time() if now is None else now
    member = f"{now:.6f}:{uuid.uuid4().hex[:8]}"
    pipe = redis.pipeline()
    pipe.zremrangebyscore(key, 0, now - WINDOW_SECONDS)
    pipe.zadd(key, {member: now})
    pipe.zcard(key)
    pipe.zrange(key, 0, 0, withscores=True)
    pipe.expire(key, WINDOW_SECONDS + 1)
    results = await pipe.execute()
    count = int(results[2])
    oldest = results[3][0][1] if results[3] else now
    return count, float(oldest)


async def _check_rate_limit(tier: str, request: Request, redis: Redis) -> None:
    limit = _limits()[tier]
    if limit <= 0:
        return

    identity = await rate_limit_identity(request)
    key = f"rl:ratelimit:{tier}:{identity}"

    try:
        count, oldest = await sliding_window_hit(redis, key, limit)
        reset_at = int(oldest + WINDOW_SECONDS)

        if not hasattr(request.state, "rate_limit_info"):
            request.state.rate_limit_info = {}
        request.state.rate_limit_info.update(
            {
                "limit_requests": limit,
                "remaining_requests": limit - count,
                "reset": reset_at,
            }
        )

        if count > limit:
            retry_after = max(1, int(reset_at - time.time()))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(retry_after)},
            )
    except HTTPException:
        raise
    except Exception as exc:
        log.warning("rate_limit_redis_error", tier=tier, error=str(exc))


async def ingest_rate_limit(
    request: Request,
    redis: Redis = Depends(get_redis),
) -> None:
    """INGEST_RATE_LIMIT_PER_MINUTE per API key — high-volume ingest."""
    await _check_rate_limit("ingest", request, redis)


async def analytics_rate_limit(
    request: Request,
    redis: Redis = Depends(get_redis),
) -> None:
    """ANALYTICS_RATE_LIMIT_PER_MINUTE per API key — analytics queries."""
    await _check_rate_limit("analytics", request, redis)


async def management_rate_limit(
    request: Request,
    redis: Redis = Depends(get_redis),
) -> None:
    """MANAGEMENT_RATE_LIMIT_PER_MINUTE per API key — CRUD management endpoints."""
    await _check_rate_limit("management", request, redis)


async def system_rate_limit(
    request: Request,
    redis: Redis = Depends(get_redis),
) -> None:
    """Low-volume protection for bootstrap/admin/system surfaces."""
    if not settings.abuse_protection_enabled:
        return
    await _check_rate_limit("system", request, redis)
