"""
Gateway runtime control checks.

  check_cost_cap        — daily/monthly USD spend vs route limits (429 on breach)
  key_tier_breach       — the API key's budget tier spend limit (checked in preflight
                          through services.budgets.check_request_budgets)
  enforce_runaway_hold  — 429 for a run or session the runaway detector holds
  check_per_user_rpm    — atomic Redis sliding window per (workspace, end user or key, route)
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
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


async def _route_cost(
    db: AsyncSession,
    row: Any,
    *,
    provider: str | None,
    model: str | None,
    workspace_id: uuid.UUID,
) -> Decimal:
    """USD cost of a route's token totals, priced exactly like the ledger:
    ``services.pricing.calculate_cost`` with this workspace's pricing override first
    (review F-14). Local providers without a price cost 0."""
    from runledger_api.services.pricing import calculate_cost  # noqa: PLC0415

    cost = None
    if provider and model:
        cost = await calculate_cost(
            db,
            provider=provider,
            model=model,
            input_tokens=int(row.total_input or 0),
            output_tokens=int(row.total_output or 0),
            workspace_id=workspace_id,
        )
    return cost if cost is not None else Decimal("0")


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

    from datetime import timedelta  # noqa: PLC0415

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
    provider = getattr(route, "provider", None)
    model = getattr(route, "target_model", None)

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
        daily_cost = await _route_cost(
            db, daily_row, provider=provider, model=model, workspace_id=workspace_id
        )
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
        monthly_cost = await _route_cost(
            db, monthly_row, provider=provider, model=model, workspace_id=workspace_id
        )
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


# ── Budget tier spend (review cd:B-06) ────────────────────────────────────────

_TIER_CACHE_TTL = 30  # seconds


async def resolve_key_tier(db: AsyncSession, workspace_id: uuid.UUID, api_key_id: uuid.UUID) -> Any:
    """The tier that governs a key: its assigned tier when active, else the
    workspace default tier; None when neither exists."""
    from runledger_api.models.budget_tiers import BudgetTier  # noqa: PLC0415
    from runledger_api.models.tenant import ApiKey  # noqa: PLC0415

    key = await db.get(ApiKey, api_key_id)
    tier_id = getattr(key, "budget_tier_id", None) if key is not None else None
    if tier_id is not None:
        tier = await db.get(BudgetTier, tier_id)
        if tier is not None and tier.is_active and tier.workspace_id == workspace_id:
            return tier
    return (
        await db.execute(
            select(BudgetTier)
            .where(
                BudgetTier.workspace_id == workspace_id,
                BudgetTier.is_active.is_(True),
                BudgetTier.is_default.is_(True),
            )
            .limit(1)
        )
    ).scalar_one_or_none()


async def key_period_spend(
    db: AsyncSession, workspace_id: uuid.UUID, api_key_id: uuid.UUID, period_type: str
) -> Decimal:
    """The key's priced spend in the current period, across every route and source."""
    from runledger_api.models.events import ProviderCall  # noqa: PLC0415
    from runledger_api.services.budgets import period_window  # noqa: PLC0415

    start, end = period_window(period_type, datetime.now(UTC))
    stmt = select(func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0))).where(
        ProviderCall.workspace_id == workspace_id,
        ProviderCall.api_key_id == api_key_id,
        ProviderCall.cost_usd.is_not(None),
    )
    if start is not None and end is not None:
        stmt = stmt.where(ProviderCall.created_at >= start, ProviderCall.created_at < end)
    return Decimal((await db.execute(stmt)).scalar_one() or 0)


async def key_tier_breach(
    db: AsyncSession, redis: Any, workspace_id: uuid.UUID, api_key_id: uuid.UUID
) -> str | None:
    """``"budget_tier:<name>"`` when the key's tier spend limit is used up, else None.

    Fixes cd:B-06: the tier is the key's own (or the workspace default), its spend is
    the key's spend across all routes, and it applies whether or not the route has a
    cost cap. The result is cached in Redis for 30 s per key.
    """
    cache_key = f"rl:tier:{workspace_id}:{api_key_id}"
    try:
        cached = await redis.get(cache_key)
    except Exception:
        cached = None
    if cached is not None:
        return None if cached == "-" else str(cached)
    tier = await resolve_key_tier(db, workspace_id, api_key_id)
    verdict: str | None = None
    if tier is not None and tier.max_spend_usd is not None:
        spend = await key_period_spend(db, workspace_id, api_key_id, tier.period_type or "monthly")
        if spend >= tier.max_spend_usd:
            verdict = f"budget_tier:{tier.name}"
            log.warning(
                "gateway_budget_tier_exceeded",
                tier_id=str(tier.id),
                api_key_id=str(api_key_id),
                spend=str(spend),
                limit=str(tier.max_spend_usd),
            )
    try:
        await redis.set(cache_key, verdict or "-", ex=_TIER_CACHE_TTL)
    except Exception:
        log.warning("gateway_budget_tier_cache_failed", api_key_id=str(api_key_id))
    return verdict


# ── Runaway holds (review cd:B-09) ────────────────────────────────────────────


async def enforce_runaway_hold(
    db: AsyncSession, workspace_id: uuid.UUID, metadata: dict[str, Any] | None
) -> None:
    """Refuse (429) a request whose run or session the runaway detector holds.

    The run id comes from ``runledger.run_id`` / ``run_id`` metadata and the session
    from ``runledger.session_id`` / ``session_id`` / ``session``, the same keys the
    gateway records runs under. Fails open if Redis and Postgres both fail.
    """
    from runledger_api.core.redis import get_redis  # noqa: PLC0415
    from runledger_api.services.budgets import find_runaway_hold  # noqa: PLC0415

    meta = metadata or {}

    def _first(*keys: str) -> str | None:
        for k in keys:
            value = meta.get(k)
            if isinstance(value, str | int) and str(value).strip():
                return str(value).strip()
        return None

    run_id = _first("runledger.run_id", "run_id")
    session_id = _first("runledger.session_id", "session_id", "session")
    if not run_id and not session_id:
        return
    try:
        held = await find_runaway_hold(
            await get_redis(), db, workspace_id, run_id=run_id, session_id=session_id
        )
    except Exception:
        log.warning("gateway_runaway_hold_check_failed", workspace_id=str(workspace_id))
        return
    if held is None:
        return
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=f"Runaway protection: {held} is on hold",
        headers={"X-Cost-Cap-Reason": "runaway_hold", "Retry-After": "300"},
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
