"""Shared building blocks for the Observe surfaces (runs, sessions, explorer, analytics).

One place for the rules every Observe endpoint must agree on (review O-06, O-14, O-23):

* **Scope** — which workspaces a request may read (workspace, org, platform).
* **Access groups** — the dashboard filters an access group imposes, applied the same way
  to ``agent_runs`` and ``provider_calls``.
* **Status vocabulary** — runs use ``succeeded``/``failed``; provider calls use
  ``success``/``error``. Filters accept either word and are mapped to the right column.
* **Cursor** — a composite ``(started_at, id)`` keyset cursor, so ties are never skipped.
* **Payload access** — who may read captured prompts and responses (O-05).
* **Summary** — the single KPI computation behind ``/analytics/summary`` and
  ``/analytics/scoped-summary``, including the run success rate (O-22).
* **Series** — spend charts served from the ``usage_hourly`` rollup, with raw provider
  calls only for the hours the rollup has not covered yet (O-16).
"""

from __future__ import annotations

import base64
import binascii
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from fastapi import HTTPException, Request, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.scopes import effective_scopes
from runledger_api.models.access_groups import AccessGroup, AccessGroupMember
from runledger_api.models.events import AgentRun, ProviderCall, RunStatusEnum
from runledger_api.models.metering import UsageHourly
from runledger_api.models.tenant import (
    MemberStatusEnum,
    TenantRoleEnum,
    TenantUser,
    Workspace,
)
from runledger_api.services.billable import billable_cost_sum

# ── Status vocabulary ─────────────────────────────────────────────────────────

RUN_STATUSES: tuple[str, ...] = tuple(s.value for s in RunStatusEnum)
# Words accepted for a run status filter, mapped to the run enum.
_RUN_STATUS_ALIASES: dict[str, str] = {
    "succeeded": "succeeded",
    "success": "succeeded",
    "ok": "succeeded",
    "failed": "failed",
    "error": "failed",
    "running": "running",
    "cancelled": "cancelled",
    "canceled": "cancelled",
}
# Run status → provider-call statuses with the same meaning.
_RUN_TO_CALL_STATUS: dict[str, tuple[str, ...]] = {
    "succeeded": ("success",),
    "failed": ("error", "timeout", "blocked", "failed"),
    "running": (),
    "cancelled": ("cancelled",),
}
CALL_STATUSES: tuple[str, ...] = ("success", "error", "timeout", "blocked")


def normalize_run_status(value: str | None) -> str | None:
    """Map a run status filter to the run enum, or raise 422 for an unknown value."""
    if value is None or not value.strip():
        return None
    key = value.strip().lower()
    if key not in _RUN_STATUS_ALIASES:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Unknown status '{value}'. Allowed: {', '.join(RUN_STATUSES)}",
        )
    return _RUN_STATUS_ALIASES[key]


def call_statuses_for(value: str | None) -> list[str] | None:
    """Provider-call statuses matching a filter given in either vocabulary (O-01)."""
    if value is None or not value.strip():
        return None
    key = value.strip().lower()
    if key in CALL_STATUSES:
        return [key]
    if key in _RUN_STATUS_ALIASES:
        return list(_RUN_TO_CALL_STATUS[_RUN_STATUS_ALIASES[key]])
    raise HTTPException(
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        f"Unknown status '{value}'. Allowed: {', '.join(CALL_STATUSES + RUN_STATUSES)}",
    )


# ── Access groups ─────────────────────────────────────────────────────────────


@dataclass
class AccessGroupFilters:
    end_user_ids: list[str] = field(default_factory=list)
    feature_tags: list[str] = field(default_factory=list)
    models: list[str] = field(default_factory=list)
    providers: list[str] = field(default_factory=list)
    statuses: list[str] = field(default_factory=list)

    def __getitem__(self, key: str) -> list[str]:  # legacy dict-style access
        return list(getattr(self, key))

    def __bool__(self) -> bool:
        return True


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


