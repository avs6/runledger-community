"""
Gateway runtime control checks.

  check_cost_cap     — daily/monthly USD spend vs route limits (429 on breach)
  check_per_user_rpm — atomic Redis sliding window per (workspace, end user or key, route)
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

# Providers that run on your own hardware: with no pricing row they cost nothing, so
# their calls don't count toward cost caps. Hosted models are never given an invented
# price (review G-17).
LOCAL_PROVIDERS = frozenset({"ollama", "vllm", "local", "lmstudio", "llamacpp"})


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
    workspace_id: uuid.UUID | None = None,
) -> tuple[Decimal, Decimal] | None:
    """(input, output) USD per 1M tokens for the route's provider/model, resolved like
    the ledger (``services.pricing``: this workspace's override, then the global row).

    Local providers with no pricing row cost 0. Returns None for an unpriced hosted
    model, so a cap is never enforced against a made-up price (review G-17)."""
    from datetime import UTC, datetime  # noqa: PLC0415

    from runledger_api.services.pricing import _get_pricing  # noqa: PLC0415

    pricing = None
    if model and provider:
        pricing = await _get_pricing(db, provider, model, datetime.now(UTC), workspace_id)
    if pricing is not None:
        return pricing.input_cost_per_1m, pricing.output_cost_per_1m
    if (provider or "").lower() in LOCAL_PROVIDERS:
        return Decimal("0"), Decimal("0")
    return None


async def cost_cap_pricing_error(
    db: AsyncSession,
    *,
    provider: str | None,
    model: str | None,
    workspace_id: uuid.UUID,
) -> str | None:
    """Why a cost cap can't be enforced on this route (no price for a hosted model),
    or None when it can. Checked when a cap is saved (review G-17)."""
    if await _lookup_model_rates(db, model, provider, workspace_id) is not None:
        return None
    return (
        f"No pricing for {provider}/{model}; add a provider price for this model before "
        "setting a cost cap on the route"
    )


def _seconds_until(when: Any, now: Any) -> str:
    """Retry-After value: whole seconds from ``now`` until ``when`` (at least 1)."""
    return str(max(1, int((when - now).total_seconds())))


def _next_month(month_start: Any) -> Any:
    """First instant of the month after ``month_start``."""
    if month_start.month == 12:
        return month_start.replace(year=month_start.year + 1, month=1)
    return month_start.replace(month=month_start.month + 1)


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

    from datetime import UTC, datetime, timedelta  # noqa: PLC0415

    rates = await _lookup_model_rates(
        db, getattr(route, "target_model", None), getattr(route, "provider", None), workspace_id
    )
    if rates is None:
        # Saving a cap requires a price, so this means the price was removed later:
        # skip rather than enforce against an invented one (review G-17).
        log.warning(
            "gateway_cost_cap_unpriced_model",
            route_id=str(route.id),
            provider=getattr(route, "provider", None),
            model=getattr(route, "target_model", None),
        )
        return
    input_rate, output_rate = rates

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
                headers={
                    "X-Cost-Cap-Reason": "daily_limit_exceeded",
                    "Retry-After": _seconds_until(today_start + timedelta(days=1), now),
                },
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
                headers={
                    "X-Cost-Cap-Reason": "monthly_limit_exceeded",
                    "Retry-After": _seconds_until(_next_month(month_start), now),
                },
            )

    # ── Budget Tier check ─────────────────────────────────────────────────────
    from runledger_api.models.budget_tiers import BudgetTier  # noqa: PLC0415

    bt_stmt = (
        select(BudgetTier)
        .where(
            BudgetTier.workspace_id == workspace_id,
            BudgetTier.is_active.is_(True),
            BudgetTier.max_spend_usd.isnot(None),
        )
        .order_by(BudgetTier.is_default.desc())
        .limit(1)
    )
    bt_res = await db.execute(bt_stmt)
    bt = bt_res.scalar_one_or_none()
    if bt and bt.max_spend_usd is not None:
        tier_cost = _estimate_cost(monthly_row, input_rate, output_rate)
        if tier_cost >= bt.max_spend_usd:
            log.warning(
                "gateway_budget_tier_exceeded",
                tier_id=str(bt.id),
                tier_cost=str(tier_cost),
                limit=str(bt.max_spend_usd),
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Budget Tier '{bt.name}' limit breached (${bt.max_spend_usd:.2f})",
                headers={
                    "X-Cost-Cap-Reason": "budget_tier_exceeded",
                    "Retry-After": _seconds_until(_next_month(month_start), now),
                },
            )


# Atomic sliding window over a sorted set of request timestamps (ms). Refused requests
# don't take a slot; with consume=0 the call only checks. Returns {allowed, count,
# retry_after_ms}, where retry_after_ms is when the oldest hit leaves the window.
_RPM_SCRIPT = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local consume = tonumber(ARGV[4])
redis.call('ZREMRANGEBYSCORE', key, '-inf', now - window)
local count = redis.call('ZCARD', key)
if count >= limit then
  local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
  local retry = window
  if oldest[2] then retry = tonumber(oldest[2]) + window - now end
  return {0, count, retry}
end
if consume == 1 then
  redis.call('ZADD', key, now, ARGV[5])
  redis.call('PEXPIRE', key, window)
end
return {1, count + consume, 0}
"""
_RPM_WINDOW_MS = 60_000


def rpm_subject(end_user_id: str | None, api_key_id: uuid.UUID | str | None) -> str | None:
    """Who a per-user RPM limit applies to: the end user when the caller names one,
    otherwise the API key, so leaving out X-RunLedger-End-User-Id doesn't bypass the
    limit (review G-14). None only for keyless callers with no end user."""
    if end_user_id:
        return f"user:{end_user_id}"
    if api_key_id:
        return f"key:{api_key_id}"
    return None


async def check_per_user_rpm(
    redis: Any,
    workspace_id: uuid.UUID,
    subject: str,
    route_id: uuid.UUID,
    rpm_limit: int,
    *,
    consume: bool = True,
) -> None:
    """Per-subject, per-route requests-per-minute limit (review G-14).

    A true sliding 60-second window, evaluated atomically in Redis, so concurrent
    requests can't overshoot it. ``consume=False`` checks without taking a slot (used for
    fallback routes, which only count when they serve). Raises 429 with Retry-After (time
    until a slot frees). Fails open, with a warning, if Redis is unavailable.
    """
    key = f"rl:gateway:rpm:{workspace_id}:{route_id}:{subject}"
    now_ms = int(time.time() * 1000)
    try:
        allowed, count, retry_ms = await redis.eval(
            _RPM_SCRIPT,
            1,
            key,
            now_ms,
            _RPM_WINDOW_MS,
            rpm_limit,
            1 if consume else 0,
            f"{now_ms}:{uuid.uuid4().hex[:8]}",
        )
    except Exception:
        # Fail open: if Redis is unavailable, allow the request
        log.warning("gateway_per_user_rpm_redis_error", route_id=str(route_id))
        return
    if int(allowed) == 1:
        return
    log.warning(
        "gateway_per_user_rpm_exceeded",
        subject=subject,
        route_id=str(route_id),
        count=int(count),
        limit=rpm_limit,
    )
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Per-user rate limit exceeded for this route",
        headers={"Retry-After": str(max(1, -(-int(retry_ms) // 1000)))},
    )
