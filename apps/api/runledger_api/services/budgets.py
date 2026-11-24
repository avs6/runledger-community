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
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx
import structlog
from redis.asyncio import Redis
from sqlalchemy import Text as sa_Text
from sqlalchemy import func, select, update
from sqlalchemy import literal as sa_literal
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models import AgentRun, ProviderCall
from runledger_api.models.access_groups import AccessGroup, AccessGroupMember
from runledger_api.models.budgets import (
    Budget,
    BudgetBreach,
    BudgetNotification,
    BudgetNotificationDelivery,
    BudgetSpend,
    BudgetSpendCall,
)
from runledger_api.models.tenant import ApiKey, Workspace
from runledger_api.schemas.budgets import BudgetCheckResponse, BudgetUserBreakdownEntry
from runledger_api.services import kafka_export

log = structlog.get_logger()

_BUDGET_CACHE_TTL = 300  # seconds


# ── Periods ───────────────────────────────────────────────────────────────────

PERIOD_TYPES = ("daily", "weekly", "monthly", "total")


def _period_key(period_type: str, dt: datetime) -> str:
    """The period a timestamp falls in: ``2026-11-22``, ``2026-W47``, ``2026-11`` or ``total``."""
    if period_type == "daily":
        return dt.strftime("%Y-%m-%d")
    if period_type == "weekly":
        year, week, _ = dt.isocalendar()
        return f"{year}-W{week:02d}"
    if period_type == "monthly":
        return dt.strftime("%Y-%m")
    return "total"


def period_window(period_type: str, at: datetime) -> tuple[datetime | None, datetime | None]:
    """``[start, end)`` of the UTC period containing ``at``; ``(None, None)`` for total."""
    at = at.astimezone(UTC)
    if period_type == "daily":
        start = at.replace(hour=0, minute=0, second=0, microsecond=0)
        return start, start + timedelta(days=1)
    if period_type == "weekly":
        day = at.replace(hour=0, minute=0, second=0, microsecond=0)
        start = day - timedelta(days=day.weekday())
        return start, start + timedelta(days=7)
    if period_type == "monthly":
        start = at.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = (
            start.replace(year=start.year + 1, month=1)
            if start.month == 12
            else start.replace(month=start.month + 1)
        )
        return start, end
    return None, None


def _spend_key(budget_id: uuid.UUID, period_key: str) -> str:
    return f"rl:budget:{budget_id}:spend:{period_key}"


def _workspace_budgets_cache_key(workspace_id: uuid.UUID) -> str:
    return f"rl:workspace:{workspace_id}:budgets"


# ── Durable spend (Postgres) ──────────────────────────────────────────────────
#
# budget_spend is the source of truth (review cd:B-05). Redis holds a short-lived
# cache of each period's total for the hot path: it is written through on every
# increment and expires after _SPEND_CACHE_TTL, so an evicted or stale key only
# costs one Postgres read and a rolled-back increment heals within the TTL.

_SPEND_CACHE_TTL = 300  # seconds


async def _db_claim_call(
    db: AsyncSession, workspace_id: uuid.UUID, provider_call_id: uuid.UUID
) -> bool:
    """Mark a provider call as counted; False when it already was (idempotency)."""
    stmt = (
        pg_insert(BudgetSpendCall)
        .values(provider_call_id=provider_call_id, workspace_id=workspace_id)
        .on_conflict_do_nothing(index_elements=["provider_call_id"])
        .returning(BudgetSpendCall.provider_call_id)
    )
    return (await db.execute(stmt)).scalar_one_or_none() is not None


async def _db_add_spend(
    db: AsyncSession, budget_id: uuid.UUID, period_key: str, cost_usd: Decimal
) -> Decimal:
    """Atomically add ``cost_usd`` to the period's spend; returns the new total."""
    stmt = (
        pg_insert(BudgetSpend)
        .values(budget_id=budget_id, period_key=period_key, spend_usd=cost_usd, call_count=1)
        .on_conflict_do_update(
            index_elements=["budget_id", "period_key"],
            set_={
                "spend_usd": BudgetSpend.spend_usd + cost_usd,
                "call_count": BudgetSpend.call_count + 1,
                "updated_at": func.now(),
            },
        )
        .returning(BudgetSpend.spend_usd)
    )
    return Decimal((await db.execute(stmt)).scalar_one())