async def resolve_access_group(
    db: AsyncSession, workspace_id: uuid.UUID, access_group_id: uuid.UUID | None
) -> AccessGroupFilters | None:
    """Load an active access group's dashboard filters (404 when not in this workspace)."""
    if access_group_id is None:
        return None
    group = (
        await db.execute(
            select(AccessGroup).where(
                AccessGroup.id == access_group_id,
                AccessGroup.workspace_id == workspace_id,
                AccessGroup.is_active.is_(True),
            )
        )
    ).scalar_one_or_none()
    if group is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Access group not found")

    raw_filters = (group.permissions or {}).get("dashboard_filters", {})
    dashboard_filters = raw_filters if isinstance(raw_filters, dict) else {}

    def _values(keys: list[str]) -> list[str]:
        collected: list[str] = []
        for key in keys:
            raw = dashboard_filters.get(key)
            if isinstance(raw, str) and raw.strip():
                collected.append(raw.strip())
            elif isinstance(raw, list):
                collected.extend(i.strip() for i in raw if isinstance(i, str) and i.strip())
        return collected

    members = (
        await db.execute(
            select(AccessGroupMember.user_id).where(AccessGroupMember.group_id == access_group_id)
        )
    ).scalars()
    end_users = [str(m) for m in members] + _values(
        ["end_user_id", "end_user_ids", "user_id", "user_ids"]
    )
    return AccessGroupFilters(
        end_user_ids=_unique(end_users),
        feature_tags=_unique(_values(["feature_tag", "feature_tags", "intent", "intents"])),
        models=_unique(_values(["model", "models"])),
        providers=_unique(_values(["provider", "providers"])),
        statuses=_unique(_values(["status", "statuses"])),
    )


def run_access_clauses(
    filters: AccessGroupFilters | None, workspace_ids: list[uuid.UUID]
) -> list[Any]:
    """WHERE clauses on ``agent_runs`` for an access group."""
    if filters is None:
        return []
    clauses: list[Any] = []
    if filters.end_user_ids:
        clauses.append(AgentRun.end_user_id.in_(filters.end_user_ids))
    if filters.feature_tags:
        clauses.append(AgentRun.feature_tag.in_(filters.feature_tags))
    if filters.statuses:
        run_statuses = {
            _RUN_STATUS_ALIASES[s.lower()]
            for s in filters.statuses
            if s.lower() in _RUN_STATUS_ALIASES
        }
        clauses.append(AgentRun.status.in_(sorted(run_statuses) or ["__none__"]))
    for column, values in (
        (ProviderCall.model, filters.models),
        (ProviderCall.provider, filters.providers),
    ):
        if values:
            clauses.append(
                AgentRun.id.in_(
                    select(ProviderCall.run_id)
                    .where(ProviderCall.workspace_id.in_(workspace_ids), column.in_(values))
                    .distinct()
                )
            )
    return clauses


def call_access_clauses(filters: AccessGroupFilters | None) -> list[Any]:
    """WHERE clauses on ``provider_calls`` for an access group (needs no join)."""
    if filters is None:
        return []
    clauses: list[Any] = []
    if filters.end_user_ids:
        clauses.append(ProviderCall.end_user_id.in_(filters.end_user_ids))
    if filters.models:
        clauses.append(ProviderCall.model.in_(filters.models))
    if filters.providers:
        clauses.append(ProviderCall.provider.in_(filters.providers))
    if filters.statuses:
        call_statuses: set[str] = set()
        for s in filters.statuses:
            call_statuses.update(call_statuses_for(s) or [])
        clauses.append(ProviderCall.status.in_(sorted(call_statuses) or ["__none__"]))
    if filters.feature_tags:
        clauses.append(
            ProviderCall.run_id.in_(
                select(AgentRun.id).where(AgentRun.feature_tag.in_(filters.feature_tags))
            )
        )
    return clauses


