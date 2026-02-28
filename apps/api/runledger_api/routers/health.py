from typing import Literal

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.redis import get_redis

try:
    from redis.asyncio import Redis
except ImportError:
    Redis = object  # type: ignore[misc,assignment]

log = structlog.get_logger()

router = APIRouter(tags=["system"])


@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict[str, Literal["ok", "error", "degraded"]]:
    result: dict[str, Literal["ok", "error", "degraded"]] = {
        "status": "ok",
        "db": "ok",
        "redis": "ok",
    }

    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        log.warning("db_health_check_failed", error=str(exc))
        result["db"] = "error"
        result["status"] = "degraded"

    try:
        await redis.ping()
    except Exception as exc:
        log.warning("redis_health_check_failed", error=str(exc))
        result["redis"] = "error"
        result["status"] = "degraded"

    return result


@router.get("/health/live")
async def liveness() -> dict[str, str]:
    """Always returns 200. Used by Railway/container restart policy."""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict[str, str]:
    """Returns 200 if both DB and Redis are reachable, else HTTP 503."""
    db_ok = True
    redis_ok = True

    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        log.warning("readiness_db_failed", error=str(exc))
        db_ok = False

    try:
        await redis.ping()
    except Exception as exc:
        log.warning("readiness_redis_failed", error=str(exc))
        redis_ok = False

    if not db_ok or not redis_ok:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "degraded",
                "db": "ok" if db_ok else "error",
                "redis": "ok" if redis_ok else "error",
            },
        )

    return {"status": "ok", "db": "ok", "redis": "ok"}
