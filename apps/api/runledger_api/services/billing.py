"""
Billing service layer — period management, reconciliation, signing, export.

All functions are pure async with no FastAPI dependencies so they can be
imported directly from Celery workers.
"""

from __future__ import annotations

import csv
import hashlib
import hmac
import io
import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import func, literal_column, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.config import settings
from runledger_api.models.billing import (
    BillingAdjustment,
    BillingPeriod,
    ChargebackRule,
    CostCenter,
    SharedCostPolicy,
    UsageSnapshot,
)
from runledger_api.models.events import AgentRun, ProviderCall
from runledger_api.models.metering import UsageDaily
from runledger_api.schemas.billing import (
    BillingAdjustmentResponse,
    BreakdownApp,
    BreakdownUser,
    CostCenterNode,
    PeriodBreakdown,
    ReconciliationResult,
)

log = structlog.get_logger()


# ── HMAC signing ──────────────────────────────────────────────────────────────


def sign_snapshot(data: dict[str, Any], key: str) -> str:
    """HMAC-SHA256 of canonical JSON (sort_keys=True). Returns hex string."""
    body = json.dumps(data, sort_keys=True, default=str).encode()
    return hmac.new(key.encode(), body, hashlib.sha256).hexdigest()


# ── Period cost ───────────────────────────────────────────────────────────────


async def get_period_total_cost(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    period_start: Any,
    period_end: Any,
) -> Decimal:
    """SUM(provider_calls.cost_usd) for the date range."""
    result = await db.execute(
        select(func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0))).where(
            ProviderCall.workspace_id == workspace_id,
            func.date(ProviderCall.created_at) >= period_start,
            func.date(ProviderCall.created_at) <= period_end,
            ProviderCall.cost_usd.is_not(None),
        )
    )
    return result.scalar_one() or Decimal(0)


# ── Reconciliation ────────────────────────────────────────────────────────────


