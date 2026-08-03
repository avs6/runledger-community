"""
Billing CRUD + export endpoints.

Prefix: /billing
Auth: Bearer API key (workspace-scoped)

Endpoints
---------
POST   /billing/periods                          Create a billing period
GET    /billing/periods                          List periods (optional ?status=)
GET    /billing/periods/{id}                     Single period
POST   /billing/periods/{id}/close               Close + sign snapshot
GET    /billing/periods/{id}/breakdown           Hierarchical breakdown by app/user
GET    /billing/periods/{id}/export              Export CSV / signed JSON
POST   /billing/periods/{id}/adjustments         Add a credit/refund/surcharge line
GET    /billing/periods/{id}/adjustments         List adjustments for a period
DELETE /billing/periods/{id}/adjustments/{adj}   Remove an adjustment
POST   /billing/shared-cost-policies             Create a shared-cost policy
GET    /billing/shared-cost-policies             List shared-cost policies
GET    /billing/shared-cost-policies/{id}        Get a shared-cost policy
PUT    /billing/shared-cost-policies/{id}        Update a shared-cost policy
DELETE /billing/shared-cost-policies/{id}        Delete a shared-cost policy
POST   /billing/shared-cost-policies/{id}/allocate  Compute cost allocation for a pool
"""

from __future__ import annotations

import asyncio as _asyncio
import uuid
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import (
    require_org_admin,
    require_workspace_admin,
)
from runledger_api.core.ratelimit import management_rate_limit
from runledger_api.models.billing import (
    BillingAdjustment,
    BillingPeriod,
    ChargebackRule,
    SharedCostPolicy,
)
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.billing import (
    BillingAdjustmentCreate,
    BillingAdjustmentList,
    BillingAdjustmentResponse,
    BillingPeriodCreate,
    BillingPeriodList,
    BillingPeriodResponse,
    ChargebackRuleCreate,
    ChargebackRuleList,
    ChargebackRuleResponse,
    PeriodBreakdown,
    SharedCostAllocationResult,
    SharedCostPolicyCreate,
    SharedCostPolicyList,
    SharedCostPolicyResponse,
    SharedCostPolicyUpdate,
    UsageSnapshotResponse,
)
from runledger_api.services.billing import (
    add_adjustment,
    close_billing_period,
    compute_shared_cost_allocation,
    export_csv,
    export_signed_json,
    get_period_adjustments,
    get_period_breakdown,
)
from runledger_api.services.email import send_billing_period_closed_email
from runledger_api.services.email_utils import get_email_preference, get_workspace_admin_users

router = APIRouter(
    prefix="/billing", tags=["billing"], dependencies=[Depends(management_rate_limit)]
)
log = structlog.get_logger()


# ── POST /billing/periods ─────────────────────────────────────────────────────