def rollup_access_clauses(filters: AccessGroupFilters | None) -> list[Any] | None:
    """Clauses on ``usage_hourly``, or None when the group can't be expressed there."""
    if filters is None:
        return []
    if filters.statuses:
        return None
    clauses: list[Any] = []
    if filters.end_user_ids:
        clauses.append(UsageHourly.end_user_id.in_(filters.end_user_ids))
    if filters.models:
        clauses.append(UsageHourly.model.in_(filters.models))
    if filters.providers:
        clauses.append(UsageHourly.provider.in_(filters.providers))
    if filters.feature_tags:
        clauses.append(UsageHourly.feature_tag.in_(filters.feature_tags))
    return clauses


# ── Scope ─────────────────────────────────────────────────────────────────────

ORG_SCOPE_ROLES = frozenset({TenantRoleEnum.org_admin, TenantRoleEnum.org_manager})


async def resolve_scope_workspace_ids(
    scope: str, workspace: Workspace, user: Any, db: AsyncSession
) -> list[uuid.UUID]:
    """Workspaces a request may read for ``scope`` (403 when the role does not allow it)."""
    if scope == "workspace":
        return [workspace.id]
    if user is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "A dashboard user session is required for org or platform scope",
        )
    if scope == "org":
        if not user.is_platform_admin:
            tu = (
                await db.execute(
                    select(TenantUser).where(
                        TenantUser.user_id == user.id,
                        TenantUser.tenant_id == workspace.tenant_id,
                        TenantUser.status == MemberStatusEnum.active,
                    )
                )
            ).scalar_one_or_none()
            if tu is None or tu.role not in ORG_SCOPE_ROLES:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN, "Organization admin access required for org scope"
                )
        rows = await db.execute(
            select(Workspace.id).where(Workspace.tenant_id == workspace.tenant_id)
        )
        return list(rows.scalars().all())
    if scope == "platform":
        if not user.is_platform_admin:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "Platform admin access required for platform scope"
            )
        return list((await db.execute(select(Workspace.id))).scalars().all())
    raise HTTPException(
        status.HTTP_422_UNPROCESSABLE_ENTITY, "scope must be workspace, org, or platform"
    )


async def allowed_scopes(workspace: Workspace, user: Any, db: AsyncSession) -> list[str]:
    """Scopes the caller may use, so the UI hides the ones that would 403."""
    scopes = ["workspace"]
    if user is None:
        return scopes
    if user.is_platform_admin:
        return ["workspace", "org", "platform"]
    tu = (
        await db.execute(
            select(TenantUser).where(
                TenantUser.user_id == user.id,
                TenantUser.tenant_id == workspace.tenant_id,
                TenantUser.status == MemberStatusEnum.active,
            )
        )
    ).scalar_one_or_none()
    if tu is not None and tu.role in ORG_SCOPE_ROLES:
        scopes.append("org")
    return scopes


async def request_user(request: Request, db: AsyncSession) -> Any:
    """The dashboard user behind this request, resolved only when a scope needs it."""
    api_key = getattr(request.state, "api_key", None)
    if api_key is None or not getattr(api_key, "is_session", False):
        return None
    cached = getattr(request.state, "session_user", None)
    if cached is not None:
        return cached
    from runledger_api.core.deps import _session_owner  # noqa: PLC0415

    return await _session_owner(api_key, db)


# ── Composite cursor ──────────────────────────────────────────────────────────


def encode_cursor(started_at: datetime, run_id: uuid.UUID) -> str:
    raw = f"{started_at.isoformat()}|{run_id}".encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID | None]:
    """Decode a ``(started_at, id)`` cursor. Bare ISO timestamps are still accepted."""
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        text = base64.urlsafe_b64decode(padded.encode()).decode()
        ts, _, rid = text.partition("|")
        if rid:
            return datetime.fromisoformat(ts), uuid.UUID(rid)
    except (binascii.Error, UnicodeDecodeError, ValueError):
        pass
    try:
        return datetime.fromisoformat(cursor), None
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid cursor") from exc


def cursor_clause(cursor: str) -> Any:
    started_at, run_id = decode_cursor(cursor)
    if run_id is None:
        return AgentRun.started_at < started_at
    return sa.or_(
        AgentRun.started_at < started_at,
        sa.and_(AgentRun.started_at == started_at, AgentRun.id < run_id),
    )


