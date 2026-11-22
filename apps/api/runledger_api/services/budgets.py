"""
Budget service layer — Redis helpers, hot-path check, notification dispatch.

All functions are pure async with no FastAPI dependencies so they can be
imported directly from Celery workers.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx
import structlog
from redis.asyncio import Redis
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models import AgentRun, ProviderCall
from runledger_api.models.access_groups import AccessGroup, AccessGroupMember
from runledger_api.models.budgets import (
    Budget,
    BudgetBreach,
    BudgetNotification,
    BudgetNotificationDelivery,
)
from runledger_api.models.tenant import ApiKey, Workspace
from runledger_api.schemas.budgets import BudgetCheckResponse, BudgetUserBreakdownEntry
from runledger_api.services import kafka_export

log = structlog.get_logger()

_BUDGET_CACHE_TTL = 300  # seconds


# ── Period key helpers ────────────────────────────────────────────────────────


def _period_key(period_type: str, dt: datetime) -> str:
    """Return the Redis period string for a given datetime."""
    if period_type == "daily":
        return dt.strftime("%Y-%m-%d")
    if period_type == "monthly":
        return dt.strftime("%Y-%m")
    return "total"


def _spend_key(budget_id: uuid.UUID, period_key: str) -> str:
    return f"rl:budget:{budget_id}:spend:{period_key}"


def _workspace_budgets_cache_key(workspace_id: uuid.UUID) -> str:
    return f"rl:workspace:{workspace_id}:budgets"


# ── Redis spend counter ───────────────────────────────────────────────────────


async def incr_budget_spend(
    redis: Redis,
    budget_id: uuid.UUID,
    period_type: str,
    cost_usd: Decimal,
    at: datetime | None = None,
) -> None:
    """INCRBYFLOAT on the spend key for the period containing ``at`` (default now)."""
    pk = _period_key(period_type, at or datetime.now(UTC))
    key = _spend_key(budget_id, pk)
    await redis.incrbyfloat(key, float(cost_usd))
    # For daily / monthly keys, set expiry so stale counters are cleaned up.
    if period_type == "daily":
        await redis.expire(key, 86400 * 2)  # 2 days
    elif period_type == "monthly":
        await redis.expire(key, 86400 * 35)  # ~5 weeks


async def get_budget_spend(
    redis: Redis,
    budget_id: uuid.UUID,
    period_type: str,
    at: datetime | None = None,
) -> Decimal:
    """GET the spend counter for the period containing ``at`` (default now); 0 if missing."""
    pk = _period_key(period_type, at or datetime.now(UTC))
    key = _spend_key(budget_id, pk)
    value = await redis.get(key)
    if value is None:
        return Decimal(0)
    return Decimal(str(value))


# ── Workspace budgets cache ───────────────────────────────────────────────────


async def get_workspace_budgets_cached(
    redis: Redis,
    db: AsyncSession,
    workspace_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """
    Return active budget defs from Redis cache (TTL 300 s).
    On miss: query Postgres, serialise, and cache the result.
    """
    cache_key = _workspace_budgets_cache_key(workspace_id)
    cached = await redis.get(cache_key)
    if cached is not None:
        return json.loads(cached)  # type: ignore[no-any-return]

    result = await db.execute(
        select(Budget).where(
            Budget.workspace_id == workspace_id,
            Budget.is_active.is_(True),
        )
    )
    budgets: list[Budget] = list(result.scalars())

    from runledger_api.models.budget_overrides import BudgetOverride  # noqa: PLC0415

    now = datetime.now(UTC)
    budget_ids = [b.id for b in budgets]
    overrides_map: dict[uuid.UUID, Decimal] = {}
    if budget_ids:
        override_result = await db.execute(
            select(BudgetOverride.budget_id, BudgetOverride.override_limit_usd).where(
                BudgetOverride.budget_id.in_(budget_ids),
                BudgetOverride.status == "active",
                BudgetOverride.starts_at <= now,
                BudgetOverride.expires_at > now,
            )
        )
        for row in override_result.all():
            budget_id = getattr(row, "budget_id", None)
            override_limit = getattr(row, "override_limit_usd", None)
            if budget_id is None and override_limit is None:
                try:
                    budget_id, override_limit = row
                except TypeError:
                    continue
            elif budget_id is None or override_limit is None:
                budget_id, override_limit = row
            overrides_map[budget_id] = override_limit

    serialised = [
        {
            "id": str(b.id),
            "workspace_id": str(b.workspace_id),
            "scope_type": b.scope_type,
            "scope_id": b.scope_id,
            "period_type": b.period_type,
            "limit_usd": str(overrides_map.get(b.id, b.limit_usd)),
            "action": b.action,
            "downgrade_to_model": b.downgrade_to_model,
        }
        for b in budgets
    ]
    await redis.set(cache_key, json.dumps(serialised), ex=_BUDGET_CACHE_TTL)
    return serialised


async def invalidate_workspace_budgets_cache(
    redis: Redis,
    workspace_id: uuid.UUID,
) -> None:
    """Delete the workspace budget cache key (called on create/delete)."""
    cache_key = _workspace_budgets_cache_key(workspace_id)
    await redis.delete(cache_key)


# ── Budget breakdown ─────────────────────────────────────────────────────────


async def get_budget_breakdown(
    budget: Budget,
    workspace: Workspace,
    db: AsyncSession,
    end_user_id: str | None = None,
) -> list[BudgetUserBreakdownEntry]:
    """Return spend breakdown by end user for a budget."""
    import calendar
    from datetime import datetime

    import sqlalchemy as sa

    now = datetime.now(UTC)
    if budget.period_type == "daily":
        period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = now
    elif budget.period_type == "monthly":
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_day = calendar.monthrange(now.year, now.month)[1]
        period_end = now.replace(day=last_day, hour=23, minute=59, second=59, microsecond=999999)
    else:
        period_start = datetime.min.replace(tzinfo=UTC)
        period_end = now

    filters: list[sa.ColumnElement[bool]] = [
        ProviderCall.workspace_id == workspace.id,
        func.date(ProviderCall.created_at) >= period_start.date(),
        func.date(ProviderCall.created_at) <= period_end.date(),
        ProviderCall.status == "success",
    ]

    if budget.scope_type == "end_user" and budget.scope_id:
        filters.append(ProviderCall.end_user_id == budget.scope_id)
    elif budget.scope_type == "access_group" and budget.scope_id:
        member_ids = select(sa.cast(AccessGroupMember.user_id, sa.String)).where(
            AccessGroupMember.group_id == uuid.UUID(budget.scope_id)
        )
        filters.append(ProviderCall.end_user_id.in_(member_ids))
    elif budget.scope_type == "api_key" and budget.scope_id:
        filters.append(ProviderCall.api_key_id == uuid.UUID(budget.scope_id))
    elif budget.scope_type == "feature_tag" and budget.scope_id:
        filters.append(AgentRun.feature_tag == budget.scope_id)
    elif budget.scope_type == "app" and budget.scope_id:
        filters.append(AgentRun.application_id == uuid.UUID(budget.scope_id))

    if end_user_id is not None:
        filters.append(ProviderCall.end_user_id == end_user_id)

    rows_result = await db.execute(
        select(
            ProviderCall.end_user_id,
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost_usd"),
            func.count(ProviderCall.id).label("call_count"),
            func.count(func.distinct(ProviderCall.run_id)).label("run_count"),
        )
        .join(AgentRun, ProviderCall.run_id == AgentRun.id)
        .where(*filters)
        .group_by(ProviderCall.end_user_id)
        .order_by(func.sum(ProviderCall.cost_usd).desc())
    )

    rows = rows_result.all()
    total_cost = sum((row.cost_usd or Decimal(0) for row in rows), Decimal(0))

    breakdown: list[BudgetUserBreakdownEntry] = []
    for row in rows:
        if row.end_user_id is not None:
            pct = (row.cost_usd / total_cost * Decimal(100)) if total_cost > 0 else Decimal(0)
            breakdown.append(
                BudgetUserBreakdownEntry(
                    end_user_id=row.end_user_id,
                    cost_usd=row.cost_usd,
                    run_count=int(row.run_count or 0),
                    call_count=int(row.call_count or 0),
                    pct_of_total=pct.quantize(Decimal("0.01")),
                )
            )

    return breakdown


# ── Scope matching ────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class BudgetScope:
    """The scope dimensions of one model call, used to pick the budgets it counts against."""

    end_user_id: str | None = None
    feature_tag: str | None = None
    app_id: str | None = None
    api_key_id: str | None = None
    access_group_ids: tuple[str, ...] = ()
    provider_profile_id: str | None = None


def _matching_budgets(
    budgets: list[dict[str, Any]],
    end_user_id: str | None = None,
    feature_tag: str | None = None,
    app_id: str | None = None,
    api_key_id: str | None = None,
    access_group_id: str | None = None,
    provider_profile_id: str | None = None,
    *,
    access_group_ids: Iterable[str] = (),
) -> list[dict[str, Any]]:
    """
    Filter budget list to those that match this specific call.

    - workspace scope: always matches
    - end_user scope: matches when scope_id == end_user_id
    - feature_tag scope: matches when scope_id == feature_tag
    - app scope: matches when scope_id == app_id
    - api_key scope: matches when scope_id == api_key_id
    - access_group scope: matches when scope_id is one of the caller's groups
      (``access_group_id`` or any of ``access_group_ids``)
    - provider_profile scope: matches when scope_id == provider_profile_id
    """
    groups = {g for g in access_group_ids if g}
    if access_group_id:
        groups.add(access_group_id)
    matched = []
    for b in budgets:
        scope_type = b["scope_type"]
        if (
            (scope_type == "workspace")
            or (scope_type == "end_user" and end_user_id and b["scope_id"] == end_user_id)
            or (scope_type == "feature_tag" and feature_tag and b["scope_id"] == feature_tag)
            or (scope_type == "app" and app_id and b["scope_id"] == app_id)
            or (scope_type == "api_key" and api_key_id and b["scope_id"] == api_key_id)
            or (scope_type == "access_group" and b["scope_id"] in groups)
            or (
                scope_type == "provider_profile"
                and provider_profile_id
                and b["scope_id"] == provider_profile_id
            )
        ):
            matched.append(b)
    return matched


# ── Hot-path check ────────────────────────────────────────────────────────────


async def check_budgets(
    redis: Redis,
    db: AsyncSession,
    workspace_id: uuid.UUID,
    end_user_id: str | None,
    feature_tag: str | None,
    app_id: str | None = None,
    api_key_id: str | None = None,
    access_group_id: str | None = None,
    provider_profile_id: str | None = None,
    *,
    access_group_ids: Iterable[str] = (),
    budgets: list[dict[str, Any]] | None = None,
) -> BudgetCheckResponse:
    """
    Hot-path budget check: reads cache + Redis counters only.

    Returns BudgetCheckResponse with allowed=False when a blocking or
    downgrade budget is exceeded.  Notify-only budgets do not block.
    """
    if budgets is None:
        budgets = await get_workspace_budgets_cached(redis, db, workspace_id)
    matched = _matching_budgets(
        budgets,
        end_user_id,
        feature_tag,
        app_id,
        api_key_id,
        access_group_id,
        provider_profile_id,
        access_group_ids=access_group_ids,
    )
    return await _evaluate_matched(redis, matched)


async def _evaluate_matched(redis: Redis, matched: list[dict[str, Any]]) -> BudgetCheckResponse:
    throttled = False
    throttle_budget_id: str | None = None

    for b in matched:
        budget_id = uuid.UUID(b["id"])
        spend = await get_budget_spend(redis, budget_id, b["period_type"])
        limit = Decimal(b["limit_usd"])

        if spend >= limit:
            action = b["action"]
            if action == "block":
                return BudgetCheckResponse(
                    allowed=False,
                    action="block",
                    budget_id=b["id"],
                )
            if action == "downgrade":
                return BudgetCheckResponse(
                    allowed=False,
                    action="downgrade",
                    budget_id=b["id"],
                    downgrade_model=b.get("downgrade_to_model"),
                )
            if action == "fallback":
                return BudgetCheckResponse(
                    allowed=False,
                    action="fallback",
                    budget_id=b["id"],
                    fallback_model=b.get("downgrade_to_model"),
                )
            if action == "throttle":
                throttled = True
                throttle_budget_id = b["id"]
            else:
                log.info(
                    "budget_notify_threshold_exceeded",
                    budget_id=b["id"],
                    spend=str(spend),
                    limit=str(limit),
                )

    if throttled:
        return BudgetCheckResponse(
            allowed=True,
            action="throttle",
            budget_id=throttle_budget_id,
            throttled=True,
        )

    return BudgetCheckResponse(allowed=True)


# ── Scope resolution ──────────────────────────────────────────────────────────


async def resolve_access_group_ids(
    db: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID
) -> tuple[str, ...]:
    """Active access groups in the workspace that the user belongs to."""
    rows = await db.execute(
        select(AccessGroup.id)
        .join(AccessGroupMember, AccessGroupMember.group_id == AccessGroup.id)
        .where(
            AccessGroup.workspace_id == workspace_id,
            AccessGroup.is_active.is_(True),
            AccessGroupMember.user_id == user_id,
        )
    )
    return tuple(str(group_id) for group_id in rows.scalars())


async def resolve_provider_profile_id(
    db: AsyncSession, workspace_id: uuid.UUID, provider: str | None, model: str | None
) -> str | None:
    """The provider-pricing row (provider profile) a call to provider/model is billed under.

    Workspace-specific rows win over global rows, then the most recent effective date.
    """
    if not model:
        return None
    from runledger_api.models.metering import ProviderPricing  # noqa: PLC0415

    stmt = select(ProviderPricing.id).where(
        ProviderPricing.model == model,
        (ProviderPricing.workspace_id == workspace_id) | (ProviderPricing.workspace_id.is_(None)),
    )
    if provider:
        stmt = stmt.where(ProviderPricing.provider == provider)
    stmt = stmt.order_by(
        ProviderPricing.workspace_id.is_(None).asc(),
        ProviderPricing.effective_from.desc().nulls_last(),
    ).limit(1)
    pricing_id = (await db.execute(stmt)).scalar_one_or_none()
    return str(pricing_id) if pricing_id else None


def _has_scope(budgets: list[dict[str, Any]], scope_type: str) -> bool:
    return any(b.get("scope_type") == scope_type for b in budgets)


async def build_budget_scope(
    db: AsyncSession,
    budgets: list[dict[str, Any]],
    *,
    workspace_id: uuid.UUID,
    api_key_id: uuid.UUID | str | None = None,
    end_user_id: str | None = None,
    feature_tag: str | None = None,
    app_id: uuid.UUID | str | None = None,
    provider: str | None = None,
    model: str | None = None,
    principal_user_id: uuid.UUID | None = None,
) -> BudgetScope:
    """Resolve every scope dimension a call can be budgeted on.

    Access-group membership is resolved from the calling user — the session key's
    owner, a user-owned key's creator, or an ``end_user_id`` that is a workspace
    member's id or email (the same mapping the gateway uses for guardrail
    profiles). The DB lookups only run when the workspace has budgets of that scope.
    """
    group_ids: tuple[str, ...] = ()
    if _has_scope(budgets, "access_group"):
        user_id = principal_user_id
        if user_id is None:
            from runledger_api.services.sessions import resolve_principal_user_id  # noqa: PLC0415

            workspace = await db.get(Workspace, workspace_id)
            api_key = None
            if api_key_id is not None:
                api_key = await db.get(ApiKey, uuid.UUID(str(api_key_id)))
            if workspace is not None:
                user_id = await resolve_principal_user_id(
                    db, api_key=api_key, end_user_id=end_user_id, workspace=workspace
                )
        if user_id is not None:
            group_ids = await resolve_access_group_ids(db, workspace_id, user_id)

    profile_id = None
    if _has_scope(budgets, "provider_profile"):
        profile_id = await resolve_provider_profile_id(db, workspace_id, provider, model)

    return BudgetScope(
        end_user_id=end_user_id,
        feature_tag=feature_tag,
        app_id=str(app_id) if app_id else None,
        api_key_id=str(api_key_id) if api_key_id else None,
        access_group_ids=group_ids,
        provider_profile_id=profile_id,
    )


def _match_scope(budgets: list[dict[str, Any]], scope: BudgetScope) -> list[dict[str, Any]]:
    return _matching_budgets(
        budgets,
        end_user_id=scope.end_user_id,
        feature_tag=scope.feature_tag,
        app_id=scope.app_id,
        api_key_id=scope.api_key_id,
        provider_profile_id=scope.provider_profile_id,
        access_group_ids=scope.access_group_ids,
    )


# ── Gateway enforcement ───────────────────────────────────────────────────────


async def check_request_budgets(
    redis: Redis,
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    api_key_id: uuid.UUID | None,
    end_user_id: str | None,
    feature_tag: str | None,
    principal_user_id: uuid.UUID | None = None,
) -> BudgetCheckResponse:
    """Route-independent budget check for a gateway request.

    Covers workspace, end_user, feature_tag, api_key and access_group budgets.
    Provider-profile budgets depend on the route and are checked per route with
    :func:`check_provider_profile_budgets`.
    """
    budgets = await get_workspace_budgets_cached(redis, db, workspace_id)
    request_budgets = [b for b in budgets if b.get("scope_type") != "provider_profile"]
    if not request_budgets:
        return BudgetCheckResponse(allowed=True)
    scope = await build_budget_scope(
        db,
        request_budgets,
        workspace_id=workspace_id,
        api_key_id=api_key_id,
        end_user_id=end_user_id,
        feature_tag=feature_tag,
        principal_user_id=principal_user_id,
    )
    return await _evaluate_matched(redis, _match_scope(request_budgets, scope))


async def check_provider_profile_budgets(
    redis: Redis,
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    provider: str | None,
    model: str | None,
) -> BudgetCheckResponse:
    """Check the provider-profile budgets that apply to one candidate route."""
    budgets = await get_workspace_budgets_cached(redis, db, workspace_id)
    profile_budgets = [b for b in budgets if b.get("scope_type") == "provider_profile"]
    if not profile_budgets:
        return BudgetCheckResponse(allowed=True)
    profile_id = await resolve_provider_profile_id(db, workspace_id, provider, model)
    if profile_id is None:
        return BudgetCheckResponse(allowed=True)
    matched = [b for b in profile_budgets if b.get("scope_id") == profile_id]
    return await _evaluate_matched(redis, matched)


async def check_budget_throttle(redis: Redis, budget_id: str, rpm_limit: int) -> bool:
    """Count one request against a throttled budget; True when it is over the limit.

    A budget with ``action="throttle"`` that has reached its limit slows traffic to
    ``rpm_limit`` requests per minute instead of blocking it outright.
    """
    epoch_minute = int(datetime.now(UTC).timestamp()) // 60
    key = f"rl:budget:{budget_id}:throttle:{epoch_minute}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, 60)
    return int(count) > rpm_limit


# ── Spend recording ───────────────────────────────────────────────────────────

_COUNTED_TTL = 86400 * 40  # longer than the longest period window (monthly)


def _flag_ttl(period_type: str) -> int:
    if period_type == "daily":
        return 86400 * 2
    return 86400 * 35


async def record_budget_spend(
    db: AsyncSession,
    redis: Redis,
    *,
    workspace_id: uuid.UUID,
    provider_call_id: uuid.UUID,
    cost_usd: Decimal | None,
    run_id: uuid.UUID | None = None,
    api_key_id: uuid.UUID | str | None = None,
    end_user_id: str | None = None,
    feature_tag: str | None = None,
    app_id: uuid.UUID | str | None = None,
    provider: str | None = None,
    model: str | None = None,
    principal_user_id: uuid.UUID | None = None,
    occurred_at: datetime | None = None,
) -> int:
    """Add one priced model call to every budget it counts against.

    Spend lands in the budget period of ``occurred_at`` (the call's own time), so a
    call priced late by enrichment is not counted in a later period.

    This is the single write path for budget spend counters. It is called wherever
    a provider call gets its cost: gateway finalize, ingest (SDK/OTLP calls that
    carry a cost) and the metering worker (calls priced after the fact).

    - Idempotent per provider call: a call is counted at most once, so ingest
      retries, re-enrichment and ``replay_backfill`` cannot double count.
    - Emits ``budget.threshold_crossed`` at 80% and records a breach (with
      notifications) when the limit is reached — each at most once per budget period.
    - Does not commit; the caller owns the transaction.

    Returns the number of budgets the call was counted against.
    """
    if cost_usd is None or cost_usd <= 0:
        return 0
    budgets = await get_workspace_budgets_cached(redis, db, workspace_id)
    if not budgets:
        return 0
    counted_key = f"rl:budget:counted:{provider_call_id}"
    if not await redis.set(counted_key, "1", nx=True, ex=_COUNTED_TTL):
        return 0
    try:
        scope = await build_budget_scope(
            db,
            budgets,
            workspace_id=workspace_id,
            api_key_id=api_key_id,
            end_user_id=end_user_id,
            feature_tag=feature_tag,
            app_id=app_id,
            provider=provider,
            model=model,
            principal_user_id=principal_user_id,
        )
        matched = _match_scope(budgets, scope)
        for b in matched:
            budget_id = uuid.UUID(b["id"])
            period_type = b["period_type"]
            await incr_budget_spend(redis, budget_id, period_type, cost_usd, occurred_at)
            spend = await get_budget_spend(redis, budget_id, period_type, occurred_at)
            limit = Decimal(b["limit_usd"])
            pk = _period_key(period_type, occurred_at or datetime.now(UTC))
            if limit <= 0:
                continue
            if limit * Decimal("0.80") <= spend < limit and await redis.set(
                f"rl:budget:{budget_id}:threshold:{pk}", "1", nx=True, ex=_flag_ttl(period_type)
            ):
                await kafka_export.publish_event(
                    db,
                    workspace_id=workspace_id,
                    event_type="budget.threshold_crossed",
                    payload={
                        "budget_id": str(budget_id),
                        "run_id": str(run_id) if run_id else None,
                        "trace_id": None,
                        "provider_call_id": str(provider_call_id),
                        "scope_type": b.get("scope_type"),
                        "scope_id": b.get("scope_id"),
                        "period_type": period_type,
                        "limit_usd": b.get("limit_usd"),
                        "spend_usd": str(spend),
                        "threshold_pct": "80",
                        "idempotency_key": f"budget-threshold:{budget_id}:{pk}",
                        "source": "runledger.budgets",
                        "event_summary": "Budget threshold crossed",
                    },
                )
            if spend >= limit and await redis.set(
                f"rl:budget:{budget_id}:breached:{pk}", "1", nx=True, ex=_flag_ttl(period_type)
            ):
                await fire_breach(db, redis, b, spend, b["action"], commit=False)
        return len(matched)
    except Exception:
        # Let a later attempt (retry / re-enrichment) count this call.
        await redis.delete(counted_key)
        raise


# ── Model-specific budget check ──────────────────────────────────────────────


def _model_spend_key(key_id: str, model: str, period_key: str) -> str:
    return f"rl:mbudget:{key_id}:{model}:{period_key}"


def _model_matches(pattern: str, model: str) -> bool:
    """Simple glob matching: supports trailing * only (e.g. 'gpt-4*')."""
    if pattern.endswith("*"):
        return model.startswith(pattern[:-1])
    return pattern == model


async def check_model_budgets(
    redis: Redis,
    db: AsyncSession,
    api_key_id: uuid.UUID,
    model: str,
) -> BudgetCheckResponse:
    from runledger_api.models.model_budgets import ModelBudget  # noqa: PLC0415

    cache_key = f"rl:mbudgets:{api_key_id}"
    cached = await redis.get(cache_key)
    if cached is not None:
        budgets = json.loads(cached)
    else:
        result = await db.execute(
            select(ModelBudget).where(
                ModelBudget.api_key_id == api_key_id,
                ModelBudget.is_active.is_(True),
            )
        )
        rows = list(result.scalars())
        budgets = [
            {
                "id": str(mb.id),
                "model_pattern": mb.model_pattern,
                "max_spend_usd": str(mb.max_spend_usd) if mb.max_spend_usd else None,
                "period_type": mb.period_type,
                "action": mb.action,
            }
            for mb in rows
        ]
        await redis.set(cache_key, json.dumps(budgets), ex=_BUDGET_CACHE_TTL)

    for b in budgets:
        if not _model_matches(b["model_pattern"], model):
            continue
        if b["max_spend_usd"] is None:
            continue

        pk = _period_key(b["period_type"], datetime.now(UTC))
        key = _model_spend_key(str(api_key_id), model, pk)
        raw = await redis.get(key)
        spend = Decimal(str(raw)) if raw else Decimal(0)
        limit = Decimal(b["max_spend_usd"])

        if spend >= limit:
            action = b["action"]
            if action == "block":
                return BudgetCheckResponse(allowed=False, action="block", budget_id=b["id"])
            if action in ("downgrade", "fallback"):
                return BudgetCheckResponse(allowed=False, action=action, budget_id=b["id"])

    return BudgetCheckResponse(allowed=True)


async def incr_model_budget_spend(
    redis: Redis,
    api_key_id: uuid.UUID,
    model: str,
    period_type: str,
    cost_usd: Decimal,
) -> None:
    pk = _period_key(period_type, datetime.now(UTC))
    key = _model_spend_key(str(api_key_id), model, pk)
    await redis.incrbyfloat(key, float(cost_usd))
    if period_type == "daily":
        await redis.expire(key, 86400 * 2)
    elif period_type == "monthly":
        await redis.expire(key, 86400 * 35)


# ── Breach recording + notification dispatch ──────────────────────────────────


async def fire_breach(
    db: AsyncSession,
    redis: Redis,
    budget_dict: dict[str, Any],
    spend: Decimal,
    action_taken: str,
    *,
    commit: bool = True,
) -> None:
    """
    Record a breach in Postgres and send notifications.

    budget_dict is the serialised dict from the Redis cache (not the ORM obj).
    Pass ``commit=False`` when the caller owns the transaction.
    """
    budget_id = uuid.UUID(budget_dict["id"])

    breach = BudgetBreach(
        budget_id=budget_id,
        spend_at_breach_usd=spend,
        action_taken=action_taken,
    )
    db.add(breach)
    await db.flush()  # get breach.id + occurred_at

    # Fetch active notifications for this workspace
    workspace_id_str = budget_dict.get("workspace_id")
    if workspace_id_str:
        workspace_id = uuid.UUID(workspace_id_str)
        try:
            await kafka_export.publish_event(
                db,
                workspace_id=workspace_id,
                event_type="budget.breached",
                payload={
                    "budget_id": str(budget_id),
                    "run_id": str(breach.id),
                    "trace_id": None,
                    "scope_type": budget_dict.get("scope_type"),
                    "scope_id": budget_dict.get("scope_id"),
                    "period_type": budget_dict.get("period_type"),
                    "limit_usd": budget_dict.get("limit_usd"),
                    "spend_usd": str(spend),
                    "action_taken": action_taken,
                    "occurred_at": breach.occurred_at.isoformat()
                    if breach.occurred_at
                    else datetime.now(UTC).isoformat(),
                    "idempotency_key": f"budget-breached:{budget_id}:{breach.id}",
                    "source": "runledger.budgets",
                    "event_summary": "Budget breached",
                },
            )
        except Exception:
            log.exception("kafka_export.budget_breached_failed", budget_id=str(budget_id))
        result = await db.execute(
            select(BudgetNotification).where(
                BudgetNotification.workspace_id == workspace_id,
                BudgetNotification.is_active.is_(True),
                BudgetNotification.events.contains(["budget.breach"]),
            )
        )
        notifications: list[BudgetNotification] = list(result.scalars())

        payload = {
            "event": "budget.breach",
            "budget_id": str(budget_id),
            "scope_type": budget_dict.get("scope_type"),
            "scope_id": budget_dict.get("scope_id"),
            "period_type": budget_dict.get("period_type"),
            "limit_usd": budget_dict.get("limit_usd"),
            "spend_usd": str(spend),
            "action_taken": action_taken,
            "occurred_at": datetime.now(UTC).isoformat(),
        }

        for notification in notifications:
            try:
                result = await send_notification(notification, payload)
                db.add(
                    build_delivery_record(
                        notification,
                        event_type=str(payload["event"]),
                        status=str(result["status"]),
                        response_status=result.get("response_status"),
                        error_detail=result.get("error_detail"),
                        delivered_at=result.get("delivered_at"),
                    )
                )
                # Mark notified_at on the breach
                await db.execute(
                    update(BudgetBreach)
                    .where(BudgetBreach.id == breach.id)
                    .values(notified_at=datetime.now(UTC))
                )
            except Exception as exc:
                db.add(
                    build_delivery_record(
                        notification,
                        event_type=str(payload["event"]),
                        status="failed",
                        error_detail=str(exc),
                    )
                )
                log.warning(
                    "budget_notification_failed",
                    notification_id=str(notification.id),
                    error=str(exc),
                )

    if commit:
        await db.commit()
    else:
        await db.flush()
    log.info(
        "budget_breach_recorded",
        budget_id=str(budget_id),
        spend=str(spend),
        action_taken=action_taken,
    )


async def send_notification(
    notification: BudgetNotification,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Dispatch a notification via Slack Block Kit or HMAC-signed generic webhook.

    For Slack channels: POST Block Kit JSON to the destination_url (no HMAC).
    For all other channels: HMAC-SHA256 signed JSON POST.
    """
    if notification.channel == "slack":
        from runledger_api.services.notifications import (
            build_budget_breach_blocks,
            send_slack_message,
        )

        blocks = build_budget_breach_blocks(
            budget_id=payload.get("budget_id", ""),
            scope_type=payload.get("scope_type"),
            scope_id=payload.get("scope_id"),
            spend_usd=payload.get("spend_usd", "0"),
            limit_usd=payload.get("limit_usd", "0"),
            action=payload.get("action_taken"),
        )
        fallback = (
            f"Budget breach: ${payload.get('spend_usd', '0')} "
            f"/ ${payload.get('limit_usd', '0')} limit"
        )
        await send_slack_message(notification.destination_url, blocks, fallback)
        return {
            "status": "success",
            "response_status": 200,
            "error_detail": None,
            "delivered_at": datetime.now(UTC),
            "event_type": str(payload.get("event", "budget.breach")),
        }

    from runledger_api.services.egress import check_url  # noqa: PLC0415

    check_url(notification.destination_url)  # SSRF: re-checked at send time
    body = json.dumps(payload, sort_keys=True).encode()
    from runledger_api.services.billing_signing import webhook_secret  # noqa: PLC0415

    secret = webhook_secret(notification.id, int(getattr(notification, "signing_version", 1) or 1))
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            notification.destination_url,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-RunLedger-Signature": f"sha256={sig}",
                "X-RunLedger-Event": payload.get("event", "budget.breach"),
            },
        )
        response.raise_for_status()
    return {
        "status": "success",
        "response_status": response.status_code,
        "error_detail": None,
        "delivered_at": datetime.now(UTC),
        "event_type": str(payload.get("event", "budget.breach")),
    }


def build_delivery_record(
    notification: BudgetNotification,
    *,
    event_type: str,
    attempt: int = 1,
    status: str,
    response_status: int | None = None,
    error_detail: str | None = None,
    delivered_at: datetime | None = None,
) -> BudgetNotificationDelivery:
    return BudgetNotificationDelivery(
        notification_id=notification.id,
        workspace_id=notification.workspace_id,
        event_type=event_type,
        attempt=attempt,
        status=status,
        response_status=response_status,
        error_detail=error_detail,
        delivered_at=delivered_at,
    )