@router.post(
    "/periods",
    response_model=BillingPeriodResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_billing_period(
    body: BillingPeriodCreate,
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BillingPeriodResponse:
    workspace: Workspace = auth[0]
    """Create a new billing period for this workspace."""
    period = BillingPeriod(
        workspace_id=workspace.id,
        period_start=body.period_start,
        period_end=body.period_end,
        status="open",
        currency=body.currency,
        exchange_rate_to_usd=body.exchange_rate_to_usd,
    )
    db.add(period)
    await db.commit()
    await db.refresh(period)

    log.info(
        "billing_period_created",
        period_id=str(period.id),
        workspace_id=str(workspace.id),
        period_start=str(period.period_start),
        period_end=str(period.period_end),
        currency=period.currency,
    )

    return BillingPeriodResponse.model_validate(period)


# ── GET /billing/periods ──────────────────────────────────────────────────────


@router.get("/periods", response_model=BillingPeriodList)
async def list_billing_periods(
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> BillingPeriodList:
    workspace: Workspace = auth[0]
    """List billing periods, optionally filtered by status."""
    stmt = select(BillingPeriod).where(BillingPeriod.workspace_id == workspace.id)
    if status_filter:
        stmt = stmt.where(BillingPeriod.status == status_filter)
    stmt = stmt.order_by(BillingPeriod.period_start.desc())

    result = await db.execute(stmt)
    periods: list[BillingPeriod] = list(result.scalars())

    return BillingPeriodList(items=[BillingPeriodResponse.model_validate(p) for p in periods])


# ── GET /billing/periods/{id} ─────────────────────────────────────────────────


@router.get("/periods/{period_id}", response_model=BillingPeriodResponse)
async def get_billing_period(
    period_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BillingPeriodResponse:
    workspace: Workspace = auth[0]
    """Get a single billing period by ID."""
    result = await db.execute(
        select(BillingPeriod).where(
            BillingPeriod.id == period_id,
            BillingPeriod.workspace_id == workspace.id,
        )
    )
    period = result.scalar_one_or_none()
    if period is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Billing period not found"
        )

    return BillingPeriodResponse.model_validate(period)


# ── POST /billing/periods/{id}/close ─────────────────────────────────────────


@router.post("/periods/{period_id}/close", response_model=UsageSnapshotResponse)
async def close_period(
    period_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UsageSnapshotResponse:
    workspace: Workspace = auth[0]
    """Close a billing period and produce a signed usage snapshot."""
    # Verify ownership
    result = await db.execute(
        select(BillingPeriod).where(
            BillingPeriod.id == period_id,
            BillingPeriod.workspace_id == workspace.id,
        )
    )
    period = result.scalar_one_or_none()
    if period is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Billing period not found"
        )

    try:
        snapshot = await close_billing_period(db, period_id)
    except ValueError as exc:
        if "already_closed" in str(exc):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Billing period is already closed",
            ) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    # Fire-and-forget: email workspace admins about closed period
    async def _notify_billing_closed() -> None:
        try:
            prefs = await get_email_preference(db, workspace.id)
            if prefs is not None and not prefs.billing_closed_enabled:
                return
            admins = await get_workspace_admin_users(db, workspace.id)
            total_cost = str(period.total_cost_usd) if period.total_cost_usd is not None else "N/A"
            snap_hash = snapshot.signature[:16] if snapshot.signature else ""
            await _asyncio.gather(
                *[
                    send_billing_period_closed_email(
                        to_email=u.email,
                        full_name=u.full_name,
                        period_start=str(period.period_start),
                        period_end=str(period.period_end),
                        total_cost_usd=total_cost,
                        snapshot_hash=snap_hash,
                        workspace_name=workspace.name,
                    )
                    for u in admins
                ],
                return_exceptions=True,
            )
        except Exception:
            pass  # never break the response

    _asyncio.create_task(_notify_billing_closed())

    return UsageSnapshotResponse(
        id=str(snapshot.id),
        billing_period_id=str(snapshot.billing_period_id),
        signature=snapshot.signature,
        signing_key_id=snapshot.signing_key_id,
        created_at=snapshot.created_at,
    )


# ── GET /billing/periods/{id}/breakdown ───────────────────────────────────────


@router.get("/periods/{period_id}/breakdown", response_model=PeriodBreakdown)
async def get_breakdown(
    period_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PeriodBreakdown:
    workspace: Workspace = auth[0]
    """Get hierarchical cost breakdown by application → user."""
    result = await db.execute(
        select(BillingPeriod).where(
            BillingPeriod.id == period_id,
            BillingPeriod.workspace_id == workspace.id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Billing period not found"
        )

    try:
        return await get_period_breakdown(db, period_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# ── GET /billing/periods/{id}/export ──────────────────────────────────────────


@router.get("/periods/{period_id}/export")
async def export_period(
    period_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    format: Annotated[str, Query(pattern="^(csv|signed_json)$")] = "csv",
) -> Response:
    workspace: Workspace = auth[0]
    """Export billing period data — csv or signed_json."""
    result = await db.execute(
        select(BillingPeriod).where(
            BillingPeriod.id == period_id,
            BillingPeriod.workspace_id == workspace.id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Billing period not found"
        )

    try:
        if format == "csv":
            csv_content = await export_csv(db, period_id)
            return Response(
                content=csv_content,
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=period_{period_id}.csv"},
            )
        else:
            import json  # noqa: PLC0415

            payload = await export_signed_json(db, period_id)
            return Response(
                content=json.dumps(payload, default=str),
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename=period_{period_id}.json"},
            )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# ── Billing Adjustments ───────────────────────────────────────────────────────


@router.post(
    "/periods/{period_id}/adjustments",
    response_model=BillingAdjustmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_adjustment(
    period_id: uuid.UUID,
    body: BillingAdjustmentCreate,
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BillingAdjustmentResponse:
    workspace: Workspace = auth[0]
    """Add a credit, refund, prepaid deduction, or surcharge to a billing period."""
    try:
        adj = await add_adjustment(
            db,
            workspace_id=workspace.id,
            billing_period_id=period_id,
            adjustment_type=body.adjustment_type,
            amount_usd=body.amount_usd,
            description=body.description,
            reference_id=body.reference_id,
            created_by=str(workspace.id),
        )
    except ValueError as exc:
        if "not found" in str(exc).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return BillingAdjustmentResponse.model_validate(adj)


@router.get("/periods/{period_id}/adjustments", response_model=BillingAdjustmentList)
async def list_adjustments(
    period_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BillingAdjustmentList:
    workspace: Workspace = auth[0]
    """List all billing adjustments for a period."""
    # Verify ownership
    result = await db.execute(
        select(BillingPeriod).where(
            BillingPeriod.id == period_id,
            BillingPeriod.workspace_id == workspace.id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Billing period not found"
        )

    from decimal import Decimal as _Decimal  # noqa: PLC0415

    _credit_types = ("credit", "refund", "prepaid_deduction")
    items = await get_period_adjustments(db, workspace.id, period_id)
    resp_items = [BillingAdjustmentResponse.model_validate(a) for a in items]

    total_credits = sum(
        (a.amount_usd for a in items if a.adjustment_type in _credit_types),
        _Decimal(0),
    )
    total_surcharges = sum(
        (a.amount_usd for a in items if a.adjustment_type == "surcharge"),
        _Decimal(0),
    )
    net_adj = total_surcharges - total_credits

    return BillingAdjustmentList(
        items=resp_items,
        total_credits_usd=total_credits,
        total_surcharges_usd=total_surcharges,
        net_adjustment_usd=net_adj,
    )


@router.delete(
    "/periods/{period_id}/adjustments/{adjustment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_adjustment(
    period_id: uuid.UUID,
    adjustment_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    workspace: Workspace = auth[0]
    result = await db.execute(
        select(BillingAdjustment).where(
            BillingAdjustment.id == adjustment_id,
            BillingAdjustment.billing_period_id == period_id,
            BillingAdjustment.workspace_id == workspace.id,
        )
    )
    adj = result.scalar_one_or_none()
    if adj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Adjustment not found")
    await db.delete(adj)
    await db.commit()


# ── Shared-cost policies ───────────────────────────────────────────────────────


@router.post(
    "/shared-cost-policies",
    response_model=SharedCostPolicyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_shared_cost_policy(
    body: SharedCostPolicyCreate,
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SharedCostPolicyResponse:
    workspace: Workspace = auth[0]
    _id = uuid.uuid4()
    policy = SharedCostPolicy(
        id=_id,
        workspace_id=workspace.id,
        name=body.name,
        description=body.description,
        formula_type=body.formula_type,
        allocations=[a.model_dump(mode="json") for a in body.allocations],
        is_active=body.is_active,
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    log.info(
        "shared_cost_policy_created",
        policy_id=str(policy.id),
        workspace_id=str(workspace.id),
        formula_type=policy.formula_type,
    )
    return SharedCostPolicyResponse.model_validate(policy)


@router.get("/shared-cost-policies", response_model=SharedCostPolicyList)
async def list_shared_cost_policies(
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    active_only: Annotated[bool, Query()] = False,
) -> SharedCostPolicyList:
    workspace: Workspace = auth[0]
    stmt = select(SharedCostPolicy).where(SharedCostPolicy.workspace_id == workspace.id)
    if active_only:
        stmt = stmt.where(SharedCostPolicy.is_active.is_(True))
    stmt = stmt.order_by(SharedCostPolicy.created_at.desc())
    result = await db.execute(stmt)
    policies = list(result.scalars().all())
    return SharedCostPolicyList(
        items=[SharedCostPolicyResponse.model_validate(p) for p in policies],
        total=len(policies),
    )


@router.get("/shared-cost-policies/{policy_id}", response_model=SharedCostPolicyResponse)
async def get_shared_cost_policy(
    policy_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SharedCostPolicyResponse:
    workspace: Workspace = auth[0]
    result = await db.execute(
        select(SharedCostPolicy).where(
            SharedCostPolicy.id == policy_id,
            SharedCostPolicy.workspace_id == workspace.id,
        )
    )
    policy = result.scalar_one_or_none()
    if policy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    return SharedCostPolicyResponse.model_validate(policy)


@router.put("/shared-cost-policies/{policy_id}", response_model=SharedCostPolicyResponse)
async def update_shared_cost_policy(
    policy_id: uuid.UUID,
    body: SharedCostPolicyUpdate,
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SharedCostPolicyResponse:
    workspace: Workspace = auth[0]
    result = await db.execute(
        select(SharedCostPolicy).where(
            SharedCostPolicy.id == policy_id,
            SharedCostPolicy.workspace_id == workspace.id,
        )
    )
    policy = result.scalar_one_or_none()
    if policy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")

    if body.name is not None:
        policy.name = body.name
    if body.description is not None:
        policy.description = body.description
    if body.formula_type is not None:
        policy.formula_type = body.formula_type
    if body.allocations is not None:
        policy.allocations = [a.model_dump(mode="json") for a in body.allocations]
    if body.is_active is not None:
        policy.is_active = body.is_active

    await db.commit()
    await db.refresh(policy)
    return SharedCostPolicyResponse.model_validate(policy)


@router.delete("/shared-cost-policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shared_cost_policy(
    policy_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    workspace: Workspace = auth[0]
    result = await db.execute(
        select(SharedCostPolicy).where(
            SharedCostPolicy.id == policy_id,
            SharedCostPolicy.workspace_id == workspace.id,
        )
    )
    policy = result.scalar_one_or_none()
    if policy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    await db.delete(policy)
    await db.commit()


@router.post(
    "/shared-cost-policies/{policy_id}/allocate",
    response_model=SharedCostAllocationResult,
)
async def allocate_shared_cost(
    policy_id: uuid.UUID,
    body: dict[str, Any],
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SharedCostAllocationResult:
    """Compute how pool_usd distributes across allocations for this policy."""
    workspace: Workspace = auth[0]
    # Verify ownership
    check = await db.execute(
        select(SharedCostPolicy).where(
            SharedCostPolicy.id == policy_id,
            SharedCostPolicy.workspace_id == workspace.id,
        )
    )
    if check.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")

    pool_str = body.get("pool_usd")
    if pool_str is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="pool_usd is required",
        )
    try:
        from decimal import Decimal as _Decimal  # noqa: PLC0415

        pool_usd = _Decimal(str(pool_str))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="pool_usd must be a valid decimal number",
        ) from exc

    try:
        result = await compute_shared_cost_allocation(db, policy_id, pool_usd)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return SharedCostAllocationResult(**result)


# ── Chargeback Rules ─────────────────────────────────────────────────────────


@router.post(
    "/chargeback-rules",
    response_model=ChargebackRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_chargeback_rule(
    body: ChargebackRuleCreate,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ChargebackRuleResponse:
    workspace: Workspace = auth[0]
    rule = ChargebackRule(
        workspace_id=workspace.id,
        allocation_type=body.allocation_type,
        dimension=body.dimension,
        weight=body.weight,
        cost_center_id=body.cost_center_id,
        status="pending_approval" if body.require_approval else "active",
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return ChargebackRuleResponse.model_validate(rule)


@router.get("/chargeback-rules", response_model=ChargebackRuleList)
async def list_chargeback_rules(
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: str | None = Query(None, alias="status"),
) -> ChargebackRuleList:
    workspace: Workspace = auth[0]
    stmt = select(ChargebackRule).where(ChargebackRule.workspace_id == workspace.id)
    if status_filter:
        stmt = stmt.where(ChargebackRule.status == status_filter)
    result = await db.execute(stmt.order_by(ChargebackRule.created_at.desc()))
    return ChargebackRuleList(
        items=[ChargebackRuleResponse.model_validate(r) for r in result.scalars().all()]
    )


@router.get("/chargeback-rules/{rule_id}", response_model=ChargebackRuleResponse)
async def get_chargeback_rule(
    rule_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ChargebackRuleResponse:
    workspace: Workspace = auth[0]
    result = await db.execute(
        select(ChargebackRule).where(
            ChargebackRule.id == rule_id,
            ChargebackRule.workspace_id == workspace.id,
        )
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    return ChargebackRuleResponse.model_validate(rule)


@router.delete("/chargeback-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chargeback_rule(
    rule_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    workspace: Workspace = auth[0]
    result = await db.execute(
        select(ChargebackRule).where(
            ChargebackRule.id == rule_id,
            ChargebackRule.workspace_id == workspace.id,
        )
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    await db.delete(rule)
    await db.commit()