async def run_reconciliation(
    db: AsyncSession,
    billing_period_id: uuid.UUID,
) -> ReconciliationResult:
    """
    Cross-check provider_calls vs usage_daily for consistency.

    1. Fetch period dates + workspace_id
    2. Sum provider_calls.cost_usd (source of truth)
    3. Sum usage_daily.cost_usd for same date range
    4. delta_pct = abs(calls_sum - daily_sum) / calls_sum * 100
    5. Count orphaned calls (no matching agent_run)
    6. Count duplicate calls (same run_id, model, second-truncated timestamp)
    """
    period_result = await db.execute(
        select(BillingPeriod).where(BillingPeriod.id == billing_period_id)
    )
    period = period_result.scalar_one_or_none()
    if period is None:
        raise ValueError(f"BillingPeriod {billing_period_id} not found")

    workspace_id = period.workspace_id
    period_start = period.period_start
    period_end = period.period_end

    # Sum from provider_calls
    calls_result = await db.execute(
        select(func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0))).where(
            ProviderCall.workspace_id == workspace_id,
            func.date(ProviderCall.created_at) >= period_start,
            func.date(ProviderCall.created_at) <= period_end,
            ProviderCall.cost_usd.is_not(None),
        )
    )
    calls_sum: Decimal = calls_result.scalar_one() or Decimal(0)

    # Sum from usage_daily
    daily_result = await db.execute(
        select(func.coalesce(func.sum(UsageDaily.cost_usd), Decimal(0))).where(
            UsageDaily.workspace_id == workspace_id,
            UsageDaily.day >= period_start,
            UsageDaily.day <= period_end,
        )
    )
    daily_sum: Decimal = daily_result.scalar_one() or Decimal(0)

    # Delta percentage
    delta_pct = abs(calls_sum - daily_sum) / calls_sum * 100 if calls_sum > 0 else Decimal(0)

    # Count orphaned calls (LEFT JOIN agent_runs WHERE agent_runs.id IS NULL)
    orphan_result = await db.execute(
        select(func.count(ProviderCall.id))
        .outerjoin(AgentRun, ProviderCall.run_id == AgentRun.id)
        .where(
            ProviderCall.workspace_id == workspace_id,
            func.date(ProviderCall.created_at) >= period_start,
            func.date(ProviderCall.created_at) <= period_end,
            AgentRun.id.is_(None),
        )
    )
    orphaned_calls: int = orphan_result.scalar_one() or 0

    # Count duplicates: same (run_id, model, date_trunc('second', created_at))
    # Use literal_column for 'second' so both SELECT and GROUP BY emit the same
    # inline literal — bound parameters at different positions confuse PostgreSQL.
    ts_trunc = func.date_trunc(literal_column("'second'"), ProviderCall.created_at)
    dup_subq = (
        select(
            ProviderCall.run_id,
            ProviderCall.model,
            ts_trunc.label("ts_second"),
            func.count().label("cnt"),
        )
        .where(
            ProviderCall.workspace_id == workspace_id,
            func.date(ProviderCall.created_at) >= period_start,
            func.date(ProviderCall.created_at) <= period_end,
        )
        .group_by(
            ProviderCall.run_id,
            ProviderCall.model,
            ts_trunc,
        )
        .having(func.count() > 1)
        .subquery()
    )
    dup_result = await db.execute(select(func.count()).select_from(dup_subq))
    duplicate_calls: int = dup_result.scalar_one() or 0

    issues: list[str] = []
    warnings: list[str] = []
    recon_status = "pass"

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
        # Duplicates are a data-quality warning, not a billing failure — the
        # pipeline now uses deterministic IDs so new ingestion won't produce
        # duplicates; existing ones are pre-fix legacy rows.
        warnings.append(
            f"{duplicate_calls} duplicate provider_call group(s) detected (data quality warning)"
        )
        if recon_status == "pass":
            recon_status = "warning"

    log.info(
        "reconciliation_complete",
        period_id=str(billing_period_id),
        status=recon_status,
        calls_sum=str(calls_sum),
        daily_sum=str(daily_sum),
        delta_pct=str(delta_pct),
        orphaned=orphaned_calls,
        duplicates=duplicate_calls,
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


# ── Close billing period ──────────────────────────────────────────────────────


async def close_billing_period(
    db: AsyncSession,
    billing_period_id: uuid.UUID,
) -> UsageSnapshot:
    """
    Close a billing period, compute final cost, build + sign a usage snapshot.

    1. Check status != 'closed' → raise ValueError if already closed
    2. SET status='closing'
    3. Compute total from provider_calls
    4. Build snapshot_data with by_model breakdown
    5. Sign and create UsageSnapshot
    6. Update BillingPeriod: status='closed', closed_at=now()
    7. Commit + return snapshot
    """
    period_result = await db.execute(
        select(BillingPeriod).where(BillingPeriod.id == billing_period_id)
    )
    period = period_result.scalar_one_or_none()
    if period is None:
        raise ValueError(f"BillingPeriod {billing_period_id} not found")
    if period.status == "closed":
        raise ValueError("already_closed")

    # Mark as closing
    await db.execute(
        update(BillingPeriod).where(BillingPeriod.id == billing_period_id).values(status="closing")
    )

    workspace_id = period.workspace_id
    period_start = period.period_start
    period_end = period.period_end

    # Total cost
    total_cost = await get_period_total_cost(db, workspace_id, period_start, period_end)

    # By-model breakdown
    model_rows_result = await db.execute(
        select(
            ProviderCall.model,
            ProviderCall.provider,
            func.coalesce(func.sum(ProviderCall.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(ProviderCall.output_tokens), 0).label("output_tokens"),
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost_usd"),
            func.count(ProviderCall.id).label("call_count"),
        )
        .where(
            ProviderCall.workspace_id == workspace_id,
            func.date(ProviderCall.created_at) >= period_start,
            func.date(ProviderCall.created_at) <= period_end,
        )
        .group_by(ProviderCall.model, ProviderCall.provider)
    )
    model_rows = model_rows_result.all()

    # Sum adjustments (credits/refunds reduce cost; surcharges add to it)
    adj_result = await db.execute(
        select(
            BillingAdjustment.adjustment_type,
            func.coalesce(func.sum(BillingAdjustment.amount_usd), Decimal(0)).label("total_amount"),
        )
        .where(BillingAdjustment.billing_period_id == billing_period_id)
        .group_by(BillingAdjustment.adjustment_type)
    )
    adj_rows = adj_result.all()

    total_deductions = Decimal(0)
    total_surcharges = Decimal(0)
    for adj_row in adj_rows:
        if adj_row.adjustment_type in ("credit", "refund", "prepaid_deduction"):
            total_deductions += adj_row.total_amount
        else:
            total_surcharges += adj_row.total_amount
    net_cost = max(total_cost - total_deductions + total_surcharges, Decimal(0))

    now = datetime.now(UTC)
    snapshot_data: dict[str, Any] = {
        "period_id": str(billing_period_id),
        "workspace_id": str(workspace_id),
        "period_start": str(period_start),
        "period_end": str(period_end),
        "total_cost_usd": str(total_cost),
        "net_cost_usd": str(net_cost),
        "total_deductions_usd": str(total_deductions),
        "total_surcharges_usd": str(total_surcharges),
        "currency": period.currency,
        "exchange_rate_to_usd": str(period.exchange_rate_to_usd),
        "closed_at": now.isoformat(),
        "by_model": [
            {
                "model": row.model,
                "provider": row.provider,
                "input_tokens": row.input_tokens,
                "output_tokens": row.output_tokens,
                "cost_usd": str(row.cost_usd),
                "call_count": row.call_count,
            }
            for row in model_rows
        ],
    }

    sig = sign_snapshot(snapshot_data, settings.secret_key)

    snapshot = UsageSnapshot(
        billing_period_id=billing_period_id,
        snapshot_data=snapshot_data,
        signature=sig,
        signing_key_id="v1",
    )
    db.add(snapshot)
    await db.flush()  # get snapshot.id + created_at

    # Close the period
    await db.execute(
        update(BillingPeriod)
        .where(BillingPeriod.id == billing_period_id)
        .values(
            status="closed",
            total_cost_usd=total_cost,
            net_cost_usd=net_cost,
            snapshot_hash=sig[:16],
            closed_at=now,
        )
    )
    await db.commit()
    await db.refresh(snapshot)

    log.info(
        "billing_period_closed",
        period_id=str(billing_period_id),
        total_cost_usd=str(total_cost),
        snapshot_id=str(snapshot.id),
    )

    return snapshot


# ── Breakdown ─────────────────────────────────────────────────────────────────


async def get_period_breakdown(
    db: AsyncSession,
    billing_period_id: uuid.UUID,
) -> PeriodBreakdown:
    """
    GROUP BY application_id, end_user_id from provider_calls JOIN agent_runs.
    Build nested BreakdownApp → BreakdownUser structure.
    """
    period_result = await db.execute(
        select(BillingPeriod).where(BillingPeriod.id == billing_period_id)
    )
    period = period_result.scalar_one_or_none()
    if period is None:
        raise ValueError(f"BillingPeriod {billing_period_id} not found")

    workspace_id = period.workspace_id
    period_start = period.period_start
    period_end = period.period_end

    rows_result = await db.execute(
        select(
            AgentRun.application_id,
            ProviderCall.end_user_id,
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost_usd"),
            func.count(func.distinct(AgentRun.id)).label("run_count"),
        )
        .join(AgentRun, ProviderCall.run_id == AgentRun.id)
        .where(
            ProviderCall.workspace_id == workspace_id,
            func.date(ProviderCall.created_at) >= period_start,
            func.date(ProviderCall.created_at) <= period_end,
        )
        .group_by(AgentRun.application_id, ProviderCall.end_user_id)
    )
    rows = rows_result.all()

    # Group into app → users
    apps: dict[str | None, dict[str, Any]] = {}
    total_cost = Decimal(0)

    for row in rows:
        app_key = str(row.application_id) if row.application_id else None
        if app_key not in apps:
            apps[app_key] = {"cost_usd": Decimal(0), "users": []}
        user_cost = row.cost_usd or Decimal(0)
        apps[app_key]["cost_usd"] += user_cost
        total_cost += user_cost
        apps[app_key]["users"].append(
            BreakdownUser(
                end_user_id=row.end_user_id,
                cost_usd=user_cost,
                run_count=row.run_count,
            )
        )

    by_application = [
        BreakdownApp(
            application_id=app_id,
            cost_usd=app_data["cost_usd"],
            users=app_data["users"],
        )
        for app_id, app_data in apps.items()
    ]

    # Fetch adjustments for this period
    adj_list_result = await db.execute(
        select(BillingAdjustment)
        .where(BillingAdjustment.billing_period_id == billing_period_id)
        .order_by(BillingAdjustment.created_at)
    )
    adj_items = list(adj_list_result.scalars())
    adj_responses = [BillingAdjustmentResponse.model_validate(a) for a in adj_items]

    _credit_types = ("credit", "refund", "prepaid_deduction")
    total_deductions = sum(
        (a.amount_usd for a in adj_items if a.adjustment_type in _credit_types),
        Decimal(0),
    )
    total_surcharges = sum(
        (a.amount_usd for a in adj_items if a.adjustment_type == "surcharge"),
        Decimal(0),
    )
    total_adjustments = total_surcharges - total_deductions
    net_cost = max(total_cost + total_adjustments, Decimal(0))

    return PeriodBreakdown(
        period_id=str(billing_period_id),
        gross_cost_usd=total_cost,
        net_cost_usd=net_cost,
        total_adjustments_usd=total_adjustments,
        by_application=by_application,
        adjustments=adj_responses,
    )


# ── Export CSV ────────────────────────────────────────────────────────────────


async def export_csv(db: AsyncSession, billing_period_id: uuid.UUID) -> str:
    """
    Columns: date, end_user_id, model, input_tokens, output_tokens, cost_usd, run_id
    Query provider_calls LEFT JOIN agent_runs for the period date range.
    """
    period_result = await db.execute(
        select(BillingPeriod).where(BillingPeriod.id == billing_period_id)
    )
    period = period_result.scalar_one_or_none()
    if period is None:
        raise ValueError(f"BillingPeriod {billing_period_id} not found")

    rows_result = await db.execute(
        select(
            func.date(ProviderCall.created_at).label("date"),
            ProviderCall.end_user_id,
            ProviderCall.model,
            ProviderCall.input_tokens,
            ProviderCall.output_tokens,
            ProviderCall.cost_usd,
            ProviderCall.run_id,
        )
        .where(
            ProviderCall.workspace_id == period.workspace_id,
            func.date(ProviderCall.created_at) >= period.period_start,
            func.date(ProviderCall.created_at) <= period.period_end,
        )
        .order_by(func.date(ProviderCall.created_at), ProviderCall.end_user_id)
    )
    rows = rows_result.all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["date", "end_user_id", "model", "input_tokens", "output_tokens", "cost_usd", "run_id"]
    )
    for row in rows:
        writer.writerow(
            [
                row.date,
                row.end_user_id or "",
                row.model,
                row.input_tokens or 0,
                row.output_tokens or 0,
                str(row.cost_usd) if row.cost_usd is not None else "",
                str(row.run_id),
            ]
        )

    return buf.getvalue()


# ── Export signed JSON ────────────────────────────────────────────────────────


async def export_signed_json(
    db: AsyncSession,
    billing_period_id: uuid.UUID,
) -> dict[str, Any]:
    """
    Build a signed JSON export with all provider_call rows.
    Signature covers the full payload (rows included).
    """
    period_result = await db.execute(
        select(BillingPeriod).where(BillingPeriod.id == billing_period_id)
    )
    period = period_result.scalar_one_or_none()
    if period is None:
        raise ValueError(f"BillingPeriod {billing_period_id} not found")

    rows_result = await db.execute(
        select(
            func.date(ProviderCall.created_at).label("date"),
            ProviderCall.end_user_id,
            ProviderCall.model,
            ProviderCall.provider,
            ProviderCall.input_tokens,
            ProviderCall.output_tokens,
            ProviderCall.cost_usd,
            ProviderCall.run_id,
        )
        .where(
            ProviderCall.workspace_id == period.workspace_id,
            func.date(ProviderCall.created_at) >= period.period_start,
            func.date(ProviderCall.created_at) <= period.period_end,
        )
        .order_by(func.date(ProviderCall.created_at))
    )
    rows = rows_result.all()

    total_cost = sum(
        (row.cost_usd or Decimal(0) for row in rows),
        Decimal(0),
    )

    payload: dict[str, Any] = {
        "period_id": str(billing_period_id),
        "period_start": str(period.period_start),
        "period_end": str(period.period_end),
        "total_cost_usd": str(total_cost),
        "rows": [
            {
                "date": str(row.date),
                "end_user_id": row.end_user_id,
                "model": row.model,
                "provider": row.provider,
                "input_tokens": row.input_tokens,
                "output_tokens": row.output_tokens,
                "cost_usd": str(row.cost_usd) if row.cost_usd is not None else None,
                "run_id": str(row.run_id),
            }
            for row in rows
        ],
        "signing_key_id": "v1",
    }

    sig = sign_snapshot(payload, settings.secret_key)
    payload["signature"] = sig

    return payload


# ── Chargeback rules ──────────────────────────────────────────────────────────


async def apply_chargeback_rules(
    db: AsyncSession,
    billing_period_id: uuid.UUID,
) -> dict[str, Decimal]:
    """
    Fetch chargeback_rules for workspace. Multiply net period cost by each weight.
    Returns {dimension: allocated_cost_usd} mapping.
    Uses net_cost_usd (after adjustments) when available; falls back to total_cost_usd.
    """
    period_result = await db.execute(
        select(BillingPeriod).where(BillingPeriod.id == billing_period_id)
    )
    period = period_result.scalar_one_or_none()
    if period is None:
        raise ValueError(f"BillingPeriod {billing_period_id} not found")

    base_cost = period.net_cost_usd or period.total_cost_usd or Decimal(0)

    rules_result = await db.execute(
        select(ChargebackRule).where(
            ChargebackRule.workspace_id == period.workspace_id,
            ChargebackRule.status == "active",
        )
    )
    rules: list[ChargebackRule] = list(rules_result.scalars())

    return {rule.dimension: base_cost * rule.weight for rule in rules}


# ── Cost Centers ──────────────────────────────────────────────────────────────


async def get_cost_center_tree(
    db: AsyncSession,
    workspace_id: uuid.UUID,
) -> list[CostCenterNode]:
    """
    Return the cost center hierarchy as a forest of CostCenterNode trees.
    Builds the tree in Python from a flat SELECT (avoids recursive CTE complexity).
    """
    result = await db.execute(
        select(CostCenter).where(CostCenter.workspace_id == workspace_id).order_by(CostCenter.name)
    )
    all_centers = list(result.scalars())

    nodes: dict[uuid.UUID, CostCenterNode] = {
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
        node = nodes[c.id]
        if c.parent_id and c.parent_id in nodes:
            nodes[c.parent_id].children.append(node)
        else:
            roots.append(node)

    return roots


# ── Billing Adjustments ───────────────────────────────────────────────────────


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
    """Create a billing adjustment on an open (or closing) period."""
    period_result = await db.execute(
        select(BillingPeriod).where(
            BillingPeriod.id == billing_period_id,
            BillingPeriod.workspace_id == workspace_id,
        )
    )
    period = period_result.scalar_one_or_none()
    if period is None:
        raise ValueError("BillingPeriod not found")
    if period.status == "closed":
        raise ValueError("Cannot add adjustments to a closed billing period")

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
    await db.commit()
    await db.refresh(adj)
    log.info(
        "billing_adjustment_added",
        period_id=str(billing_period_id),
        adjustment_type=adjustment_type,
        amount_usd=str(amount_usd),
    )
    return adj


async def get_period_adjustments(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    billing_period_id: uuid.UUID,
) -> list[BillingAdjustment]:
    """List all adjustments for a period."""
    result = await db.execute(
        select(BillingAdjustment)
        .where(
            BillingAdjustment.billing_period_id == billing_period_id,
            BillingAdjustment.workspace_id == workspace_id,
        )
        .order_by(BillingAdjustment.created_at)
    )
    return list(result.scalars())


# ── Shared-cost policies ───────────────────────────────────────────────────────


async def compute_shared_cost_allocation(
    db: AsyncSession,
    policy_id: uuid.UUID,
    pool_usd: Decimal,
) -> dict[str, Any]:
    """
    Distribute pool_usd across cost centers according to policy formula.

    Returns dict with keys: policy_id, policy_name, pool_usd, formula_type,
    allocations: [{label, cost_center_id, allocated_usd}]

    formula_type:
      equal_split   — pool / N for each allocation
      fixed_weight  — pool * allocation["weight"]
      proportional  — pool * allocation["denominator_value"] / sum(denominator_values)
    """
    from runledger_api.schemas.billing import SharedCostAllocationResult  # noqa: PLC0415

    result = await db.execute(select(SharedCostPolicy).where(SharedCostPolicy.id == policy_id))
    policy = result.scalar_one_or_none()
    if policy is None:
        raise ValueError(f"SharedCostPolicy {policy_id} not found")

    allocations: list[dict[str, Any]] = policy.allocations or []
    n = len(allocations)
    formula = policy.formula_type
    computed: list[dict[str, Any]] = []

    if n == 0:
        return SharedCostAllocationResult(
            policy_id=policy.id,
            policy_name=policy.name,
            pool_usd=pool_usd,
            formula_type=formula,
            allocations=[],
        ).model_dump()

    if formula == "equal_split":
        share = (pool_usd / n).quantize(Decimal("0.000001"))
        for alloc in allocations:
            computed.append(
                {
                    "label": alloc.get("label", ""),
                    "cost_center_id": alloc.get("cost_center_id"),
                    "allocated_usd": share,
                }
            )

    elif formula == "fixed_weight":
        for alloc in allocations:
            w = Decimal(str(alloc.get("weight", 0)))
            computed.append(
                {
                    "label": alloc.get("label", ""),
                    "cost_center_id": alloc.get("cost_center_id"),
                    "allocated_usd": (pool_usd * w).quantize(Decimal("0.000001")),
                }
            )

    elif formula == "proportional":
        total_denom = sum(Decimal(str(a.get("denominator_value") or 0)) for a in allocations)
        for alloc in allocations:
            denom = Decimal(str(alloc.get("denominator_value") or 0))
            share = (
                (pool_usd * denom / total_denom).quantize(Decimal("0.000001"))
                if total_denom > 0
                else Decimal(0)
            )
            computed.append(
                {
                    "label": alloc.get("label", ""),
                    "cost_center_id": alloc.get("cost_center_id"),
                    "allocated_usd": share,
                }
            )

    return SharedCostAllocationResult(
        policy_id=policy.id,
        policy_name=policy.name,
        pool_usd=pool_usd,
        formula_type=formula,
        allocations=computed,
    ).model_dump()
