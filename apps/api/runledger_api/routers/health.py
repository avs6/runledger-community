from datetime import UTC, datetime
from email.utils import format_datetime
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.config import settings
from runledger_api.core.db import get_db
from runledger_api.core.deps import require_platform_admin
from runledger_api.core.redis import get_redis
from runledger_api.models.events import AgentRun, ProviderCall
from runledger_api.models.gateway import GatewayRequest
from runledger_api.services.ops import get_queue_depths
from runledger_api.services.system_status import (
    STARTED_AT,
    check_db,
    check_redis,
    health_snapshot,
    migration_state,
    system_status,
)

try:
    from redis.asyncio import Redis
except ImportError:
    Redis = object  # type: ignore[misc,assignment]

log = structlog.get_logger()

router = APIRouter(tags=["system"])
_STARTED_AT = STARTED_AT


def _require_metrics_token(authorization: str | None) -> None:
    import hmac  # noqa: PLC0415

    token = settings.effective_metrics_token
    if not token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Metrics disabled: set METRICS_TOKEN to enable /metrics",
        )
    expected = f"Bearer {token}"
    # Constant-time compare (review P-15).
    if authorization and hmac.compare_digest(authorization.encode(), expected.encode()):
        return
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid metrics token",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> JSONResponse:
    """Overall health. 503 when degraded (review P-19): the database or Redis is down,
    the database is behind this build's migrations, or Celery beat stopped sending
    heartbeats. Load balancers and uptime checks can rely on the status code."""
    healthy, body = await health_snapshot(db, redis)
    return JSONResponse(
        body,
        status_code=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
    )


@router.get("/health/live")
async def liveness() -> dict[str, str]:
    """Always returns 200. Used by Railway/container restart policy."""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict[str, Any]:
    """Ready to take traffic: DB and Redis reachable and the schema not behind this
    build (a pod started before its migration job finished stays out of rotation).
    Beat is not required for readiness, so a beat outage never drains the API."""
    db_state = await check_db(db)
    redis_state = await check_redis(redis)
    migrations = await migration_state(db) if db_state == "ok" else {"status": "unknown"}
    body = {
        "status": "ok",
        "db": db_state,
        "redis": redis_state,
        "migrations": migrations["status"],
    }
    if db_state != "ok" or redis_state != "ok" or migrations["status"] == "behind":
        body["status"] = "degraded"
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=body)
    return body


@router.get("/system/status")
async def get_system_status(
    _auth: Annotated[tuple[Any, ...], Depends(require_platform_admin)],
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict[str, Any]:
    """Platform admins: workers, queues, beat, migrations, backups and the build each
    component runs (version skew), plus production configuration warnings."""
    return await system_status(db, redis)


@router.get("/metrics", include_in_schema=False)
async def metrics(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> Response:
    """
    Prometheus-style plaintext metrics for infrastructure scraping.

    Protected by a bearer token via METRICS_TOKEN (no admin-secret fallback).
    """
    _require_metrics_token(authorization)

    now = datetime.now(UTC)
    uptime = max(0.0, (now - _STARTED_AT).total_seconds())
    one_hour_ago = now.timestamp() - 3600
    five_minutes_ago = now.timestamp() - 300

    active_runs = (
        await db.execute(
            select(func.count()).select_from(AgentRun).where(AgentRun.status == "running")
        )
    ).scalar_one()
    latest_ingest_at = (await db.execute(select(func.max(ProviderCall.created_at)))).scalar_one()
    provider_calls_last_hour = (
        await db.execute(
            select(func.count())
            .select_from(ProviderCall)
            .where(func.extract("epoch", ProviderCall.created_at) >= one_hour_ago)
        )
    ).scalar_one()
    provider_calls_last_five_minutes = (
        await db.execute(
            select(func.count())
            .select_from(ProviderCall)
            .where(func.extract("epoch", ProviderCall.created_at) >= five_minutes_ago)
        )
    ).scalar_one()
    gateway_requests_last_hour = (
        await db.execute(
            select(func.count())
            .select_from(GatewayRequest)
            .where(func.extract("epoch", GatewayRequest.created_at) >= one_hour_ago)
        )
    ).scalar_one()
    gateway_cache_hits_last_hour = (
        await db.execute(
            select(func.count())
            .select_from(GatewayRequest)
            .where(
                func.extract("epoch", GatewayRequest.created_at) >= one_hour_ago,
                GatewayRequest.cache_hit.is_(True),
            )
        )
    ).scalar_one()
    uncosted_provider_calls = (
        await db.execute(
            select(func.count()).select_from(ProviderCall).where(ProviderCall.cost_usd.is_(None))
        )
    ).scalar_one()

    pipeline_lag_seconds = 0.0
    if latest_ingest_at is not None:
        pipeline_lag_seconds = max(0.0, (now - latest_ingest_at).total_seconds())

    cache_hit_rate = 0.0
    if gateway_requests_last_hour:
        cache_hit_rate = gateway_cache_hits_last_hour / gateway_requests_last_hour

    queue_depths = await get_queue_depths(redis)

    lines = [
        "# HELP runledger_uptime_seconds Seconds since the API process started.",
        "# TYPE runledger_uptime_seconds gauge",
        f"runledger_uptime_seconds {uptime:.3f}",
        "# HELP runledger_active_runs Agent runs currently marked running.",
        "# TYPE runledger_active_runs gauge",
        f"runledger_active_runs {active_runs}",
        "# HELP runledger_pipeline_lag_seconds Seconds since the latest provider call was ingested.",
        "# TYPE runledger_pipeline_lag_seconds gauge",
        f"runledger_pipeline_lag_seconds {pipeline_lag_seconds:.3f}",
        "# HELP runledger_ingest_rate_per_minute Average provider-call ingest rate over the last five minutes.",
        "# TYPE runledger_ingest_rate_per_minute gauge",
        f"runledger_ingest_rate_per_minute {provider_calls_last_five_minutes / 5:.3f}",
        "# HELP runledger_provider_calls_last_hour Provider calls recorded in the last hour.",
        "# TYPE runledger_provider_calls_last_hour gauge",
        f"runledger_provider_calls_last_hour {provider_calls_last_hour}",
        "# HELP runledger_gateway_requests_last_hour Gateway requests recorded in the last hour.",
        "# TYPE runledger_gateway_requests_last_hour gauge",
        f"runledger_gateway_requests_last_hour {gateway_requests_last_hour}",
        "# HELP runledger_gateway_cache_hit_rate Fraction of last-hour gateway requests served from cache.",
        "# TYPE runledger_gateway_cache_hit_rate gauge",
        f"runledger_gateway_cache_hit_rate {cache_hit_rate:.6f}",
        "# HELP runledger_uncosted_provider_calls Provider calls still missing cost enrichment.",
        "# TYPE runledger_uncosted_provider_calls gauge",
        f"runledger_uncosted_provider_calls {uncosted_provider_calls}",
        "# HELP runledger_celery_queue_depth Tasks currently waiting in Redis-backed Celery queues.",
        "# TYPE runledger_celery_queue_depth gauge",
    ]
    for item in queue_depths:
        lines.append(f'runledger_celery_queue_depth{{queue="{item["queue"]}"}} {item["depth"]}')

    return Response(
        content="\n".join(lines) + "\n",
        media_type="text/plain; version=0.0.4; charset=utf-8",
        headers={"Last-Modified": format_datetime(now, usegmt=True)},
    )
