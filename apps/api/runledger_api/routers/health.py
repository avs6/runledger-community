from typing import Literal

import structlog
from fastapi import APIRouter, Depends
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
