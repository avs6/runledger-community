"""
Operational metrics endpoints.

  GET /metrics       — Prometheus text format (scrape by Prometheus/Grafana Agent)
  GET /ops/status    — JSON operational snapshot (dashboards, status pages)

Both endpoints require X-Metrics-Token header (defaults to ADMIN_SECRET / SECRET_KEY).

Prometheus scrape config example:
  - job_name: runledger
    static_configs:
      - targets: ["api:8000"]
    metrics_path: /metrics
    params:
      format: [prometheus]
    authorization:
      type: Bearer   # or use bearer_token_file
      credentials: <METRICS_TOKEN>

Grafana dashboard: import the JSON at docs/grafana-dashboard.json
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from collections.abc import Awaitable
from typing import Any, cast

import structlog
from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from runledger_api.core.config import settings

log = structlog.get_logger()

router = APIRouter(tags=["Operations"])

_SCRAPE_START = time.time()


# ── Auth helper ───────────────────────────────────────────────────────────────


def _check_metrics_token(token: str | None) -> None:
    expected = settings.effective_metrics_token
    bearer = (token or "").removeprefix("Bearer ").strip()
    if bearer != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Metrics-Token",
        )


# ── Metrics collection ────────────────────────────────────────────────────────


async def _collect_metrics() -> dict[str, Any]:
    """Gather all operational metrics from Redis + PostgreSQL."""
    from runledger_api.core.redis import redis_client  # noqa: PLC0415
    from runledger_api.models.events import AgentRun, ProviderCall  # noqa: PLC0415
    from runledger_api.models.gateway import GatewayRequest  # noqa: PLC0415

    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    metrics: dict[str, Any] = {
        "collected_at": datetime.now(UTC).isoformat(),
        "uptime_seconds": round(time.time() - _SCRAPE_START, 1),
    }

    # ── Celery queue depths (Redis list lengths) ────────────────────────────
    celery_queues = ["celery", "priority", "low"]
    queue_depths: dict[str, int] = {}
    for q in celery_queues:
        try:
            depth = await cast(Awaitable[int], redis_client.llen(q))
            queue_depths[q] = int(depth or 0)
        except Exception:
            queue_depths[q] = -1
    metrics["celery_queue_depths"] = queue_depths

    async with AsyncSession(engine) as session:
        # ── Active agent runs ──────────────────────────────────────────────
        try:
            result = await session.execute(select(func.count()).where(AgentRun.status == "running"))
            metrics["active_runs"] = result.scalar() or 0
        except Exception:
            metrics["active_runs"] = -1

        # ── Pipeline lag (seconds since last AgentRun was created) ─────────
        try:
            result = await session.execute(
                select(func.max(AgentRun.started_at)).where(AgentRun.source_type != "otlp")
            )
            last_run_at = cast(datetime | None, result.scalar())
            if last_run_at:
                lag = (datetime.now(UTC) - last_run_at.replace(tzinfo=UTC)).total_seconds()
                metrics["pipeline_lag_seconds"] = round(lag, 1)
            else:
                metrics["pipeline_lag_seconds"] = -1.0
        except Exception:
            metrics["pipeline_lag_seconds"] = -1.0

        # ── Ingest rate — runs created in last 5 minutes ──────────────────
        try:
            cutoff = datetime.now(UTC) - timedelta(minutes=5)
            result = await session.execute(
                select(func.count(AgentRun.id)).where(AgentRun.started_at >= cutoff)
            )
            count_5m = result.scalar() or 0
            metrics["ingest_rate_per_minute"] = round(count_5m / 5.0, 2)
        except Exception:
            metrics["ingest_rate_per_minute"] = -1.0

        # ── Provider calls last hour ───────────────────────────────────────
        try:
            cutoff_1h = datetime.now(UTC) - timedelta(hours=1)
            result = await session.execute(
                select(func.count(ProviderCall.id)).where(ProviderCall.created_at >= cutoff_1h)
            )
            metrics["provider_calls_last_hour"] = result.scalar() or 0
        except Exception:
            metrics["provider_calls_last_hour"] = -1

        # ── Gateway requests last hour + cache hit rate ───────────────────
        try:
            result = await session.execute(
                select(
                    func.count(GatewayRequest.id).label("total"),
                    func.sum(
                        func.cast(GatewayRequest.cache_hit.is_(True), type_=func.count().type)
                    ).label("cached"),
                ).where(GatewayRequest.created_at >= cutoff_1h)
            )
            row = result.one()
            total_gw = row.total or 0
            metrics["gateway_requests_last_hour"] = total_gw
            metrics["gateway_cache_hit_rate"] = (
                round((row.cached or 0) / total_gw, 4) if total_gw > 0 else 0.0
            )
        except Exception:
            metrics["gateway_requests_last_hour"] = -1
            metrics["gateway_cache_hit_rate"] = -1.0

        # ── Uncosted provider calls (metering backlog) ────────────────────
        try:
            result = await session.execute(
                select(func.count(ProviderCall.id)).where(ProviderCall.cost_usd.is_(None))
            )
            metrics["uncosted_provider_calls"] = result.scalar() or 0
        except Exception:
            metrics["uncosted_provider_calls"] = -1

    await engine.dispose()
    return metrics


# ── Prometheus text format renderer ──────────────────────────────────────────


def _prometheus_lines(m: dict[str, Any]) -> list[str]:
    lines: list[str] = []

    def gauge(name: str, value: float | int, labels: str = "", help_text: str = "") -> None:
        if help_text:
            lines.append(f"# HELP {name} {help_text}")
        lines.append(f"# TYPE {name} gauge")
        label_str = f"{{{labels}}}" if labels else ""
        lines.append(f"{name}{label_str} {value}")

    gauge(
        "runledger_uptime_seconds",
        m.get("uptime_seconds", 0),
        help_text="Seconds since the API process started",
    )
    gauge(
        "runledger_active_runs",
        m.get("active_runs", 0),
        help_text="Number of agent runs currently in running state",
    )
    gauge(
        "runledger_pipeline_lag_seconds",
        m.get("pipeline_lag_seconds", -1),
        help_text="Seconds since the most recent agent run was ingested",
    )
    gauge(
        "runledger_ingest_rate_per_minute",
        m.get("ingest_rate_per_minute", 0),
        help_text="Agent runs ingested per minute (5-minute window)",
    )
    gauge(
        "runledger_provider_calls_last_hour",
        m.get("provider_calls_last_hour", 0),
        help_text="Provider calls recorded in the last hour",
    )
    gauge(
        "runledger_gateway_requests_last_hour",
        m.get("gateway_requests_last_hour", 0),
        help_text="Gateway requests forwarded in the last hour",
    )
    gauge(
        "runledger_gateway_cache_hit_rate",
        m.get("gateway_cache_hit_rate", 0),
        help_text="Fraction of gateway requests served from prompt cache (0–1)",
    )
    gauge(
        "runledger_uncosted_provider_calls",
        m.get("uncosted_provider_calls", 0),
        help_text="Provider calls awaiting cost enrichment (metering backlog)",
    )

    # Queue depths as labelled series
    lines.append("# HELP runledger_celery_queue_depth Number of tasks waiting in Celery queue")
    lines.append("# TYPE runledger_celery_queue_depth gauge")
    for queue, depth in m.get("celery_queue_depths", {}).items():
        lines.append(f'runledger_celery_queue_depth{{queue="{queue}"}} {depth}')

    return lines


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/metrics", response_class=PlainTextResponse, include_in_schema=False)
async def prometheus_metrics(
    x_metrics_token: str | None = Header(default=None, alias="X-Metrics-Token"),
) -> PlainTextResponse:
    """
    Prometheus text-format metrics endpoint.
    Protected by X-Metrics-Token header.
    """
    _check_metrics_token(x_metrics_token)
    try:
        m = await _collect_metrics()
        lines = _prometheus_lines(m)
        body = "\n".join(lines) + "\n"
    except Exception as exc:
        log.exception("metrics_collection_failed", error=str(exc))
        body = "# ERROR metrics collection failed\n"
    return PlainTextResponse(body, media_type="text/plain; version=0.0.4; charset=utf-8")


@router.get("/ops/status")
async def ops_status(
    x_metrics_token: str | None = Header(default=None, alias="X-Metrics-Token"),
) -> dict[str, Any]:
    """
    JSON operational snapshot — queue depths, active runs, pipeline lag,
    ingest rate, gateway stats, and uncosted backlog.
    Protected by X-Metrics-Token header.
    """
    _check_metrics_token(x_metrics_token)
    try:
        return await _collect_metrics()
    except Exception as exc:
        log.exception("ops_status_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Metrics collection failed") from exc