# ── Payload access (O-05) ─────────────────────────────────────────────────────

_PAYLOAD_ORG_ROLES = frozenset(
    {TenantRoleEnum.org_admin, TenantRoleEnum.org_manager, TenantRoleEnum.org_auditor}
)


async def can_view_payloads(request: Request, workspace: Workspace, db: AsyncSession) -> bool:
    """Whether the caller may read captured prompts and responses.

    * Workload keys: unrestricted keys and keys with the ``write`` scope. Read-only
      keys (dashboards, BI exports) get metadata only.
    * Dashboard users: platform admins, org admins/managers/auditors, and workspace
      members with a writable role. Viewers and org billing admins get metadata only.
    """
    api_key = getattr(request.state, "api_key", None)
    if api_key is None:
        return True  # OIDC workload token: workspace credential
    if not api_key.is_session:
        granted = effective_scopes(api_key.scopes)
        return granted is None or "write" in granted
    from runledger_api.core.deps import (  # noqa: PLC0415
        _get_tenant_user,
        _session_owner,
        can_write_workspace,
    )

    user = getattr(request.state, "session_user", None) or await _session_owner(api_key, db)
    if user is None:
        return False
    if user.is_platform_admin:
        return True
    tu = await _get_tenant_user(user.id, workspace.tenant_id, db)
    if tu is not None and tu.role in _PAYLOAD_ORG_ROLES:
        return True
    return await can_write_workspace(db, user, workspace)


# ── Summary service (O-06, O-14, O-22) ────────────────────────────────────────


@dataclass
class SummaryResult:
    total_cost_usd: Decimal
    total_savings_usd: Decimal
    total_input_tokens: int
    total_output_tokens: int
    run_count: int
    call_count: int
    active_users: int
    prev_cost_usd: Decimal
    cost_delta_pct: Decimal | None
    succeeded_runs: int
    finished_runs: int
    success_rate: Decimal | None


def _call_filters(
    workspace_ids: list[uuid.UUID],
    t_from: datetime,
    t_to: datetime,
    access: AccessGroupFilters | None,
    api_key_id: uuid.UUID | None,
) -> list[Any]:
    clauses: list[Any] = [
        ProviderCall.workspace_id.in_(workspace_ids),
        ProviderCall.created_at >= t_from,
        ProviderCall.created_at < t_to,
        *call_access_clauses(access),
    ]
    if api_key_id is not None:
        clauses.append(ProviderCall.api_key_id == api_key_id)
    return clauses


def run_filters(
    workspace_ids: list[uuid.UUID],
    t_from: datetime,
    t_to: datetime,
    access: AccessGroupFilters | None,
    api_key_id: uuid.UUID | None,
) -> list[Any]:
    clauses: list[Any] = [
        AgentRun.workspace_id.in_(workspace_ids),
        AgentRun.started_at >= t_from,
        AgentRun.started_at < t_to,
        *run_access_clauses(access, workspace_ids),
    ]
    if api_key_id is not None:
        clauses.append(AgentRun.api_key_id == api_key_id)
    return clauses


