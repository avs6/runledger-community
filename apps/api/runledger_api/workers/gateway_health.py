"""
Celery beat worker: gateway route health monitoring (every 5 minutes).

For each workspace's active gateway routes, query gateway_requests over the
last 10 minutes.  If the error rate exceeds 5%, increment consecutive_health_failures.
When failures reach the threshold (3), auto-disable the route and set disabled_reason.

Recovery: if a previously auto-disabled route now has <5% error rate, re-enable it
and reset consecutive_health_failures.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from runledger_api.core.celery_app import celery_app
from runledger_api.core.config import settings
from runledger_api.models.gateway import GatewayRequest, GatewayRoute

log = structlog.get_logger()

_ERROR_RATE_THRESHOLD = 0.05   # 5 %
_WINDOW_MINUTES = 10
_FAILURE_THRESHOLD = 3         # consecutive bad windows before auto-disable
_MIN_REQUESTS = 5              # ignore routes with fewer requests in window


def _make_session_factory() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@celery_app.task(name="gateway.health_check", max_retries=1)  # type: ignore[untyped-decorator]
def run_gateway_health_check() -> dict[str, int]:
    """Check health of all gateway routes; auto-disable unhealthy ones."""
    return asyncio.run(_run_health_check())


async def _run_health_check() -> dict[str, int]:
    factory = _make_session_factory()
    disabled_count = 0
    recovered_count = 0
    checked_count = 0

    async with factory() as db:
        # Load all routes (active AND inactive, to allow recovery)
        routes_result = await db.execute(select(GatewayRoute))
        routes = list(routes_result.scalars().all())

        cutoff = datetime.now(UTC) - timedelta(minutes=_WINDOW_MINUTES)

        for route in routes:
            checked_count += 1
            now = datetime.now(UTC)

            # Query request counts in the health window
            stats_stmt = (
                select(
                    func.count(GatewayRequest.id).label("total"),
                    func.count(GatewayRequest.id)
                    .filter(GatewayRequest.status == "error")
                    .label("errors"),
                )
                .where(
                    GatewayRequest.route_id == route.id,
                    GatewayRequest.created_at >= cutoff,
                )
            )
            result = await db.execute(stats_stmt)
            row = result.one()
            total = int(row.total or 0)
            errors = int(row.errors or 0)

            # Update last_health_check_at regardless
            await db.execute(
                update(GatewayRoute)
                .where(GatewayRoute.id == route.id)
                .values(last_health_check_at=now)
            )

            if total < _MIN_REQUESTS:
                # Not enough traffic to make a health decision; reset failures
                if route.consecutive_health_failures > 0 and route.is_active:
                    await db.execute(
                        update(GatewayRoute)
                        .where(GatewayRoute.id == route.id)
                        .values(consecutive_health_failures=0)
                    )
                continue

            error_rate = errors / total

            if error_rate > _ERROR_RATE_THRESHOLD:
                new_failures = route.consecutive_health_failures + 1
                updates: dict = {"consecutive_health_failures": new_failures}

                if route.is_active and route.health_auto_disable and new_failures >= _FAILURE_THRESHOLD:
                    reason = (
                        f"Auto-disabled: {errors}/{total} errors "
                        f"({error_rate:.1%}) in last {_WINDOW_MINUTES}m"
                    )
                    updates["is_active"] = False
                    updates["disabled_reason"] = reason
                    disabled_count += 1
                    log.warning(
                        "gateway_route_auto_disabled",
                        route_id=str(route.id),
                        alias=route.alias,
                        error_rate=f"{error_rate:.2%}",
                    )

                await db.execute(
                    update(GatewayRoute).where(GatewayRoute.id == route.id).values(**updates)
                )
            else:
                # Healthy window
                if not route.is_active and route.disabled_reason and route.disabled_reason.startswith("Auto-disabled"):
                    # Re-enable auto-disabled routes that have recovered
                    await db.execute(
                        update(GatewayRoute)
                        .where(GatewayRoute.id == route.id)
                        .values(
                            is_active=True,
                            disabled_reason=None,
                            consecutive_health_failures=0,
                        )
                    )
                    recovered_count += 1
                    log.info(
                        "gateway_route_recovered",
                        route_id=str(route.id),
                        alias=route.alias,
                    )
                elif route.consecutive_health_failures > 0:
                    await db.execute(
                        update(GatewayRoute)
                        .where(GatewayRoute.id == route.id)
                        .values(consecutive_health_failures=0)
                    )

        await db.commit()

    log.info(
        "gateway_health_check_complete",
        checked=checked_count,
        disabled=disabled_count,
        recovered=recovered_count,
    )
    return {"checked": checked_count, "disabled": disabled_count, "recovered": recovered_count}
