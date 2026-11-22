"""
Billing service layer — periods, close/reopen, frozen snapshots, reconciliation,
exports, chargeback (rules → cost centers), shared-cost allocation.

All functions are pure async with no FastAPI dependencies so they can be imported
from Celery workers.

Cost definition: every total here uses ``services.billable`` — a call counts when it
has a priced cost and ``is_billable`` is true, whatever its status.

Closed periods are frozen: closing locks the period row, computes the totals and the
billing lines once, signs them with the workspace's billing key and stores them in a
``UsageSnapshot``. Breakdown and exports of a closed period read that snapshot, so
late-arriving data never changes a closed bill. Reopening (with a reason) unfreezes
the period; closing again writes a new snapshot.
"""

from __future__ import annotations

import calendar
import csv
import hashlib
import hmac
import io
import json
import uuid
from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import sqlalchemy as sa
import structlog
from sqlalchemy import func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.access_groups import AccessGroup, AccessGroupMember
from runledger_api.models.billing import (
    BillingAdjustment,
    BillingPeriod,
    ChargebackRule,
    CostAllocation,
    CostCenter,
    SharedCostPolicy,
    UsageSnapshot,
)
from runledger_api.models.budgets import Budget
from runledger_api.models.events import AgentRun, ProviderCall
from runledger_api.models.metering import UsageDaily
from runledger_api.models.tenant import ApiKey, Application, Workspace
from runledger_api.schemas.billing import (
    BillingAdjustmentResponse,
    BreakdownApp,
    BreakdownUser,
    ChargebackBreakdownItem,
    ChargebackReport,
    CostCenterNode,
    CostCenterReport,
    CostCenterReportRow,
    PeriodBreakdown,
    ReconciliationResult,
)
from runledger_api.services import billing_signing
from runledger_api.services.billable import billable_filters

log = structlog.get_logger()

_CREDIT_TYPES = ("credit", "refund", "prepaid_deduction")
_Q6 = Decimal("0.000001")

_CHARGEBACK_DIMENSIONS = {
    "workspace",
    "end_user",
    "application",
    "api_key",
    "access_group",
    "feature_tag",
    "workflow",
    "model",
    "provider",
    "intent",
}
# Dimensions a chargeback rule can map to a cost center (a rule names one value).
RULE_DIMENSIONS = {
    "feature_tag",
    "end_user",
    "application",
    "api_key",
    "access_group",
    "model",
    "provider",
    "intent",
}


class BillingConflict(ValueError):
    """A state conflict the router maps to 409."""


# ── Helpers ───────────────────────────────────────────────────────────────────


def _chargeback_period_bounds(period: str | None) -> tuple[str, date, date]:
    now = datetime.now(UTC)
    normalized = period or f"{now.year}-{now.month:02d}"
    try:
        year_str, month_str = normalized.split("-", 1)
        year, month = int(year_str), int(month_str)
        start = date(year, month, 1)
    except (ValueError, TypeError) as exc:
        raise ValueError("period must be YYYY-MM") from exc
    end = date(year, month, calendar.monthrange(year, month)[1])
    return f"{year}-{month:02d}", start, end


def csv_safe(value: Any) -> Any:
    """Neutralize spreadsheet formulas in exported text (review F-23).

    Text starting with = + - @ tab or CR is prefixed with a quote so spreadsheet
    apps show it as text instead of evaluating it. Numbers are left alone.
    """
    if value is None:
        return ""
    if isinstance(value, int | float | Decimal):
        return value
    text = str(value)
    if text and text[0] in ("=", "+", "-", "@", "\t", "\r"):
        try:
            Decimal(text)
            return text  # a plain negative number
        except ArithmeticError:
            return "'" + text
    return text


async def _validate_access_group_scope(
    db: AsyncSession, workspace_id: uuid.UUID, access_group_id: uuid.UUID
) -> AccessGroup:
    group = (
        await db.execute(
            select(AccessGroup).where(
                AccessGroup.id == access_group_id, AccessGroup.workspace_id == workspace_id
            )
        )
    ).scalar_one_or_none()
    if group is None:
        raise ValueError(f"AccessGroup {access_group_id} not found")
    return group