async def compute_summary(
    db: AsyncSession,
    *,
    workspace_ids: list[uuid.UUID],
    t_from: datetime,
    t_to: datetime,
    access: AccessGroupFilters | None = None,
    api_key_id: uuid.UUID | None = None,
) -> SummaryResult:
    """The one KPI computation. Spend is billable cost; usage counts successful calls.

    When a window has no provider calls (runs ingested with totals only) the run
    table supplies cost and tokens instead, so the KPIs are never blank for SDK-only
    workspaces. The previous period uses the same filters (O-14).
    """
    ok = ProviderCall.status == "success"

    async def _calls(period_from: datetime, period_to: datetime) -> Any:
        return (
            await db.execute(
                select(
                    billable_cost_sum().label("cost"),
                    func.coalesce(func.sum(ProviderCall.savings_usd), Decimal(0)).label("savings"),
                    func.coalesce(func.sum(case((ok, ProviderCall.input_tokens))), 0).label("inp"),
                    func.coalesce(func.sum(case((ok, ProviderCall.output_tokens))), 0).label("out"),
                    func.count(case((ok, ProviderCall.run_id)).distinct()).label("runs"),
                    func.count(case((ok, ProviderCall.id))).label("calls"),
                    func.count(ProviderCall.end_user_id.distinct()).label("users"),
                ).where(*_call_filters(workspace_ids, period_from, period_to, access, api_key_id))
            )
        ).one()

    async def _runs(period_from: datetime, period_to: datetime) -> Any:
        filters = run_filters(workspace_ids, period_from, period_to, access, api_key_id)
        succeeded = AgentRun.status == RunStatusEnum.succeeded
        finished = AgentRun.status.in_([RunStatusEnum.succeeded, RunStatusEnum.failed])
        return (
            await db.execute(
                select(
                    func.coalesce(
                        func.sum(case((succeeded, AgentRun.total_cost_usd))), Decimal(0)
                    ).label("cost"),
                    func.coalesce(
                        func.sum(case((succeeded, AgentRun.total_input_tokens))), 0
                    ).label("inp"),
                    func.coalesce(
                        func.sum(case((succeeded, AgentRun.total_output_tokens))), 0
                    ).label("out"),
                    func.count(case((succeeded, AgentRun.id))).label("succeeded"),
                    func.count(case((finished, AgentRun.id))).label("finished"),
                    func.count(AgentRun.end_user_id.distinct()).label("users"),
                ).where(*filters)
            )
        ).one()

    cur = await _calls(t_from, t_to)
    prev = await _calls(t_from - (t_to - t_from), t_from)
    runs = await _runs(t_from, t_to)

    cost = Decimal(cur.cost or 0)
    prev_cost = Decimal(prev.cost or 0)
    inp, out, run_count, calls, users = (
        int(cur.inp),
        int(cur.out),
        int(cur.runs),
        int(cur.calls),
        int(cur.users),
    )
    if int(cur.calls or 0) == 0 and runs.succeeded:
        cost, inp, out = Decimal(runs.cost or 0), int(runs.inp), int(runs.out)
        run_count = calls = int(runs.succeeded)
        users = int(runs.users)
    if int(prev.calls or 0) == 0:
        prev_runs = await _runs(t_from - (t_to - t_from), t_from)
        if prev_runs.succeeded:
            prev_cost = Decimal(prev_runs.cost or 0)

    delta = (cost - prev_cost) / prev_cost * Decimal(100) if prev_cost > 0 else None
    finished = int(runs.finished)
    rate = (
        (Decimal(int(runs.succeeded)) / Decimal(finished)).quantize(Decimal("0.0001"))
        if finished
        else None
    )
    return SummaryResult(
        total_cost_usd=cost,
        total_savings_usd=Decimal(cur.savings or 0),
        total_input_tokens=inp,
        total_output_tokens=out,
        run_count=run_count,
        call_count=calls,
        active_users=users,
        prev_cost_usd=prev_cost,
        cost_delta_pct=delta,
        succeeded_runs=int(runs.succeeded),
        finished_runs=finished,
        success_rate=rate,
    )


# ── Rollup-backed series (O-16) ───────────────────────────────────────────────


async def rollup_watermark(db: AsyncSession, workspace_ids: list[uuid.UUID]) -> datetime | None:
    """End of the last hour the hourly rollup has covered for these workspaces.

    Hours before the watermark come from ``usage_hourly``; later ones from raw provider
    calls. None means the rollup has never run (dev without Celery beat): all raw.
    """
    latest = (
        await db.execute(
            select(func.max(UsageHourly.hour)).where(UsageHourly.workspace_id.in_(workspace_ids))
        )
    ).scalar_one_or_none()
    if latest is None:
        return None
    if latest.tzinfo is None:
        latest = latest.replace(tzinfo=UTC)
    return latest + timedelta(hours=1)