async def _db_load_spend(db: AsyncSession, budget_id: uuid.UUID, period_key: str) -> Decimal:
    value = (
        await db.execute(
            select(BudgetSpend.spend_usd).where(
                BudgetSpend.budget_id == budget_id, BudgetSpend.period_key == period_key
            )
        )
    ).scalar_one_or_none()
    return Decimal(value) if value is not None else Decimal(0)


async def _db_set_spend(
    db: AsyncSession, budget_id: uuid.UUID, period_key: str, spend_usd: Decimal, calls: int
) -> None:
    """Overwrite a period's spend (reconciliation from provider_calls)."""
    stmt = (
        pg_insert(BudgetSpend)
        .values(budget_id=budget_id, period_key=period_key, spend_usd=spend_usd, call_count=calls)
        .on_conflict_do_update(
            index_elements=["budget_id", "period_key"],
            set_={"spend_usd": spend_usd, "call_count": calls, "updated_at": func.now()},
        )
    )
    await db.execute(stmt)


async def _db_mark_once(db: AsyncSession, budget_id: uuid.UUID, period_key: str, flag: str) -> bool:
    """Set ``threshold_notified_at`` / ``breached_at`` once per period; True the first time."""
    column = getattr(BudgetSpend, flag)
    stmt = (
        update(BudgetSpend)
        .where(
            BudgetSpend.budget_id == budget_id,
            BudgetSpend.period_key == period_key,
            column.is_(None),
        )
        .values({flag: func.now()})
        .returning(BudgetSpend.budget_id)
    )
    return (await db.execute(stmt)).scalar_one_or_none() is not None


async def _cache_spend(redis: Redis, budget_id: uuid.UUID, period_key: str, value: Decimal) -> None:
    try:
        await redis.set(_spend_key(budget_id, period_key), str(value), ex=_SPEND_CACHE_TTL)
    except Exception:
        log.warning("budget_spend_cache_write_failed", budget_id=str(budget_id))


async def get_budget_spend(
    redis: Redis,
    budget_id: uuid.UUID,
    period_type: str,
    at: datetime | None = None,
    *,
    db: AsyncSession | None = None,
) -> Decimal:
    """Spend for the period containing ``at`` (default now).

    Redis first; on a miss (expired, evicted, Redis restarted) the Postgres total is
    loaded and cached. Without ``db`` a miss reads as 0 (tests, cache-only callers).
    """
    pk = _period_key(period_type, at or datetime.now(UTC))
    try:
        value = await redis.get(_spend_key(budget_id, pk))
    except Exception:
        value = None
    if value is not None:
        return Decimal(str(value))
    if db is None:
        return Decimal(0)
    spend = await _db_load_spend(db, budget_id, pk)
    await _cache_spend(redis, budget_id, pk, spend)
    return spend


