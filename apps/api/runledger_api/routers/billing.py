"""
Billing CRUD + reconciliation + export endpoints.

Prefix: /billing
Auth: Bearer API key (workspace-scoped)

Endpoints
---------
POST   /billing/periods                          Create a billing period
GET    /billing/periods                          List periods (optional ?status=)
GET    /billing/periods/{id}                     Single period
POST   /billing/periods/{id}/close               Close + sign + dispatch webhook
GET    /billing/periods/{id}/reconciliation      Run reconciliation check
GET    /billing/periods/{id}/breakdown           Hierarchical breakdown by app/user
GET    /billing/periods/{id}/export              Export CSV / signed JSON / QB / NetSuite
POST   /billing/periods/{id}/adjustments         Add a credit/refund/surcharge line
GET    /billing/periods/{id}/adjustments         List adjustments for a period
DELETE /billing/periods/{id}/adjustments/{adj}   Remove an adjustment
POST   /billing/chargeback-rules                 Create a chargeback rule
GET    /billing/chargeback-rules                 List chargeback rules
POST   /billing/cost-centers                     Create a cost center
GET    /billing/cost-centers                     List cost centers
GET    /billing/cost-centers/tree                Cost center hierarchy tree
GET    /billing/cost-centers/{id}                Get a cost center
PUT    /billing/cost-centers/{id}                Update a cost center
DELETE /billing/cost-centers/{id}                Delete a cost center
POST   /billing/webhooks                         Create a billing webhook config
GET    /billing/webhooks                         List billing webhook configs
DELETE /billing/webhooks/{id}                    Delete a billing webhook config
GET    /billing/webhooks/{id}/deliveries         List delivery attempts for a webhook
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
from runledger_api.core.feature_gate import require_cloud
from runledger_api.core.ratelimit import management_rate_limit
from runledger_api.models.billing import (
    BillingAdjustment,
    BillingPeriod,
    ChargebackRule,
    CostCenter,
)
from runledger_api.models.billing_webhooks import BillingWebhookConfig, BillingWebhookDelivery
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
    CostCenterCreate,
    CostCenterList,
    CostCenterNode,
    CostCenterResponse,
    CostCenterUpdate,
    PeriodBreakdown,
    ReconciliationResult,
    UsageSnapshotResponse,
)
from runledger_api.schemas.billing_webhooks import (
    BillingWebhookConfigCreate,
    BillingWebhookConfigList,
    BillingWebhookConfigResponse,
    BillingWebhookDeliveryList,
    BillingWebhookDeliveryResponse,
)
from runledger_api.services.billing import (
    add_adjustment,
    close_billing_period,
    export_csv,
    export_signed_json,
    get_cost_center_tree,
    get_period_adjustments,
    get_period_breakdown,
    run_reconciliation,
)
from runledger_api.services.billing_webhooks import (
    dispatch_billing_webhook,
    export_netsuite_csv,
    export_quickbooks_csv,
)
from runledger_api.services.crypto import encrypt_secret
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

    return BillingPeriodList(
        items=[BillingPeriodResponse.model_validate(p) for p in periods]
    )


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

    # Fire-and-forget: HMAC-signed billing webhook dispatch
    async def _dispatch_webhooks() -> None:
        try:
            # Reload period inside new task context to get updated total
            result2 = await db.execute(select(BillingPeriod).where(BillingPeriod.id == period_id))
            p2 = result2.scalar_one_or_none()
            if p2:
                await dispatch_billing_webhook(db, p2)
        except Exception:
            pass  # never break the response

    _asyncio.create_task(_dispatch_webhooks())

    return UsageSnapshotResponse(
        id=str(snapshot.id),
        billing_period_id=str(snapshot.billing_period_id),
        signature=snapshot.signature,
        signing_key_id=snapshot.signing_key_id,
        created_at=snapshot.created_at,
    )


# ── GET /billing/periods/{id}/reconciliation ──────────────────────────────────


@router.get("/periods/{period_id}/reconciliation", response_model=ReconciliationResult)
async def get_reconciliation(
    period_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReconciliationResult:
    workspace: Workspace = auth[0]
    """Run a reconciliation check for the billing period."""
    require_cloud("Invoice reconciliation")
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

    try:
        return await run_reconciliation(db, period_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


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
    format: Annotated[str, Query(pattern="^(csv|signed_json|quickbooks|netsuite)$")] = "csv",
) -> Response:
    workspace: Workspace = auth[0]
    """Export billing period data — csv, signed_json, quickbooks, or netsuite."""
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
        elif format == "quickbooks":
            qb_csv = await export_quickbooks_csv(db, period_id)
            return Response(
                content=qb_csv,
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=period_{period_id}_quickbooks.csv"
                },
            )
        elif format == "netsuite":
            ns_csv = await export_netsuite_csv(db, period_id)
            return Response(
                content=ns_csv,
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=period_{period_id}_netsuite.csv"
                },
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


# ── POST /billing/chargeback-rules ────────────────────────────────────────────


@router.post(
    "/chargeback-rules",
    response_model=ChargebackRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_chargeback_rule(
    body: ChargebackRuleCreate,
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ChargebackRuleResponse:
    workspace: Workspace = auth[0]
    """Create a chargeback allocation rule for this workspace."""
    rule = ChargebackRule(
        workspace_id=workspace.id,
        allocation_type=body.allocation_type,
        dimension=body.dimension,
        weight=body.weight,
        cost_center_id=body.cost_center_id,
    )
    db.add(rule)
    await db.flush()

    # Optionally gate through the approvals system
    if body.require_approval:
        from runledger_api.models.approvals import Approval  # noqa: PLC0415

        approval = Approval(
            workspace_id=workspace.id,
            request_type="chargeback_rule",
            request={
                "rule_id": str(rule.id),
                "allocation_type": body.allocation_type,
                "dimension": body.dimension,
                "weight": str(body.weight),
                "cost_center_id": str(body.cost_center_id) if body.cost_center_id else None,
            },
            status="pending",
            requested_by=str(workspace.id),
        )
        db.add(approval)

    await db.commit()
    await db.refresh(rule)

    log.info(
        "chargeback_rule_created",
        rule_id=str(rule.id),
        workspace_id=str(workspace.id),
        allocation_type=rule.allocation_type,
        dimension=rule.dimension,
        weight=str(rule.weight),
        cost_center_id=str(rule.cost_center_id) if rule.cost_center_id else None,
    )

    return ChargebackRuleResponse.model_validate(rule)


# ── GET /billing/chargeback-rules ─────────────────────────────────────────────


@router.get("/chargeback-rules", response_model=ChargebackRuleList)
async def list_chargeback_rules(
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ChargebackRuleList:
    workspace: Workspace = auth[0]
    """List chargeback rules for this workspace."""
    result = await db.execute(
        select(ChargebackRule)
        .where(ChargebackRule.workspace_id == workspace.id)
        .order_by(ChargebackRule.created_at.desc())
    )
    rules: list[ChargebackRule] = list(result.scalars())

    return ChargebackRuleList(
        items=[ChargebackRuleResponse.model_validate(r) for r in rules]
    )


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


# ── Cost Centers ──────────────────────────────────────────────────────────────


@router.post(
    "/cost-centers",
    response_model=CostCenterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_cost_center(
    body: CostCenterCreate,
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CostCenterResponse:
    workspace: Workspace = auth[0]
    """Create a cost center (optionally nested under a parent)."""
    cc = CostCenter(
        workspace_id=workspace.id,
        name=body.name,
        code=body.code,
        parent_id=body.parent_id,
        description=body.description,
    )
    db.add(cc)
    await db.commit()
    await db.refresh(cc)
    return CostCenterResponse.model_validate(cc)


@router.get("/cost-centers", response_model=CostCenterList)
async def list_cost_centers(
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CostCenterList:
    workspace: Workspace = auth[0]
    result = await db.execute(
        select(CostCenter)
        .where(CostCenter.workspace_id == workspace.id)
        .order_by(CostCenter.name)
    )
    items = list(result.scalars())
    return CostCenterList(
        items=[CostCenterResponse.model_validate(c) for c in items],
        total=len(items),
    )


@router.get("/cost-centers/tree", response_model=list[CostCenterNode])
async def get_cost_center_tree_endpoint(
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[CostCenterNode]:
    workspace: Workspace = auth[0]
    """Return cost center hierarchy as a nested tree."""
    return await get_cost_center_tree(db, workspace.id)


@router.get("/cost-centers/{cost_center_id}", response_model=CostCenterResponse)
async def get_cost_center(
    cost_center_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CostCenterResponse:
    workspace: Workspace = auth[0]
    result = await db.execute(
        select(CostCenter).where(
            CostCenter.id == cost_center_id,
            CostCenter.workspace_id == workspace.id,
        )
    )
    cc = result.scalar_one_or_none()
    if cc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cost center not found")
    return CostCenterResponse.model_validate(cc)


@router.put("/cost-centers/{cost_center_id}", response_model=CostCenterResponse)
async def update_cost_center(
    cost_center_id: uuid.UUID,
    body: CostCenterUpdate,
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CostCenterResponse:
    workspace: Workspace = auth[0]
    result = await db.execute(
        select(CostCenter).where(
            CostCenter.id == cost_center_id,
            CostCenter.workspace_id == workspace.id,
        )
    )
    cc = result.scalar_one_or_none()
    if cc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cost center not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(cc, field, value)
    await db.commit()
    await db.refresh(cc)
    return CostCenterResponse.model_validate(cc)


@router.delete("/cost-centers/{cost_center_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cost_center(
    cost_center_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    workspace: Workspace = auth[0]
    result = await db.execute(
        select(CostCenter).where(
            CostCenter.id == cost_center_id,
            CostCenter.workspace_id == workspace.id,
        )
    )
    cc = result.scalar_one_or_none()
    if cc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cost center not found")
    await db.delete(cc)
    await db.commit()


# ── POST /billing/webhooks ────────────────────────────────────────────────────


@router.post(
    "/webhooks",
    response_model=BillingWebhookConfigResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_billing_webhook(
    body: BillingWebhookConfigCreate,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BillingWebhookConfigResponse:
    workspace: Workspace = auth[0]
    """Register a webhook endpoint to receive billing.period.closed events."""
    cfg = BillingWebhookConfig(
        workspace_id=workspace.id,
        url=body.url,
        secret=encrypt_secret(body.secret),
        label=body.label,
    )
    db.add(cfg)
    await db.flush()
    await db.refresh(cfg)
    await db.commit()
    return BillingWebhookConfigResponse.model_validate(cfg)


# ── GET /billing/webhooks ─────────────────────────────────────────────────────


@router.get("/webhooks", response_model=BillingWebhookConfigList)
async def list_billing_webhooks(
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BillingWebhookConfigList:
    workspace: Workspace = auth[0]
    """List billing webhook configurations for this workspace."""
    result = await db.execute(
        select(BillingWebhookConfig)
        .where(BillingWebhookConfig.workspace_id == workspace.id)
        .order_by(BillingWebhookConfig.created_at.desc())
    )
    cfgs = list(result.scalars().all())
    return BillingWebhookConfigList(
        items=[BillingWebhookConfigResponse.model_validate(c) for c in cfgs]
    )


# ── DELETE /billing/webhooks/{id} ─────────────────────────────────────────────


@router.delete("/webhooks/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_billing_webhook(
    webhook_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    workspace: Workspace = auth[0]
    result = await db.execute(
        select(BillingWebhookConfig).where(
            BillingWebhookConfig.id == webhook_id,
            BillingWebhookConfig.workspace_id == workspace.id,
        )
    )
    cfg = result.scalar_one_or_none()
    if cfg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    await db.delete(cfg)
    await db.commit()


# ── GET /billing/webhooks/{id}/deliveries ─────────────────────────────────────


@router.get("/webhooks/{webhook_id}/deliveries", response_model=BillingWebhookDeliveryList)
async def list_webhook_deliveries(
    webhook_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> BillingWebhookDeliveryList:
    workspace: Workspace = auth[0]
    # Verify webhook belongs to workspace
    cfg_result = await db.execute(
        select(BillingWebhookConfig).where(
            BillingWebhookConfig.id == webhook_id,
            BillingWebhookConfig.workspace_id == workspace.id,
        )
    )
    if cfg_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    result = await db.execute(
        select(BillingWebhookDelivery)
        .where(BillingWebhookDelivery.webhook_config_id == webhook_id)
        .order_by(BillingWebhookDelivery.created_at.desc())
        .limit(limit)
    )
    deliveries = list(result.scalars().all())
    return BillingWebhookDeliveryList(
        items=[BillingWebhookDeliveryResponse.model_validate(d) for d in deliveries]
    )