@dataclass
class SeriesPoint:
    period: datetime
    cost_usd: Decimal
    input_tokens: int
    output_tokens: int
    call_count: int


@dataclass
class ModelRow:
    provider: str
    model: str
    cost_usd: Decimal
    input_tokens: int
    output_tokens: int
    call_count: int


def _bucket(dt: datetime, unit: str) -> datetime:
    dt = dt.astimezone(UTC) if dt.tzinfo else dt.replace(tzinfo=UTC)
    if unit == "day":
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)
    return dt.replace(minute=0, second=0, microsecond=0)


async def spend_series(
    db: AsyncSession,
    *,
    workspace_ids: list[uuid.UUID],
    t_from: datetime,
    t_to: datetime,
    granularity: str,
    access: AccessGroupFilters | None = None,
    api_key_id: uuid.UUID | None = None,
) -> tuple[list[SeriesPoint], str]:
    """Spend over time. Returns points and the source used (``rollup+raw`` or ``raw``)."""
    unit = {"hourly": "hour", "daily": "day"}.get(granularity)
    rollup_clauses = rollup_access_clauses(access)
    watermark = (
        await rollup_watermark(db, workspace_ids)
        if unit and api_key_id is None and rollup_clauses is not None
        else None
    )
    split = min(max(watermark, t_from), t_to) if watermark else t_from
    buckets: dict[datetime, SeriesPoint] = {}

    def _add(period: datetime, cost: Any, inp: Any, out: Any, calls: Any) -> None:
        key = _bucket(period, unit) if unit else period
        point = buckets.setdefault(key, SeriesPoint(key, Decimal(0), 0, 0, 0))
        point.cost_usd += Decimal(cost or 0)
        point.input_tokens += int(inp or 0)
        point.output_tokens += int(out or 0)
        point.call_count += int(calls or 0)

    if unit and split > t_from:
        rows = await db.execute(
            select(
                UsageHourly.hour.label("period"),
                func.sum(UsageHourly.cost_usd).label("cost_usd"),
                func.sum(UsageHourly.input_tokens).label("input_tokens"),
                func.sum(UsageHourly.output_tokens).label("output_tokens"),
                func.sum(UsageHourly.call_count).label("call_count"),
            )
            .where(
                UsageHourly.workspace_id.in_(workspace_ids),
                UsageHourly.hour >= _bucket(t_from, "hour"),
                UsageHourly.hour < split,
                *(rollup_clauses or []),
            )
            .group_by(UsageHourly.hour)
        )
        for r in rows.all():
            _add(r.period, r.cost_usd, r.input_tokens, r.output_tokens, r.call_count)

    if granularity == "minute":
        period_col = func.date_trunc("minute", ProviderCall.created_at)
    elif granularity == "5min":
        period_col = func.to_timestamp(
            func.floor(func.extract("epoch", ProviderCall.created_at) / 300) * 300
        )
    else:
        period_col = func.date_trunc("hour", ProviderCall.created_at)
    period = period_col.label("period")
    raw = await db.execute(
        select(
            period,
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost_usd"),
            func.coalesce(func.sum(ProviderCall.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(ProviderCall.output_tokens), 0).label("output_tokens"),
            func.count(ProviderCall.id).label("call_count"),
        )
        .where(
            *_call_filters(workspace_ids, split, t_to, access, api_key_id),
            ProviderCall.status == "success",
        )
        .group_by(period)
    )
    for r in raw.all():
        _add(r.period, r.cost_usd, r.input_tokens, r.output_tokens, r.call_count)

    if not buckets:
        # SDK-only workspaces: runs carry totals but no provider calls.
        run_period = (
            func.date_trunc("minute", AgentRun.started_at)
            if granularity in {"minute", "5min"}
            else func.date_trunc("hour", AgentRun.started_at)
        ).label("period")
        rows2 = await db.execute(
            select(
                run_period,
                func.coalesce(func.sum(AgentRun.total_cost_usd), Decimal(0)).label("cost_usd"),
                func.coalesce(func.sum(AgentRun.total_input_tokens), 0).label("input_tokens"),
                func.coalesce(func.sum(AgentRun.total_output_tokens), 0).label("output_tokens"),
                func.count(AgentRun.id).label("call_count"),
            )
            .where(
                *run_filters(workspace_ids, t_from, t_to, access, api_key_id),
                AgentRun.status == RunStatusEnum.succeeded,
            )
            .group_by(run_period)
        )
        for r in rows2.all():
            _add(r.period, r.cost_usd, r.input_tokens, r.output_tokens, r.call_count)

    source = "rollup+raw" if unit and watermark and split > t_from else "raw"
    return [buckets[k] for k in sorted(buckets)], source


async def spend_by_model_rows(
    db: AsyncSession,
    *,
    workspace_ids: list[uuid.UUID],
    t_from: datetime,
    t_to: datetime,
    access: AccessGroupFilters | None = None,
    api_key_id: uuid.UUID | None = None,
) -> list[ModelRow]:
    """Spend by provider + model from the rollup plus the not-yet-rolled-up tail."""
    rollup_clauses = rollup_access_clauses(access)
    watermark = (
        await rollup_watermark(db, workspace_ids)
        if api_key_id is None and rollup_clauses is not None
        else None
    )
    # Only whole hours come from the rollup; partial edge hours stay raw.
    first_full_hour = _bucket(t_from, "hour")
    if first_full_hour < t_from:
        first_full_hour += timedelta(hours=1)
    split = min(max(watermark, first_full_hour), _bucket(t_to, "hour")) if watermark else t_from
    acc: dict[tuple[str, str], ModelRow] = {}

    def _add(provider: str, model: str, cost: Any, inp: Any, out: Any, calls: Any) -> None:
        row = acc.setdefault((provider, model), ModelRow(provider, model, Decimal(0), 0, 0, 0))
        row.cost_usd += Decimal(cost or 0)
        row.input_tokens += int(inp or 0)
        row.output_tokens += int(out or 0)
        row.call_count += int(calls or 0)

    def _raw_stmt(lo: datetime, hi: datetime) -> Any:
        return (
            select(
                ProviderCall.provider,
                ProviderCall.model,
                func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost_usd"),
                func.coalesce(func.sum(ProviderCall.input_tokens), 0).label("input_tokens"),
                func.coalesce(func.sum(ProviderCall.output_tokens), 0).label("output_tokens"),
                func.count(ProviderCall.id).label("call_count"),
            )
            .where(
                *_call_filters(workspace_ids, lo, hi, access, api_key_id),
                ProviderCall.status == "success",
            )
            .group_by(ProviderCall.provider, ProviderCall.model)
        )

    if watermark and split > first_full_hour:
        if first_full_hour > t_from:
            for r in (await db.execute(_raw_stmt(t_from, first_full_hour))).all():
                _add(r.provider, r.model, r.cost_usd, r.input_tokens, r.output_tokens, r.call_count)
        rows = await db.execute(
            select(
                UsageHourly.provider,
                UsageHourly.model,
                func.sum(UsageHourly.cost_usd).label("cost_usd"),
                func.sum(UsageHourly.input_tokens).label("input_tokens"),
                func.sum(UsageHourly.output_tokens).label("output_tokens"),
                func.sum(UsageHourly.call_count).label("call_count"),
            )
            .where(
                UsageHourly.workspace_id.in_(workspace_ids),
                UsageHourly.hour >= first_full_hour,
                UsageHourly.hour < split,
                *(rollup_clauses or []),
            )
            .group_by(UsageHourly.provider, UsageHourly.model)
        )
        for r in rows.all():
            _add(r.provider, r.model, r.cost_usd, r.input_tokens, r.output_tokens, r.call_count)
        lo = split
    else:
        lo = t_from
    for r in (await db.execute(_raw_stmt(lo, t_to))).all():
        _add(r.provider, r.model, r.cost_usd, r.input_tokens, r.output_tokens, r.call_count)
    return sorted(acc.values(), key=lambda m: m.cost_usd, reverse=True)