async def set_budget_spend(
    db: AsyncSession,
    redis: Redis,
    budget_id: uuid.UUID,
    period_type: str,
    spend_usd: Decimal,
    calls: int,
    at: datetime | None = None,
) -> None:
    """Reconcile a period's spend to a recomputed total (daily sync)."""
    pk = _period_key(period_type, at or datetime.now(UTC))
    await _db_set_spend(db, budget_id, pk, spend_usd, calls)
    await _cache_spend(redis, budget_id, pk, spend_usd)


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
            "api_key_id": str(b.api_key_id) if getattr(b, "api_key_id", None) else None,
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
    import sqlalchemy as sa

    start, end = period_window(budget.period_type, datetime.now(UTC))
    filters: list[sa.ColumnElement[bool]] = [
        ProviderCall.workspace_id == workspace.id,
        ProviderCall.status == "success",
    ]
    if start is not None and end is not None:
        filters += [ProviderCall.created_at >= start, ProviderCall.created_at < end]

    scope_filter = scope_filters(budget.scope_type, budget.scope_id, budget.api_key_id)
    if scope_filter is None:
        return []
    filters += scope_filter

    if end_user_id is not None:
        filters.append(ProviderCall.end_user_id == end_user_id)

    rows_result = await db.execute(
        select(
            ProviderCall.end_user_id,
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost_usd"),
            func.count(ProviderCall.id).label("call_count"),
            func.count(func.distinct(ProviderCall.run_id)).label("run_count"),
        )
        .outerjoin(AgentRun, ProviderCall.run_id == AgentRun.id)
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

UUID_SCOPES = frozenset({"app", "access_group", "api_key", "provider_profile"})


def model_matches(pattern: str, model: str | None) -> bool:
    """Model-scope pattern: exact name, or a trailing ``*`` prefix (``gpt-4*``)."""
    if not model or not pattern:
        return False
    if pattern.endswith("*"):
        return model.startswith(pattern[:-1])
    return pattern == model


def scope_filters(
    scope_type: str, scope_id: str | None, api_key_id: uuid.UUID | str | None = None
) -> list[Any] | None:
    """SQL filters (over provider_calls outer-joined to agent_runs) for a budget scope.

    Shared by the breakdown, the nightly reconciliation and the 30-day simulation so
    every reader agrees with the live spend path. Returns None for a scope that can't
    be evaluated in SQL (malformed id, or provider_profile, handled by the caller).
    """
    from sqlalchemy import String, cast, or_  # noqa: PLC0415

    from runledger_api.models.tenant import User  # noqa: PLC0415

    if scope_type == "workspace":
        return []
    if not scope_id:
        return None
    try:
        if scope_type == "end_user":
            return [or_(ProviderCall.end_user_id == scope_id, AgentRun.end_user_id == scope_id)]
        if scope_type == "feature_tag":
            return [AgentRun.feature_tag == scope_id]
        if scope_type == "app":
            return [AgentRun.application_id == uuid.UUID(scope_id)]
        if scope_type == "api_key":
            key_id = uuid.UUID(scope_id)
            return [or_(ProviderCall.api_key_id == key_id, AgentRun.api_key_id == key_id)]
        if scope_type == "access_group":
            group_id = uuid.UUID(scope_id)
            members = select(AccessGroupMember.user_id).where(
                AccessGroupMember.group_id == group_id
            )
            return [
                or_(
                    ProviderCall.api_key_id.in_(
                        select(ApiKey.id).where(ApiKey.user_id.in_(members))
                    ),
                    ProviderCall.end_user_id.in_(
                        select(cast(AccessGroupMember.user_id, String)).where(
                            AccessGroupMember.group_id == group_id
                        )
                    ),
                    ProviderCall.end_user_id.in_(select(User.email).where(User.id.in_(members))),
                )
            ]
        if scope_type == "model":
            cond = (
                ProviderCall.model.like(
                    scope_id[:-1].replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                    + "%",
                    escape="\\",
                )
                if scope_id.endswith("*")
                else ProviderCall.model == scope_id
            )
            filters: list[Any] = [cond]
            if api_key_id:
                filters.append(ProviderCall.api_key_id == uuid.UUID(str(api_key_id)))
            return filters
    except ValueError:
        return None
    return None


@dataclass(frozen=True, slots=True)
class BudgetScope:
    """The scope dimensions of one model call, used to pick the budgets it counts against."""

    end_user_id: str | None = None
    feature_tag: str | None = None
    app_id: str | None = None
    api_key_id: str | None = None
    access_group_ids: tuple[str, ...] = ()
    provider_profile_id: str | None = None
    model: str | None = None


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
    model: str | None = None,
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
    - model scope: matches when ``model`` fits the scope_id pattern and, if the budget
      has a key filter, the call came from that key
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
            or (
                scope_type == "model"
                and model_matches(b["scope_id"] or "", model)
                and (not b.get("api_key_id") or b.get("api_key_id") == api_key_id)
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
    model: str | None = None,
    run_id: str | None = None,
    session_id: str | None = None,
) -> BudgetCheckResponse:
    """
    Budget check for SDK callers (``GET /budgets/check``): cached budget defs plus
    period spend (Redis, falling back to Postgres), and runaway holds.

    Returns BudgetCheckResponse with allowed=False when a blocking or
    downgrade budget is exceeded.  Notify-only budgets do not block.
    """
    hold = await find_runaway_hold(redis, db, workspace_id, run_id=run_id, session_id=session_id)
    if hold is not None:
        return BudgetCheckResponse(allowed=False, action="block", reason=f"runaway_hold:{hold}")
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
        model=model,
    )
    return await _evaluate_matched(redis, matched, db)