async def _validate_api_key_scope(
    db: AsyncSession, workspace_id: uuid.UUID, api_key_id: uuid.UUID
) -> ApiKey:
    key = (
        await db.execute(
            select(ApiKey).where(
                ApiKey.id == api_key_id,
                ApiKey.workspace_id == workspace_id,
                ApiKey.revoked_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if key is None:
        raise ValueError(f"ApiKey {api_key_id} not found")
    return key


def _access_group_member_filter(access_group_id: uuid.UUID) -> sa.ColumnElement[bool]:
    member_ids = select(sa.cast(AccessGroupMember.user_id, sa.String)).where(
        AccessGroupMember.group_id == access_group_id
    )
    return ProviderCall.end_user_id.in_(member_ids)


async def _member_ids(db: AsyncSession, access_group_id: uuid.UUID) -> set[str]:
    rows = await db.execute(
        select(sa.cast(AccessGroupMember.user_id, sa.String)).where(
            AccessGroupMember.group_id == access_group_id
        )
    )
    return {r[0] for r in rows}


async def _get_period(
    db: AsyncSession, billing_period_id: uuid.UUID, *, lock: bool = False
) -> BillingPeriod:
    stmt = select(BillingPeriod).where(BillingPeriod.id == billing_period_id)
    if lock:
        stmt = stmt.with_for_update()
    period = (await db.execute(stmt)).scalar_one_or_none()
    if period is None:
        raise ValueError(f"BillingPeriod {billing_period_id} not found")
    return period


async def latest_snapshot(db: AsyncSession, billing_period_id: uuid.UUID) -> UsageSnapshot | None:
    return (
        await db.execute(
            select(UsageSnapshot)
            .where(UsageSnapshot.billing_period_id == billing_period_id)
            .order_by(UsageSnapshot.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


def _period_call_filters(period: BillingPeriod) -> list[sa.ColumnElement[bool]]:
    return [
        ProviderCall.workspace_id == period.workspace_id,
        func.date(ProviderCall.created_at) >= period.period_start,
        func.date(ProviderCall.created_at) <= period.period_end,
        *billable_filters(),
    ]


def to_local(amount_usd: Decimal, exchange_rate_to_usd: Decimal) -> Decimal:
    """USD → period currency (exchange_rate_to_usd = USD per 1 unit of currency)."""
    if not exchange_rate_to_usd:
        return amount_usd
    return (amount_usd / exchange_rate_to_usd).quantize(_Q6)


# ── Periods ───────────────────────────────────────────────────────────────────


async def check_period_overlap(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    period_start: date,
    period_end: date,
    exclude_id: uuid.UUID | None = None,
) -> None:
    """Raise BillingConflict if [start, end] overlaps another period (review F-11)."""
    stmt = select(BillingPeriod.id, BillingPeriod.period_start, BillingPeriod.period_end).where(
        BillingPeriod.workspace_id == workspace_id,
        BillingPeriod.period_start <= period_end,
        BillingPeriod.period_end >= period_start,
    )
    if exclude_id is not None:
        stmt = stmt.where(BillingPeriod.id != exclude_id)
    clash = (await db.execute(stmt.limit(1))).first()
    if clash is not None:
        raise BillingConflict(f"Overlaps billing period {clash.period_start} to {clash.period_end}")


async def get_period_total_cost(
    db: AsyncSession, workspace_id: uuid.UUID, period_start: Any, period_end: Any
) -> Decimal:
    """Billable cost for the date range."""
    result = await db.execute(
        select(func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0))).where(
            ProviderCall.workspace_id == workspace_id,
            func.date(ProviderCall.created_at) >= period_start,
            func.date(ProviderCall.created_at) <= period_end,
            *billable_filters(),
        )
    )
    return result.scalar_one() or Decimal(0)


def _adjustment_totals(adjustments: list[Any]) -> tuple[Decimal, Decimal]:
    deductions = sum(
        (Decimal(str(a.amount_usd)) for a in adjustments if a.adjustment_type in _CREDIT_TYPES),
        Decimal(0),
    )
    surcharges = sum(
        (Decimal(str(a.amount_usd)) for a in adjustments if a.adjustment_type == "surcharge"),
        Decimal(0),
    )
    return deductions, surcharges


async def _compute_lines(db: AsyncSession, period: BillingPeriod) -> list[dict[str, Any]]:
    """Billing lines: billable cost per day × application × key × end user × model."""
    day = func.date(ProviderCall.created_at).label("day")
    rows = (
        await db.execute(
            select(
                day,
                AgentRun.application_id,
                ProviderCall.api_key_id,
                ProviderCall.end_user_id,
                ProviderCall.model,
                ProviderCall.provider,
                func.count(ProviderCall.id).label("calls"),
                func.count(func.distinct(ProviderCall.run_id)).label("runs"),
                func.coalesce(func.sum(ProviderCall.input_tokens), 0).label("input_tokens"),
                func.coalesce(func.sum(ProviderCall.output_tokens), 0).label("output_tokens"),
                func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost_usd"),
            )
            .select_from(ProviderCall)
            .outerjoin(AgentRun, AgentRun.id == ProviderCall.run_id)
            .where(*_period_call_filters(period))
            .group_by(
                day,
                AgentRun.application_id,
                ProviderCall.api_key_id,
                ProviderCall.end_user_id,
                ProviderCall.model,
                ProviderCall.provider,
            )
            .order_by(day, ProviderCall.end_user_id, ProviderCall.model)
        )
    ).all()
    return [
        {
            "date": str(r.day),
            "application_id": str(r.application_id) if r.application_id else None,
            "api_key_id": str(r.api_key_id) if r.api_key_id else None,
            "end_user_id": r.end_user_id,
            "model": r.model,
            "provider": r.provider,
            "calls": int(r.calls),
            "runs": int(r.runs),
            "input_tokens": int(r.input_tokens),
            "output_tokens": int(r.output_tokens),
            "cost_usd": str(r.cost_usd),
        }
        for r in rows
    ]


async def _period_lines(
    db: AsyncSession, period: BillingPeriod
) -> tuple[list[dict[str, Any]], UsageSnapshot | None]:
    """Frozen lines for a closed period, live lines otherwise."""
    if period.status == "closed":
        snap = await latest_snapshot(db, period.id)
        if snap is not None and "lines" in (snap.snapshot_data or {}):
            return list(snap.snapshot_data["lines"]), snap
    return await _compute_lines(db, period), None


async def _filter_lines(
    db: AsyncSession,
    period: BillingPeriod,
    lines: list[dict[str, Any]],
    access_group_id: uuid.UUID | None,
    api_key_id: uuid.UUID | None,
    end_user_id: str | None = None,
) -> list[dict[str, Any]]:
    if access_group_id is not None:
        await _validate_access_group_scope(db, period.workspace_id, access_group_id)
        members = await _member_ids(db, access_group_id)
        lines = [ln for ln in lines if ln.get("end_user_id") in members]
    if api_key_id is not None:
        await _validate_api_key_scope(db, period.workspace_id, api_key_id)
        lines = [ln for ln in lines if ln.get("api_key_id") == str(api_key_id)]
    if end_user_id is not None:
        lines = [ln for ln in lines if ln.get("end_user_id") == end_user_id]
    return lines


async def close_billing_period(
    db: AsyncSession, billing_period_id: uuid.UUID, closed_by: str | None = None
) -> UsageSnapshot:
    """Close a period: lock it, freeze totals and lines, sign, store a snapshot.

    The period row is locked (SELECT … FOR UPDATE) for the whole close, so two
    concurrent closes can't both succeed; a second one sees ``closed`` and fails
    with BillingConflict (review F-08).
    """
    period = await _get_period(db, billing_period_id, lock=True)
    if period.status in ("closed", "closing"):
        raise BillingConflict("already_closed")

    workspace = await db.get(Workspace, period.workspace_id, with_for_update=False)
    version = int(getattr(workspace, "billing_signing_version", 1) or 1)

    lines = await _compute_lines(db, period)
    total_cost = sum((Decimal(ln["cost_usd"]) for ln in lines), Decimal(0))

    by_model: dict[tuple[str, str], dict[str, Any]] = {}
    for ln in lines:
        key = (ln["model"], ln["provider"])
        agg = by_model.setdefault(
            key,
            {
                "model": ln["model"],
                "provider": ln["provider"],
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": Decimal(0),
                "call_count": 0,
            },
        )
        agg["input_tokens"] += ln["input_tokens"]
        agg["output_tokens"] += ln["output_tokens"]
        agg["cost_usd"] += Decimal(ln["cost_usd"])
        agg["call_count"] += ln["calls"]

    adjustments = list(
        (
            await db.execute(
                select(BillingAdjustment)
                .where(BillingAdjustment.billing_period_id == billing_period_id)
                .order_by(BillingAdjustment.created_at)
            )
        ).scalars()
    )
    deductions, surcharges = _adjustment_totals(adjustments)
    net_cost = max(total_cost - deductions + surcharges, Decimal(0))

    now = datetime.now(UTC)
    snapshot_data: dict[str, Any] = {
        "period_id": str(billing_period_id),
        "workspace_id": str(period.workspace_id),
        "period_start": str(period.period_start),
        "period_end": str(period.period_end),
        "total_cost_usd": str(total_cost),
        "net_cost_usd": str(net_cost),
        "total_deductions_usd": str(deductions),
        "total_surcharges_usd": str(surcharges),
        "currency": period.currency,
        "exchange_rate_to_usd": str(period.exchange_rate_to_usd),
        "net_cost_local": str(to_local(net_cost, period.exchange_rate_to_usd)),
        "closed_at": now.isoformat(),
        "closed_by": closed_by,
        "by_model": [
            {**v, "cost_usd": str(v["cost_usd"])}
            for v in sorted(by_model.values(), key=lambda x: (x["model"], x["provider"]))
        ],
        "adjustments": [
            {
                "id": str(a.id),
                "adjustment_type": a.adjustment_type,
                "amount_usd": str(a.amount_usd),
                "description": a.description,
                "reference_id": a.reference_id,
                "created_by": a.created_by,
            }
            for a in adjustments
        ],
        "lines": lines,
    }
    signature, signing_key_id = billing_signing.sign(snapshot_data, period.workspace_id, version)

    snapshot = UsageSnapshot(
        billing_period_id=billing_period_id,
        snapshot_data=snapshot_data,
        signature=signature,
        signing_key_id=signing_key_id,
    )
    db.add(snapshot)
    period.status = "closed"
    period.total_cost_usd = total_cost
    period.net_cost_usd = net_cost
    period.snapshot_hash = signature[:16]
    period.closed_at = now
    period.closed_by = closed_by
    await db.flush()
    await db.commit()
    await db.refresh(snapshot)

    log.info(
        "billing_period_closed",
        period_id=str(billing_period_id),
        total_cost_usd=str(total_cost),
        snapshot_id=str(snapshot.id),
        lines=len(lines),
    )
    return snapshot


async def reopen_billing_period(
    db: AsyncSession, billing_period_id: uuid.UUID, reason: str
) -> BillingPeriod:
    """Reopen a closed period. Snapshots are kept as history; closing again re-freezes."""
    period = await _get_period(db, billing_period_id, lock=True)
    if period.status != "closed":
        raise BillingConflict("Only a closed billing period can be reopened")
    period.status = "open"
    period.reopened_at = datetime.now(UTC)
    period.reopen_reason = reason
    period.snapshot_hash = None
    await db.commit()
    await db.refresh(period)
    return period


# ── Reconciliation ────────────────────────────────────────────────────────────


async def run_reconciliation(
    db: AsyncSession,
    billing_period_id: uuid.UUID,
    access_group_id: uuid.UUID | None = None,
    api_key_id: uuid.UUID | None = None,
) -> ReconciliationResult:
    """Cross-check billable provider-call cost with the usage_daily rollup, and look
    for orphaned and duplicate calls. For a closed period, also check the frozen
    snapshot still matches live data and its signature."""
    period = await _get_period(db, billing_period_id)
    workspace_id = period.workspace_id
    scoped_filters = _period_call_filters(period)
    if access_group_id is not None:
        await _validate_access_group_scope(db, workspace_id, access_group_id)
        scoped_filters.append(_access_group_member_filter(access_group_id))
    if api_key_id is not None:
        await _validate_api_key_scope(db, workspace_id, api_key_id)
        scoped_filters.append(ProviderCall.api_key_id == api_key_id)

    calls_sum: Decimal = (
        await db.execute(
            select(func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0))).where(
                *scoped_filters
            )
        )
    ).scalar_one() or Decimal(0)

    if access_group_id is None and api_key_id is None:
        daily_sum: Decimal = (
            await db.execute(
                select(func.coalesce(func.sum(UsageDaily.cost_usd), Decimal(0))).where(
                    UsageDaily.workspace_id == workspace_id,
                    UsageDaily.day >= period.period_start,
                    UsageDaily.day <= period.period_end,
                )
            )
        ).scalar_one() or Decimal(0)
        delta_pct = abs(calls_sum - daily_sum) / calls_sum * 100 if calls_sum > 0 else Decimal(0)
    else:
        daily_sum = calls_sum
        delta_pct = Decimal(0)

    orphaned_calls: int = (
        await db.execute(
            select(func.count(ProviderCall.id))
            .outerjoin(AgentRun, ProviderCall.run_id == AgentRun.id)
            .where(*scoped_filters, AgentRun.id.is_(None))
        )
    ).scalar_one() or 0

    ts_trunc = func.date_trunc(literal_column("'second'"), ProviderCall.created_at)
    dup_subq = (
        select(ProviderCall.run_id, ProviderCall.model, ts_trunc.label("ts"), func.count())
        .where(*scoped_filters)
        .group_by(ProviderCall.run_id, ProviderCall.model, ts_trunc)
        .having(func.count() > 1)
        .subquery()
    )
    duplicate_calls: int = (
        await db.execute(select(func.count()).select_from(dup_subq))
    ).scalar_one() or 0

    issues: list[str] = []
    warnings: list[str] = []
    recon_status = "pass"
    if access_group_id is not None or api_key_id is not None:
        warnings.append(
            "Scoped reconciliation validates provider-call attribution only; "
            "usage_daily remains workspace-aggregated."
        )
    if delta_pct > Decimal("0.01"):
        issues.append(
            f"Cost delta {delta_pct:.4f}% exceeds 0.01% threshold "
            f"(calls={calls_sum}, daily={daily_sum})"
        )
        recon_status = "fail"
    if orphaned_calls > 0:
        issues.append(f"{orphaned_calls} orphaned provider_call(s) with no matching agent_run")
        recon_status = "fail"
    if duplicate_calls > 0:
        warnings.append(
            f"{duplicate_calls} duplicate provider_call group(s) detected (data quality warning)"
        )
        if recon_status == "pass":
            recon_status = "warning"

    if period.status == "closed" and access_group_id is None and api_key_id is None:
        snap = await latest_snapshot(db, period.id)
        if snap is not None:
            if not billing_signing.verify(
                snap.snapshot_data, snap.signature, workspace_id, snap.signing_key_id
            ):
                issues.append("Frozen snapshot signature does not verify")
                recon_status = "fail"
            frozen = Decimal(str(snap.snapshot_data.get("total_cost_usd", "0")))
            if frozen != calls_sum:
                warnings.append(
                    f"Live billable cost ({calls_sum}) differs from the frozen total "
                    f"({frozen}): data arrived after close. The closed bill is unchanged; "
                    "reopen and close again to include it."
                )
                if recon_status == "pass":
                    recon_status = "warning"

    log.info(
        "reconciliation_complete",
        period_id=str(billing_period_id),
        status=recon_status,
        calls_sum=str(calls_sum),
        daily_sum=str(daily_sum),
    )
    return ReconciliationResult(
        period_id=str(billing_period_id),
        status=recon_status,
        provider_calls_sum=calls_sum,
        usage_daily_sum=daily_sum,
        delta_pct=delta_pct,
        orphaned_calls=orphaned_calls,
        duplicate_calls=duplicate_calls,
        issues=issues,
        warnings=warnings,
    )


# ── Breakdown ─────────────────────────────────────────────────────────────────


async def get_period_breakdown(
    db: AsyncSession,
    billing_period_id: uuid.UUID,
    access_group_id: uuid.UUID | None = None,
    api_key_id: uuid.UUID | None = None,
    end_user_id: str | None = None,
) -> PeriodBreakdown:
    """Application → end user cost, from frozen lines once the period is closed."""
    period = await _get_period(db, billing_period_id)
    lines, snap = await _period_lines(db, period)
    lines = await _filter_lines(db, period, lines, access_group_id, api_key_id, end_user_id)

    apps: dict[str | None, dict[str | None, dict[str, Any]]] = defaultdict(dict)
    total_cost = Decimal(0)
    for ln in lines:
        cost = Decimal(ln["cost_usd"])
        total_cost += cost
        users = apps[ln.get("application_id")]
        u = users.setdefault(ln.get("end_user_id"), {"cost_usd": Decimal(0), "run_count": 0})
        u["cost_usd"] += cost
        u["run_count"] += int(ln.get("runs", 0))

    by_application = [
        BreakdownApp(
            application_id=app_id,
            cost_usd=sum((u["cost_usd"] for u in users.values()), Decimal(0)),
            users=[
                BreakdownUser(end_user_id=uid, cost_usd=u["cost_usd"], run_count=u["run_count"])
                for uid, u in users.items()
            ],
        )
        for app_id, users in apps.items()
    ]

    # Adjustments can't change while a period is closed, so the live rows equal the
    # frozen ones.
    live = await get_period_adjustments(db, period.workspace_id, billing_period_id)
    adj_responses = [BillingAdjustmentResponse.model_validate(a) for a in live]
    deductions, surcharges = _adjustment_totals(live)
    total_adjustments = surcharges - deductions
    net_cost = max(total_cost + total_adjustments, Decimal(0))

    return PeriodBreakdown(
        period_id=str(billing_period_id),
        gross_cost_usd=total_cost,
        net_cost_usd=net_cost,
        total_adjustments_usd=total_adjustments,
        by_application=by_application,
        adjustments=adj_responses,
        frozen=snap is not None,
    )


# ── Exports ───────────────────────────────────────────────────────────────────

_LINE_COLUMNS = [
    "date",
    "application_id",
    "api_key_id",
    "end_user_id",
    "model",
    "provider",
    "calls",
    "input_tokens",
    "output_tokens",
    "cost_usd",
]


async def export_csv(
    db: AsyncSession,
    billing_period_id: uuid.UUID,
    access_group_id: uuid.UUID | None = None,
    api_key_id: uuid.UUID | None = None,
) -> str:
    """Billing lines as CSV (frozen lines for a closed period). Cells are escaped
    against spreadsheet formula injection."""
    period = await _get_period(db, billing_period_id)
    lines, _ = await _period_lines(db, period)
    lines = await _filter_lines(db, period, lines, access_group_id, api_key_id)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(_LINE_COLUMNS)
    for ln in lines:
        writer.writerow([csv_safe(ln.get(col)) for col in _LINE_COLUMNS])
    return buf.getvalue()


async def export_signed_json(
    db: AsyncSession,
    billing_period_id: uuid.UUID,
    access_group_id: uuid.UUID | None = None,
    api_key_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Billing lines + totals, signed with the workspace's billing key.

    ``signature`` covers every other field (canonical JSON, sorted keys). Verify with
    ``POST /billing/verify`` or locally with the key from ``GET /billing/signing-key``.
    """
    period = await _get_period(db, billing_period_id)
    lines, snap = await _period_lines(db, period)
    lines = await _filter_lines(db, period, lines, access_group_id, api_key_id)
    total_cost = sum((Decimal(ln["cost_usd"]) for ln in lines), Decimal(0))

    workspace = await db.get(Workspace, period.workspace_id)
    version = int(getattr(workspace, "billing_signing_version", 1) or 1)
    payload: dict[str, Any] = {
        "period_id": str(billing_period_id),
        "workspace_id": str(period.workspace_id),
        "period_start": str(period.period_start),
        "period_end": str(period.period_end),
        "status": period.status,
        "frozen": snap is not None,
        "snapshot_id": str(snap.id) if snap is not None else None,
        "currency": period.currency,
        "exchange_rate_to_usd": str(period.exchange_rate_to_usd),
        "total_cost_usd": str(total_cost),
        "total_cost_local": str(to_local(total_cost, period.exchange_rate_to_usd)),
        "scope": {
            "access_group_id": str(access_group_id) if access_group_id else None,
            "api_key_id": str(api_key_id) if api_key_id else None,
        },
        "lines": lines,
    }
    signature, signing_key_id = billing_signing.sign(payload, period.workspace_id, version)
    payload["signing_key_id"] = signing_key_id
    payload["signature"] = signature
    return payload


def sign_snapshot(data: dict[str, Any], key: str) -> str:
    """HMAC-SHA256 of canonical JSON with an explicit key (used by the cost ledger)."""
    body = json.dumps(data, sort_keys=True, default=str).encode()
    return hmac.new(key.encode(), body, hashlib.sha256).hexdigest()


# ── Chargeback report ─────────────────────────────────────────────────────────


def _budget_for_month(period_type: str, limit_usd: Decimal, days_in_month: int) -> Decimal | None:
    """A budget's limit expressed for one calendar month, or None if it has no
    monthly equivalent (review F-18: variance must compare like with like)."""
    if period_type == "monthly":
        return limit_usd
    if period_type == "daily":
        return limit_usd * days_in_month
    if period_type == "weekly":
        return (limit_usd * Decimal(days_in_month) / Decimal(7)).quantize(Decimal("0.01"))
    return None


async def _dimension_rows(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    dimension: str,
    period_start: date,
    period_end: date,
    *,
    access_group_id: uuid.UUID | None = None,
    api_key_id: uuid.UUID | None = None,
    end_user_id: str | None = None,
) -> list[Any]:
    """Billable cost per dimension value: rows of (key, label, cost, calls, runs)."""
    stmt: Any
    if dimension == "workspace":
        key_expr, label_expr = Workspace.id, Workspace.name
        stmt = (
            select()
            .select_from(ProviderCall)
            .join(Workspace, Workspace.id == ProviderCall.workspace_id)
        )
    elif dimension == "end_user":
        key_expr = label_expr = ProviderCall.end_user_id
        stmt = select().select_from(ProviderCall)
    elif dimension == "application":
        key_expr, label_expr = AgentRun.application_id, Application.name
        stmt = (
            select()
            .select_from(ProviderCall)
            .outerjoin(AgentRun, AgentRun.id == ProviderCall.run_id)
            .outerjoin(Application, Application.id == AgentRun.application_id)
        )
    elif dimension == "api_key":
        key_expr = ProviderCall.api_key_id
        label_expr = func.coalesce(ApiKey.name, ApiKey.key_prefix)
        stmt = (
            select()
            .select_from(ProviderCall)
            .outerjoin(ApiKey, ApiKey.id == ProviderCall.api_key_id)
        )
    elif dimension == "access_group":
        # Attribute each user to exactly one group — their earliest membership — so a
        # user in two groups isn't counted twice (review F-18).
        primary = (
            select(AccessGroupMember.user_id, AccessGroupMember.group_id)
            .join(AccessGroup, AccessGroup.id == AccessGroupMember.group_id)
            .where(AccessGroup.workspace_id == workspace_id)
            .distinct(AccessGroupMember.user_id)
            .order_by(
                AccessGroupMember.user_id,
                AccessGroupMember.created_at,
                AccessGroupMember.group_id,
            )
            .subquery()
        )
        key_expr, label_expr = AccessGroup.id, AccessGroup.name
        stmt = (
            select()
            .select_from(ProviderCall)
            .outerjoin(primary, sa.cast(primary.c.user_id, sa.String) == ProviderCall.end_user_id)
            .outerjoin(AccessGroup, AccessGroup.id == primary.c.group_id)
        )
    elif dimension in {"feature_tag", "workflow"}:
        key_expr = label_expr = AgentRun.feature_tag
        stmt = (
            select()
            .select_from(ProviderCall)
            .outerjoin(AgentRun, AgentRun.id == ProviderCall.run_id)
        )
    elif dimension == "intent":
        key_expr = label_expr = AgentRun.intent
        stmt = (
            select()
            .select_from(ProviderCall)
            .outerjoin(AgentRun, AgentRun.id == ProviderCall.run_id)
        )
    elif dimension == "model":
        key_expr = label_expr = ProviderCall.model
        stmt = select().select_from(ProviderCall)
    elif dimension == "provider":
        key_expr = label_expr = ProviderCall.provider
        stmt = select().select_from(ProviderCall)
    else:
        raise ValueError(f"Unsupported chargeback dimension: {dimension}")

    filters: list[sa.ColumnElement[bool]] = [
        ProviderCall.workspace_id == workspace_id,
        func.date(ProviderCall.created_at) >= period_start,
        func.date(ProviderCall.created_at) <= period_end,
        *billable_filters(),
    ]
    if access_group_id is not None:
        await _validate_access_group_scope(db, workspace_id, access_group_id)
        filters.append(_access_group_member_filter(access_group_id))
    if api_key_id is not None:
        await _validate_api_key_scope(db, workspace_id, api_key_id)
        filters.append(ProviderCall.api_key_id == api_key_id)
    if end_user_id is not None:
        filters.append(ProviderCall.end_user_id == end_user_id)

    stmt = (
        stmt.add_columns(
            key_expr.label("dimension_key"),
            label_expr.label("dimension_label"),
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost_usd"),
            func.count(ProviderCall.id).label("call_count"),
            func.count(func.distinct(ProviderCall.run_id)).label("run_count"),
        )
        .where(*filters)
        .group_by(key_expr, label_expr)
        .order_by(func.sum(ProviderCall.cost_usd).desc().nulls_last())
    )
    return list((await db.execute(stmt)).all())


_BUDGET_SCOPE = {
    "workspace": "workspace",
    "end_user": "end_user",
    "application": "app",
    "api_key": "api_key",
    "access_group": "access_group",
    "feature_tag": "feature_tag",
    "workflow": "feature_tag",
}


async def build_chargeback_report(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    *,
    period: str | None = None,
    dimension: str | None = None,
    access_group_id: uuid.UUID | None = None,
    api_key_id: uuid.UUID | None = None,
    end_user_id: str | None = None,
) -> ChargebackReport:
    """Billable cost for one month by dimension, with budget variance where a
    budget of the same scope has a monthly equivalent."""
    chosen = dimension or "feature_tag"
    if chosen not in _CHARGEBACK_DIMENSIONS:
        raise ValueError(f"Unsupported chargeback dimension: {chosen}")
    period_label, period_start, period_end = _chargeback_period_bounds(period)
    days_in_month = (period_end - period_start).days + 1

    rows = await _dimension_rows(
        db,
        workspace_id,
        chosen,
        period_start,
        period_end,
        access_group_id=access_group_id,
        api_key_id=api_key_id,
        end_user_id=end_user_id,
    )
    total_cost = sum((row.cost_usd or Decimal(0) for row in rows), Decimal(0))

    budget_map: dict[str, tuple[str, Decimal]] = {}
    scope_type = _BUDGET_SCOPE.get(chosen)
    if scope_type is not None:
        for scope_id, period_type, limit_usd in (
            await db.execute(
                select(Budget.scope_id, Budget.period_type, Budget.limit_usd).where(
                    Budget.workspace_id == workspace_id,
                    Budget.scope_type == scope_type,
                    Budget.is_active.is_(True),
                )
            )
        ).all():
            if scope_id is not None:
                budget_map[str(scope_id)] = (period_type, limit_usd)
    if chosen == "workspace":
        for period_type, limit_usd in (
            await db.execute(
                select(Budget.period_type, Budget.limit_usd).where(
                    Budget.workspace_id == workspace_id,
                    Budget.scope_type == "workspace",
                    Budget.is_active.is_(True),
                )
            )
        ).all():
            budget_map[str(workspace_id)] = (period_type, limit_usd)

    items: list[ChargebackBreakdownItem] = []
    covered_cost = Decimal(0)
    unallocated_cost = Decimal(0)
    for row in rows:
        cost = row.cost_usd or Decimal(0)
        raw_label = row.dimension_label or row.dimension_key
        dimension_value = str(raw_label) if raw_label is not None else "Unallocated"
        allocation_status = "allocated" if raw_label is not None else "unallocated"
        if allocation_status == "unallocated":
            unallocated_cost += cost
        budget_value: Decimal | None = None
        variance: Decimal | None = None
        coverage_status = "unbudgeted"
        key = str(row.dimension_key) if row.dimension_key is not None else None
        if key is not None and key in budget_map:
            period_type, limit_usd = budget_map[key]
            budget_value = _budget_for_month(period_type, limit_usd, days_in_month)
            coverage_status = "budgeted" if budget_value is not None else "budgeted_other_period"
            covered_cost += cost
            if budget_value is not None:
                variance = (cost - budget_value).quantize(Decimal("0.01"))
        items.append(
            ChargebackBreakdownItem(
                dimension="feature_tag" if chosen == "workflow" else chosen,
                dimension_key=key,
                dimension_value=dimension_value,
                cost_usd=cost,
                pct_of_total=(cost / total_cost * Decimal(100)).quantize(Decimal("0.01"))
                if total_cost > 0
                else Decimal(0),
                budget_usd=budget_value,
                variance_usd=variance,
                call_count=int(row.call_count or 0),
                run_count=int(row.run_count or 0),
                allocation_status=allocation_status,
                coverage_status=coverage_status,
            )
        )

    return ChargebackReport(
        period=period_label,
        dimension=chosen,
        total_cost_usd=total_cost.quantize(Decimal("0.0001")) if total_cost else Decimal("0"),
        covered_cost_usd=covered_cost.quantize(Decimal("0.0001")) if covered_cost else Decimal("0"),
        unallocated_cost_usd=unallocated_cost.quantize(Decimal("0.0001"))
        if unallocated_cost
        else Decimal("0"),
        breakdown=items,
    )


async def build_cost_center_report(
    db: AsyncSession, workspace_id: uuid.UUID, *, period: str | None = None
) -> CostCenterReport:
    """Apply active chargeback rules and shared-cost allocations for one month.

    direct_usd: the month's billable cost of each mapped dimension value × rule weight.
    shared_usd: shared-cost pools applied to the month (``cost_allocations``).
    unassigned_usd: billable cost no active rule covers.
    """
    period_label, period_start, period_end = _chargeback_period_bounds(period)
    rules = list(
        (
            await db.execute(
                select(ChargebackRule).where(
                    ChargebackRule.workspace_id == workspace_id,
                    ChargebackRule.status == "active",
                    ChargebackRule.dimension_value.is_not(None),
                    ChargebackRule.cost_center_id.is_not(None),
                )
            )
        ).scalars()
    )
    centers = {
        c.id: c
        for c in (
            await db.execute(select(CostCenter).where(CostCenter.workspace_id == workspace_id))
        ).scalars()
    }

    total_cost: Decimal = await get_period_total_cost(db, workspace_id, period_start, period_end)
    direct: dict[uuid.UUID, Decimal] = defaultdict(Decimal)
    rule_dimension = rules[0].dimension if rules else None
    assigned = Decimal(0)
    if rule_dimension is not None:
        value_cost = {
            str(r.dimension_key): (r.cost_usd or Decimal(0))
            for r in await _dimension_rows(
                db, workspace_id, rule_dimension, period_start, period_end
            )
            if r.dimension_key is not None
        }
        for rule in rules:
            if rule.cost_center_id not in centers:
                continue
            share = (value_cost.get(str(rule.dimension_value), Decimal(0)) * rule.weight).quantize(
                _Q6
            )
            direct[rule.cost_center_id] += share
            assigned += share

    shared: dict[uuid.UUID | None, Decimal] = defaultdict(Decimal)
    for alloc in (
        await db.execute(
            select(CostAllocation).where(
                CostAllocation.workspace_id == workspace_id, CostAllocation.period == period_label
            )
        )
    ).scalars():
        shared[alloc.cost_center_id] += alloc.amount_usd

    rows: list[CostCenterReportRow] = []
    for cc_id in sorted(
        set(direct) | {k for k in shared if k is not None},
        key=lambda i: centers[i].name if i in centers else "",
    ):
        cc = centers.get(cc_id)
        d = direct.get(cc_id, Decimal(0))
        s = shared.get(cc_id, Decimal(0))
        rows.append(
            CostCenterReportRow(
                cost_center_id=cc_id,
                name=cc.name if cc else "(deleted cost center)",
                code=cc.code if cc else None,
                direct_usd=d,
                shared_usd=s,
                total_usd=d + s,
            )
        )
    return CostCenterReport(
        period=period_label,
        rule_dimension=rule_dimension,
        total_billable_usd=total_cost,
        assigned_usd=assigned,
        unassigned_usd=max(total_cost - assigned, Decimal(0)),
        shared_usd=sum(shared.values(), Decimal(0)),
        unassigned_shared_usd=shared.get(None, Decimal(0)),
        rows=rows,
    )


# ── Chargeback rules: validation ─────────────────────────────────────────────


async def validate_rule(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    *,
    dimension: str,
    dimension_value: str,
    cost_center_id: uuid.UUID,
    weight: Decimal,
    allocation_type: str,
    exclude_rule_id: uuid.UUID | None = None,
    activating: bool,
) -> None:
    """Validate a rule before it is saved or activated (review F-02).

    - the dimension is mappable and the cost center belongs to the workspace;
    - ``direct`` rules carry weight 1;
    - active weights for one dimension value add up to at most 1;
    - all active rules use one dimension, so a call is never charged twice through
      two different dimensions.
    """
    if dimension not in RULE_DIMENSIONS:
        raise ValueError(f"dimension must be one of: {', '.join(sorted(RULE_DIMENSIONS))}")
    if not dimension_value.strip():
        raise ValueError("dimension_value is required")
    if weight <= 0 or weight > 1:
        raise ValueError("weight must be greater than 0 and at most 1")
    if allocation_type == "direct" and weight != 1:
        raise ValueError("direct rules assign the whole cost: weight must be 1")
    cc = (
        await db.execute(
            select(CostCenter.id).where(
                CostCenter.id == cost_center_id, CostCenter.workspace_id == workspace_id
            )
        )
    ).scalar_one_or_none()
    if cc is None:
        raise ValueError("Cost center not found in this workspace")
    if not activating:
        return
    others = select(ChargebackRule).where(
        ChargebackRule.workspace_id == workspace_id, ChargebackRule.status == "active"
    )
    if exclude_rule_id is not None:
        others = others.where(ChargebackRule.id != exclude_rule_id)
    active = list((await db.execute(others)).scalars())
    other_dims = {r.dimension for r in active}
    if other_dims and dimension not in other_dims:
        raise BillingConflict(
            f"Active chargeback rules map by {', '.join(sorted(other_dims))}; "
            f"deactivate them before mapping by {dimension}"
        )
    used = sum((r.weight for r in active if r.dimension_value == dimension_value), Decimal(0))
    if used + weight > 1:
        raise BillingConflict(
            f"Active weights for {dimension}={dimension_value} would total {used + weight}; "
            "they must not exceed 1"
        )


# ── Cost centers ──────────────────────────────────────────────────────────────


async def get_cost_center_tree(db: AsyncSession, workspace_id: uuid.UUID) -> list[CostCenterNode]:
    """The cost center hierarchy as a forest."""
    all_centers = list(
        (
            await db.execute(
                select(CostCenter)
                .where(CostCenter.workspace_id == workspace_id)
                .order_by(CostCenter.name)
            )
        ).scalars()
    )
    nodes = {
        c.id: CostCenterNode(
            id=c.id,
            name=c.name,
            code=c.code,
            parent_id=c.parent_id,
            description=c.description,
            children=[],
        )
        for c in all_centers
    }
    roots: list[CostCenterNode] = []
    for c in all_centers:
        if c.parent_id and c.parent_id in nodes:
            nodes[c.parent_id].children.append(nodes[c.id])
        else:
            roots.append(nodes[c.id])
    return roots


async def validate_cost_center_parent(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    parent_id: uuid.UUID | None,
    center_id: uuid.UUID | None = None,
) -> None:
    """Parent must be in the workspace and must not create a cycle."""
    if parent_id is None:
        return
    if center_id is not None and parent_id == center_id:
        raise ValueError("A cost center cannot be its own parent")
    parents = {
        c.id: c.parent_id
        for c in (
            await db.execute(select(CostCenter).where(CostCenter.workspace_id == workspace_id))
        ).scalars()
    }
    if parent_id not in parents:
        raise ValueError("Parent cost center not found in this workspace")
    seen: set[uuid.UUID] = set()
    cursor: uuid.UUID | None = parent_id
    while cursor is not None:
        if cursor == center_id:
            raise ValueError("That parent would create a cycle")
        if cursor in seen:
            break
        seen.add(cursor)
        cursor = parents.get(cursor)


# ── Adjustments ───────────────────────────────────────────────────────────────


async def add_adjustment(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    billing_period_id: uuid.UUID,
    adjustment_type: str,
    amount_usd: Decimal,
    description: str | None,
    reference_id: str | None,
    created_by: str | None,
) -> BillingAdjustment:
    """Create an adjustment on an open period."""
    period = (
        await db.execute(
            select(BillingPeriod)
            .where(
                BillingPeriod.id == billing_period_id, BillingPeriod.workspace_id == workspace_id
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if period is None:
        raise ValueError("BillingPeriod not found")
    if period.status != "open":
        raise BillingConflict("Cannot add adjustments to a closed billing period")
    adj = BillingAdjustment(
        workspace_id=workspace_id,
        billing_period_id=billing_period_id,
        adjustment_type=adjustment_type,
        amount_usd=amount_usd,
        description=description,
        reference_id=reference_id,
        created_by=created_by,
    )
    db.add(adj)
    await db.flush()
    return adj


async def get_period_adjustments(
    db: AsyncSession, workspace_id: uuid.UUID, billing_period_id: uuid.UUID
) -> list[BillingAdjustment]:
    return list(
        (
            await db.execute(
                select(BillingAdjustment)
                .where(
                    BillingAdjustment.billing_period_id == billing_period_id,
                    BillingAdjustment.workspace_id == workspace_id,
                )
                .order_by(BillingAdjustment.created_at)
            )
        ).scalars()
    )


# ── Shared-cost policies ──────────────────────────────────────────────────────


async def validate_shared_cost_allocations(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    formula_type: str,
    allocations: list[dict[str, Any]],
) -> None:
    """Validate a policy's targets (review F-17)."""
    if not allocations:
        return
    ids = {a.get("cost_center_id") for a in allocations if a.get("cost_center_id")}
    if ids:
        found = {
            str(i)
            for i in (
                await db.execute(
                    select(CostCenter.id).where(
                        CostCenter.workspace_id == workspace_id,
                        CostCenter.id.in_([uuid.UUID(str(i)) for i in ids]),
                    )
                )
            ).scalars()
        }
        missing = {str(i) for i in ids} - found
        if missing:
            raise ValueError(
                "Cost center not found in this workspace: " + ", ".join(sorted(missing))
            )
    if formula_type == "fixed_weight":
        weights = [a.get("weight") for a in allocations]
        if any(w is None or Decimal(str(w)) < 0 for w in weights):
            raise ValueError("fixed_weight allocations need a non-negative weight each")
        total = sum((Decimal(str(w)) for w in weights), Decimal(0))
        if abs(total - Decimal(1)) > Decimal("0.0001"):
            raise ValueError(f"fixed_weight weights must sum to 1 (got {total})")
    if formula_type == "proportional":
        denoms = [a.get("denominator_value") for a in allocations]
        if any(d is None or Decimal(str(d)) < 0 for d in denoms):
            raise ValueError("proportional allocations need a non-negative denominator_value each")
        if sum((Decimal(str(d)) for d in denoms), Decimal(0)) <= 0:
            raise ValueError("proportional denominators must not all be zero")


async def compute_shared_cost_allocation(
    db: AsyncSession, policy_id: uuid.UUID, pool_usd: Decimal
) -> dict[str, Any]:
    """Split ``pool_usd`` by the policy's formula. Shares are rounded to 6 places and
    the rounding remainder goes to the last target, so they always sum to the pool."""
    from runledger_api.schemas.billing import SharedCostAllocationResult  # noqa: PLC0415

    policy = (
        await db.execute(select(SharedCostPolicy).where(SharedCostPolicy.id == policy_id))
    ).scalar_one_or_none()
    if policy is None:
        raise ValueError(f"SharedCostPolicy {policy_id} not found")
    allocations: list[dict[str, Any]] = policy.allocations or []
    computed: list[dict[str, Any]] = []
    n = len(allocations)
    if n:
        if policy.formula_type == "equal_split":
            shares = [Decimal(1) / n] * n
        elif policy.formula_type == "fixed_weight":
            shares = [Decimal(str(a.get("weight") or 0)) for a in allocations]
        else:
            denoms = [Decimal(str(a.get("denominator_value") or 0)) for a in allocations]
            total = sum(denoms, Decimal(0))
            shares = [d / total if total > 0 else Decimal(0) for d in denoms]
        amounts = [(pool_usd * s).quantize(_Q6) for s in shares]
        if sum(shares, Decimal(0)) > 0:
            amounts[-1] += pool_usd - sum(amounts, Decimal(0))
        for alloc, amount in zip(allocations, amounts, strict=True):
            computed.append(
                {
                    "label": alloc.get("label", ""),
                    "cost_center_id": alloc.get("cost_center_id"),
                    "allocated_usd": amount,
                }
            )
    return SharedCostAllocationResult(
        policy_id=policy.id,
        policy_name=policy.name,
        pool_usd=pool_usd,
        formula_type=policy.formula_type,
        allocations=computed,
    ).model_dump()


async def apply_shared_cost_policy(
    db: AsyncSession,
    policy: SharedCostPolicy,
    period: str,
    pool_usd: Decimal,
    created_by: str | None,
) -> list[CostAllocation]:
    """Persist a policy's split of ``pool_usd`` for a month, replacing any earlier
    application of the same policy to that month."""
    period_label, _, _ = _chargeback_period_bounds(period)
    result = await compute_shared_cost_allocation(db, policy.id, pool_usd)
    await db.execute(
        sa.delete(CostAllocation).where(
            CostAllocation.workspace_id == policy.workspace_id,
            CostAllocation.policy_id == policy.id,
            CostAllocation.period == period_label,
        )
    )
    rows = []
    for a in result["allocations"]:
        cc = a.get("cost_center_id")
        row = CostAllocation(
            workspace_id=policy.workspace_id,
            period=period_label,
            policy_id=policy.id,
            cost_center_id=uuid.UUID(str(cc)) if cc else None,
            label=a.get("label") or "",
            pool_usd=pool_usd,
            amount_usd=a["allocated_usd"],
            created_by=created_by,
        )
        db.add(row)
        rows.append(row)
    await db.flush()
    return rows
