"""
Gateway runtime control checks.

  check_cost_cap     — daily/monthly USD spend vs route limits (429 on breach)
  check_per_user_rpm — Redis sliding window per (workspace, end_user, route)
"""

from __future__ import annotations

import time
import uuid
from decimal import Decimal
from typing import Any

import structlog
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.gateway import GatewayRequest, GatewayRoute

log = structlog.get_logger()

# Fallback prices used only when no pricing row is found for the route's model.
# Real per-model rates are fetched from provider_pricing at check time.
_FALLBACK_COST_PER_1M_INPUT = Decimal("0.50")
_FALLBACK_COST_PER_1M_OUTPUT = Decimal("1.50")


def _estimate_cost(
    row: Any,
    input_rate: Decimal,
    output_rate: Decimal,
) -> Decimal:
    """Estimate USD cost from token counts using per-model pricing rates."""
    input_t = Decimal(str(row.total_input or 0))
    output_t = Decimal(str(row.total_output or 0))
    return input_t / Decimal("1000000") * input_rate + output_t / Decimal("1000000") * output_rate


async def _lookup_model_rates(
    db: AsyncSession,
    model: str | None,
    provider: str | None,
) -> tuple[Decimal, Decimal]:
    """
    Return (input_cost_per_1m, output_cost_per_1m) for the given model.
    Falls back to generic defaults if no pricing row is found.
    Prefers workspace-specific rows over global rows, and the most-recently
    effective row when multiple match.
    """
    if not model:
        return _FALLBACK_COST_PER_1M_INPUT, _FALLBACK_COST_PER_1M_OUTPUT

    from datetime import date  # noqa: PLC0415

    from sqlalchemy import and_, or_  # noqa: PLC0415

    from runledger_api.models.metering import ProviderPricing  # noqa: PLC0415

    today = date.today()
    stmt = (
        select(ProviderPricing)
        .where(
            and_(
                ProviderPricing.model == model,
                or_(
                    ProviderPricing.effective_from.is_(None),
                    ProviderPricing.effective_from <= today,
                ),
            )
        )
        .order_by(
            # Workspace-specific rows first (workspace_id IS NOT NULL), then by
            # most-recent effective date
            ProviderPricing.workspace_id.is_(None).asc(),
            ProviderPricing.effective_from.desc().nulls_last(),
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    pricing = result.scalar_one_or_none()
    if pricing is None:
        return _FALLBACK_COST_PER_1M_INPUT, _FALLBACK_COST_PER_1M_OUTPUT
    return pricing.input_cost_per_1m, pricing.output_cost_per_1m


async def check_cost_cap(
    db: AsyncSession,
    route: GatewayRoute,
    workspace_id: uuid.UUID,
) -> None:
    """
    Raise HTTP 429 with X-Cost-Cap-Reason if the route's daily or monthly
    cost limit has been exceeded.  Skips if no limits are configured.
    """
    has_daily = route.daily_cost_limit_usd is not None
    has_monthly = route.monthly_cost_limit_usd is not None
    if not has_daily and not has_monthly:
        return

    from datetime import UTC, datetime  # noqa: PLC0415

    input_rate, output_rate = await _lookup_model_rates(
        db, getattr(route, "target_model", None), getattr(route, "provider", None)
    )

    now = datetime.now(UTC)
    today_start = datetime(now.year, now.month, now.day, tzinfo=UTC)
    month_start = datetime(now.year, now.month, 1, tzinfo=UTC)

    # Single query covering both windows
    stmt = select(
        func.sum(GatewayRequest.input_tokens).label("total_input"),
        func.sum(GatewayRequest.output_tokens).label("total_output"),
        func.min(GatewayRequest.created_at).label("oldest"),
    ).where(
        GatewayRequest.route_id == route.id,
        GatewayRequest.workspace_id == workspace_id,
        GatewayRequest.created_at >= month_start,
        GatewayRequest.status != "cache_hit",
    )
    result = await db.execute(stmt)
    monthly_row = result.one()

    # Daily subset
    day_stmt = select(
        func.sum(GatewayRequest.input_tokens).label("total_input"),
        func.sum(GatewayRequest.output_tokens).label("total_output"),
    ).where(
        GatewayRequest.route_id == route.id,
        GatewayRequest.workspace_id == workspace_id,
        GatewayRequest.created_at >= today_start,
        GatewayRequest.status != "cache_hit",
    )
    day_result = await db.execute(day_stmt)
    daily_row = day_result.one()

    if has_daily:
        daily_cost = _estimate_cost(daily_row, input_rate, output_rate)
        if daily_cost >= route.daily_cost_limit_usd:  # type: ignore[operator]
            log.warning(
                "gateway_cost_cap_daily_exceeded",
                route_id=str(route.id),
                daily_cost=str(daily_cost),
                limit=str(route.daily_cost_limit_usd),
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Daily cost cap reached for this route",
                headers={"X-Cost-Cap-Reason": "daily_limit_exceeded"},
            )

    if has_monthly:
        monthly_cost = _estimate_cost(monthly_row, input_rate, output_rate)
        if monthly_cost >= route.monthly_cost_limit_usd:  # type: ignore[operator]
            log.warning(
                "gateway_cost_cap_monthly_exceeded",
                route_id=str(route.id),
                monthly_cost=str(monthly_cost),
                limit=str(route.monthly_cost_limit_usd),
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Monthly cost cap reached for this route",
                headers={"X-Cost-Cap-Reason": "monthly_limit_exceeded"},
            )


async def check_per_user_rpm(
    redis: Any,
    workspace_id: uuid.UUID,
    end_user_id: str,
    route_id: uuid.UUID,
    rpm_limit: int,
) -> None:
    """
    Redis sliding-window rate limiter per end-user per route.

    Key: rl:gateway:rpm:{workspace_id}:{route_id}:{end_user_id}:{epoch_minute}
    Window: 1 minute (60 seconds TTL).
    Raises HTTP 429 with Retry-After header on breach.
    """
    epoch_minute = int(time.time()) // 60
    key = f"rl:gateway:rpm:{workspace_id}:{route_id}:{end_user_id}:{epoch_minute}"

    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 60)
        if count > rpm_limit:
            log.warning(
                "gateway_per_user_rpm_exceeded",
                end_user_id=end_user_id,
                route_id=str(route_id),
                count=count,
                limit=rpm_limit,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Per-user rate limit exceeded for this route",
                headers={"Retry-After": "60"},
            )
    except HTTPException:
        raise
    except Exception:
        # Fail open: if Redis is unavailable, allow the request
        log.warning("gateway_per_user_rpm_redis_error", route_id=str(route_id))