async def _evaluate_matched(
    redis: Redis, matched: list[dict[str, Any]], db: AsyncSession | None = None
) -> BudgetCheckResponse:
    throttled = False
    throttle_budget_id: str | None = None

    for b in matched:
        budget_id = uuid.UUID(b["id"])
        spend = await get_budget_spend(redis, budget_id, b["period_type"], db=db)
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
        model=model,
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
        model=scope.model,
    )


# ── Gateway enforcement ───────────────────────────────────────────────────────


_ROUTE_SCOPES = frozenset({"provider_profile", "model"})


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

    Covers workspace, end_user, feature_tag, api_key and access_group budgets, then
    the key's budget tier spend limit (review cd:B-06). Provider-profile and model
    budgets depend on the route and are checked per route with
    :func:`check_provider_profile_budgets`.
    """
    budgets = await get_workspace_budgets_cached(redis, db, workspace_id)
    request_budgets = [b for b in budgets if b.get("scope_type") not in _ROUTE_SCOPES]
    if request_budgets:
        scope = await build_budget_scope(
            db,
            request_budgets,
            workspace_id=workspace_id,
            api_key_id=api_key_id,
            end_user_id=end_user_id,
            feature_tag=feature_tag,
            principal_user_id=principal_user_id,
        )
        result = await _evaluate_matched(redis, _match_scope(request_budgets, scope), db)
        if not result.allowed:
            return result
    else:
        result = BudgetCheckResponse(allowed=True)

    if api_key_id is not None:
        from runledger_api.services.gateway_controls import key_tier_breach  # noqa: PLC0415

        breach = await key_tier_breach(db, redis, workspace_id, api_key_id)
        if breach is not None:
            return BudgetCheckResponse(allowed=False, action="block", reason=breach)
    return result


async def check_provider_profile_budgets(
    redis: Redis,
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    provider: str | None,
    model: str | None,
    api_key_id: uuid.UUID | str | None = None,
) -> BudgetCheckResponse:
    """Check the route-dependent budgets for one candidate route.

    Provider-profile budgets (the pricing row the route bills under) and model
    budgets (``scope_type=model``, review G-01). A route over such a budget is
    skipped, so traffic falls back to the next route; with none left the gateway
    returns 429.
    """
    budgets = await get_workspace_budgets_cached(redis, db, workspace_id)
    route_budgets = [b for b in budgets if b.get("scope_type") in _ROUTE_SCOPES]
    if not route_budgets:
        return BudgetCheckResponse(allowed=True)
    key = str(api_key_id) if api_key_id else None
    matched = _matching_budgets(
        [b for b in route_budgets if b["scope_type"] == "model"], api_key_id=key, model=model
    )
    if any(b["scope_type"] == "provider_profile" for b in route_budgets):
        profile_id = await resolve_provider_profile_id(db, workspace_id, provider, model)
        if profile_id is not None:
            matched += [
                b
                for b in route_budgets
                if b["scope_type"] == "provider_profile" and b.get("scope_id") == profile_id
            ]
    return await _evaluate_matched(redis, matched, db)


# ── Runaway holds (review cd:B-09) ────────────────────────────────────────────

_HOLDS_CACHE_TTL = 30  # seconds


def _holds_cache_key(workspace_id: uuid.UUID) -> str:
    return f"rl:workspace:{workspace_id}:runaway_holds"


async def invalidate_runaway_holds_cache(redis: Redis, workspace_id: uuid.UUID) -> None:
    try:
        await redis.delete(_holds_cache_key(workspace_id))
    except Exception:
        log.warning("runaway_holds_cache_invalidate_failed", workspace_id=str(workspace_id))


async def _active_holds(redis: Redis, db: AsyncSession, workspace_id: uuid.UUID) -> set[str]:
    """``{"run:<id>", "session:<id>"}`` currently held in the workspace (cached 30 s)."""
    key = _holds_cache_key(workspace_id)
    try:
        cached = await redis.get(key)
    except Exception:
        cached = None
    if cached is not None:
        return set(json.loads(cached))
    from runledger_api.models.budgets import RunawayHold  # noqa: PLC0415

    rows = await db.execute(
        select(RunawayHold.subject_type, RunawayHold.subject_id).where(
            RunawayHold.workspace_id == workspace_id,
            RunawayHold.released_at.is_(None),
            RunawayHold.expires_at > datetime.now(UTC),
        )
    )
    held = {f"{t}:{i}" for t, i in rows.all()}
    try:
        await redis.set(key, json.dumps(sorted(held)), ex=_HOLDS_CACHE_TTL)
    except Exception:
        log.warning("runaway_holds_cache_write_failed", workspace_id=str(workspace_id))
    return held


async def find_runaway_hold(
    redis: Redis,
    db: AsyncSession,
    workspace_id: uuid.UUID,
    *,
    run_id: str | None = None,
    session_id: str | None = None,
) -> str | None:
    """The held subject (``run:<id>`` / ``session:<id>``) a request belongs to, if any."""
    if not run_id and not session_id:
        return None
    held = await _active_holds(redis, db, workspace_id)
    for subject in (
        f"run:{run_id}" if run_id else None,
        f"session:{session_id}" if session_id else None,
    ):
        if subject and subject in held:
            return subject
    return None


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

    This is the single write path for budget spend. It is called wherever a provider
    call gets its cost: gateway finalize, ingest (SDK/OTLP calls that carry a cost)
    and the metering worker (calls priced after the fact).

    - Durable: spend is added to ``budget_spend`` in the caller's transaction and
      written through to the Redis cache (review cd:B-05).
    - Spend lands in the period of ``occurred_at`` (the call's own time), so a call
      priced late by enrichment is not counted in a later period.
    - Idempotent per provider call (``budget_spend_calls``), so ingest retries,
      re-enrichment and ``replay_backfill`` cannot double count.
    - Emits ``budget.threshold_crossed`` at 80% and records a breach (with queued
      notifications) when the limit is reached, each once per budget period.
    - Does not commit; the caller owns the transaction.

    Returns the number of budgets the call was counted against.
    """
    if cost_usd is None or cost_usd <= 0:
        return 0
    budgets = await get_workspace_budgets_cached(redis, db, workspace_id)
    if not budgets:
        return 0
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
    if not matched or not await _db_claim_call(db, workspace_id, provider_call_id):
        return 0
    at = occurred_at or datetime.now(UTC)
    for b in matched:
        budget_id = uuid.UUID(b["id"])
        period_type = b["period_type"]
        pk = _period_key(period_type, at)
        spend = await _db_add_spend(db, budget_id, pk, cost_usd)
        await _cache_spend(redis, budget_id, pk, spend)
        limit = Decimal(b["limit_usd"])
        if limit <= 0:
            continue
        if limit * Decimal("0.80") <= spend < limit and await _db_mark_once(
            db, budget_id, pk, "threshold_notified_at"
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
        if spend >= limit and await _db_mark_once(db, budget_id, pk, "breached_at"):
            await fire_breach(db, redis, b, spend, b["action"], commit=False)
    return len(matched)


# ── Breach recording + queued notification delivery (review F-22) ─────────────

DELIVERY_MAX_ATTEMPTS = 5


def delivery_backoff(attempt: int) -> timedelta:
    """Delay before retry ``attempt + 1``: 1, 2, 4, 8 … minutes."""
    return timedelta(minutes=2 ** max(0, attempt - 1))


async def queue_notifications(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    event: str,
    payload: dict[str, Any],
    *,
    breach_id: uuid.UUID | None = None,
) -> int:
    """Queue one delivery per active destination subscribed to ``event``.

    Nothing is sent inline: ``budgets.deliver_notifications`` sends due deliveries
    with retry and backoff, so a slow webhook can't stall metering or the gateway.
    Returns the number of deliveries queued.
    """
    result = await db.execute(
        select(BudgetNotification).where(
            BudgetNotification.workspace_id == workspace_id,
            BudgetNotification.is_active.is_(True),
            BudgetNotification.events.contains([event]),
        )
    )
    now = datetime.now(UTC)
    queued = 0
    for notification in result.scalars():
        delivery = build_delivery_record(notification, event_type=event, status="pending")
        delivery.payload = payload
        delivery.next_attempt_at = now
        delivery.breach_id = breach_id
        db.add(delivery)
        queued += 1
    return queued


def kick_delivery_worker() -> None:
    """Ask the worker to deliver soon; the 60 s sweep covers it if this fails."""
    try:
        from runledger_api.core.celery_app import celery_app  # noqa: PLC0415

        celery_app.send_task("budgets.deliver_notifications", countdown=2)
    except Exception:
        log.debug("budget_delivery_kick_failed")


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
    Record a breach in Postgres and queue its notifications.

    budget_dict is the serialised dict from the budgets cache (not the ORM obj).
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

    workspace_id_str = budget_dict.get("workspace_id")
    queued = 0
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
        queued = await queue_notifications(
            db,
            workspace_id,
            "budget.breach",
            {
                "event": "budget.breach",
                "budget_id": str(budget_id),
                "breach_id": str(breach.id),
                "scope_type": budget_dict.get("scope_type"),
                "scope_id": budget_dict.get("scope_id"),
                "period_type": budget_dict.get("period_type"),
                "limit_usd": budget_dict.get("limit_usd"),
                "spend_usd": str(spend),
                "action_taken": action_taken,
                "occurred_at": datetime.now(UTC).isoformat(),
            },
            breach_id=breach.id,
        )

    if commit:
        await db.commit()
    else:
        await db.flush()
    if queued:
        kick_delivery_worker()
    log.info(
        "budget_breach_recorded",
        budget_id=str(budget_id),
        spend=str(spend),
        action_taken=action_taken,
        notifications_queued=queued,
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


# ── Burn-down, forecast and simulation (ENH) ──────────────────────────────────


async def resolve_scope_filters(
    db: AsyncSession,
    scope_type: str,
    scope_id: str | None,
    api_key_id: uuid.UUID | str | None = None,
) -> list[Any] | None:
    """:func:`scope_filters`, plus provider profiles resolved through their priced model."""
    if scope_type == "provider_profile":
        from runledger_api.models.metering import ProviderPricing  # noqa: PLC0415

        try:
            pricing = await db.get(ProviderPricing, uuid.UUID(scope_id or ""))
        except ValueError:
            return None
        if pricing is None:
            return None
        return [ProviderCall.model == pricing.model, ProviderCall.provider == pricing.provider]
    return scope_filters(scope_type, scope_id, api_key_id)


def _scoped_calls(workspace_id: uuid.UUID, filters: list[Any]) -> Any:
    from runledger_api.services.billable import billable_filters  # noqa: PLC0415

    return (
        select(ProviderCall.id, ProviderCall.created_at, ProviderCall.cost_usd)
        .select_from(ProviderCall)
        .outerjoin(AgentRun, AgentRun.id == ProviderCall.run_id)
        .where(ProviderCall.workspace_id == workspace_id, *filters, *billable_filters())
    )


async def budget_burndown(
    db: AsyncSession, redis: Redis, budget: Budget, *, now: datetime | None = None
) -> dict[str, Any]:
    """Cumulative spend through the current period and a forecast-to-breach date.

    Buckets are hours for daily budgets and days otherwise. The run rate is the
    average spend per bucket over the elapsed part of the period (at most the last 7
    days, so an early spike doesn't dominate); the forecast extends it to the end of
    the period (90 days for ``total`` budgets) and reports the first bucket where the
    projected total reaches the limit.
    """
    now = now or datetime.now(UTC)
    start, end = period_window(budget.period_type, now)
    hourly = budget.period_type == "daily"
    step = timedelta(hours=1) if hourly else timedelta(days=1)
    unit = "hour" if hourly else "day"
    series_start = start or (now - timedelta(days=30)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    series_end = end or now + timedelta(days=90)
    limit = Decimal(budget.limit_usd)
    current = await get_budget_spend(redis, budget.id, budget.period_type, now, db=db)

    filters = await resolve_scope_filters(db, budget.scope_type, budget.scope_id, budget.api_key_id)
    by_bucket: dict[datetime, Decimal] = {}
    if filters is not None:
        calls = (
            _scoped_calls(budget.workspace_id, filters)
            .where(ProviderCall.created_at >= series_start, ProviderCall.created_at <= now)
            .subquery()
        )
        bucket = func.date_trunc(unit, calls.c.created_at)
        rows = await db.execute(
            select(bucket.label("b"), func.coalesce(func.sum(calls.c.cost_usd), 0)).group_by(bucket)
        )
        for b, cost in rows.all():
            by_bucket[b.astimezone(UTC) if b.tzinfo else b.replace(tzinfo=UTC)] = Decimal(cost)

    points: list[dict[str, Any]] = []
    cursor = series_start
    cumulative = Decimal(0)
    elapsed: list[Decimal] = []
    while cursor <= now:
        spend = by_bucket.get(cursor, Decimal(0))
        cumulative += spend
        elapsed.append(spend)
        points.append(
            {"date": cursor.isoformat(), "spend_usd": spend, "cumulative_usd": cumulative}
        )
        cursor += step
    # The live counter is authoritative for "now" (it includes calls priced after the
    # chart's rows were read); rescale the last point if they differ.
    if start is not None and points and current > cumulative:
        points[-1]["cumulative_usd"] = current
        cumulative = current
    window = elapsed[-(168 if hourly else 7) :] if elapsed else []
    rate = (sum(window, Decimal(0)) / len(window)) if window else Decimal(0)
    forecast_breach: str | None = None
    already = cumulative >= limit
    projected = cumulative
    while cursor < series_end:
        projected += rate
        points.append(
            {
                "date": cursor.isoformat(),
                "spend_usd": rate,
                "cumulative_usd": projected,
                "forecast": True,
            }
        )
        if forecast_breach is None and not already and rate > 0 and projected >= limit:
            forecast_breach = cursor.isoformat()
        cursor += step
    daily_rate = rate * 24 if hourly else rate
    return {
        "budget_id": str(budget.id),
        "period_type": budget.period_type,
        "period_start": start,
        "period_end": end,
        "limit_usd": limit,
        "current_spend_usd": cumulative,
        "daily_run_rate_usd": daily_rate.quantize(Decimal("0.000001")),
        "projected_period_spend_usd": projected if end is not None else None,
        "forecast_breach_date": forecast_breach,
        "already_breached": already,
        "points": points,
    }


_TRUNC_UNIT = {"daily": "day", "weekly": "week", "monthly": "month"}


async def simulate_budget(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    *,
    scope_type: str,
    scope_id: str | None,
    api_key_id: str | None,
    period_type: str,
    limit_usd: Decimal,
    action: str,
    days: int = 30,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Replay the last ``days`` of real spend against a candidate budget.

    The same scope filters as live enforcement select the calls; within each budget
    period a running total (SQL window function) finds when the limit would have been
    reached. Calls made after that point, when spend was already at or above the
    limit, are the ones the action would have affected (blocked, downgraded, throttled
    or merely notified on), mirroring the gateway's pre-call check.
    """
    now = now or datetime.now(UTC)
    window_start = now - timedelta(days=days)
    filters = await resolve_scope_filters(db, scope_type, scope_id, api_key_id)
    if filters is None:
        raise ValueError("This scope can't be simulated (unknown or malformed scope id)")
    calls = (
        _scoped_calls(workspace_id, filters)
        .where(ProviderCall.created_at >= window_start, ProviderCall.created_at <= now)
        .subquery()
    )
    unit = _TRUNC_UNIT.get(period_type)
    period = func.date_trunc(unit, calls.c.created_at) if unit else sa_literal("total", sa_Text)
    cost = func.coalesce(calls.c.cost_usd, 0)
    running = (
        select(
            period.label("p"),
            calls.c.created_at,
            cost.label("cost"),
            func.sum(cost)
            .over(partition_by=period, order_by=(calls.c.created_at, calls.c.id))
            .label("cum"),
        )
    ).subquery()
    before = running.c.cum - running.c.cost
    rows = await db.execute(
        select(
            running.c.p,
            func.sum(running.c.cost),
            func.count(),
            func.min(running.c.created_at).filter(running.c.cum >= limit_usd),
            func.count().filter(before >= limit_usd),
            func.coalesce(func.sum(running.c.cost).filter(before >= limit_usd), 0),
        )
        .group_by(running.c.p)
        .order_by(running.c.p)
    )
    periods: list[dict[str, Any]] = []
    for p, spend, n, breached_at, affected, affected_cost in rows.all():
        label = _period_key(period_type, p) if isinstance(p, datetime) else "total"
        periods.append(
            {
                "period_key": label,
                "spend_usd": Decimal(spend or 0),
                "call_count": int(n or 0),
                "breached_at": breached_at,
                "affected_calls": int(affected or 0),
                "affected_cost_usd": Decimal(affected_cost or 0),
            }
        )
    breaches = [p for p in periods if p["breached_at"] is not None]
    affected_calls = sum(p["affected_calls"] for p in periods)
    affected_cost = sum((p["affected_cost_usd"] for p in periods), Decimal(0))
    verb = {
        "block": "blocked",
        "downgrade": "downgraded",
        "fallback": "sent to the fallback model",
        "throttle": "throttled",
        "notify": "flagged (notify only)",
    }.get(action, "affected")
    if not periods:
        summary = f"No matching spend in the last {days} days."
    elif not breaches:
        summary = f"Never breached in the last {days} days ({len(periods)} period(s))."
    else:
        summary = (
            f"Breached in {len(breaches)} of {len(periods)} period(s); "
            f"{affected_calls} call(s) (${affected_cost:.4f}) would have been {verb}."
        )
    return {
        "days": days,
        "window_start": window_start,
        "window_end": now,
        "total_spend_usd": sum((p["spend_usd"] for p in periods), Decimal(0)),
        "total_calls": sum(p["call_count"] for p in periods),
        "periods": periods,
        "breach_count": len(breaches),
        "affected_calls": affected_calls,
        "affected_cost_usd": affected_cost,
        "first_breach_at": breaches[0]["breached_at"] if breaches else None,
        "summary": summary,
    }


# ── Alert metrics (review S-18) ───────────────────────────────────────────────


async def compute_budget_metric(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    metric: str,
    window_start: datetime,
    window_end: datetime,
) -> Decimal | None:
    """Values for the ``budget_*`` alert metrics.

    - ``budget_utilization``: the highest percent used (0-100+) of any active budget
      in its current period, read from budget_spend; None without active budgets.
    - ``budget_breach_count``: breaches recorded in the alert window.
    """
    if metric == "budget_breach_count":
        count = (
            await db.execute(
                select(func.count(BudgetBreach.id))
                .join(Budget, Budget.id == BudgetBreach.budget_id)
                .where(
                    Budget.workspace_id == workspace_id,
                    BudgetBreach.occurred_at >= window_start,
                    BudgetBreach.occurred_at < window_end,
                )
            )
        ).scalar_one()
        return Decimal(int(count or 0))
    if metric == "budget_utilization":
        budgets = list(
            (
                await db.execute(
                    select(Budget).where(
                        Budget.workspace_id == workspace_id, Budget.is_active.is_(True)
                    )
                )
            ).scalars()
        )
        if not budgets:
            return None
        best = Decimal(0)
        for budget in budgets:
            if budget.limit_usd <= 0:
                continue
            spend = await _db_load_spend(db, budget.id, _period_key(budget.period_type, window_end))
            best = max(best, spend / Decimal(budget.limit_usd) * 100)
        return best.quantize(Decimal("0.01"))
    return None
