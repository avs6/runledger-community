"""
Billing & chargeback endpoints.

Prefix: /billing
Auth: dashboard session or API key. Reads need billing access (org admin, org manager,
org billing admin or workspace admin); writes need org admin (periods, adjustments,
shared costs, signing key) or workspace admin (cost centers, chargeback rules).

Periods
  POST   /billing/periods                          Create (dates validated, no overlaps)
  GET    /billing/periods                          List (?status=, access group / key scope)
  GET    /billing/periods/{id}                     Get
  PATCH  /billing/periods/{id}                     Edit an open period
  DELETE /billing/periods/{id}                     Delete an open period with no adjustments
  POST   /billing/periods/{id}/close               Lock, freeze lines and totals, sign
  POST   /billing/periods/{id}/reopen              Reopen a closed period (reason required)
  GET    /billing/periods/{id}/breakdown           Application → user (frozen when closed)
  GET    /billing/periods/{id}/reconciliation      Cross-checks, incl. frozen-snapshot drift
  GET    /billing/periods/{id}/export              CSV or signed JSON (frozen when closed)
  POST|GET|PUT|DELETE /billing/periods/{id}/adjustments[/{adj}]   Open periods only

Cost centers and chargeback
  POST|GET /billing/cost-centers, GET /billing/cost-centers/tree
  GET|PUT|DELETE /billing/cost-centers/{id}
  POST|GET /billing/chargeback-rules, GET|PUT|DELETE /billing/chargeback-rules/{id}
  GET    /billing/chargeback-report                By dimension, with budget variance
  GET    /billing/chargeback-report/export         CSV / JSON
  GET    /billing/chargeback-report/cost-centers   Rules + shared costs applied per center

Shared costs
  POST|GET /billing/shared-cost-policies, GET|PUT|DELETE /billing/shared-cost-policies/{id}
  POST   /billing/shared-cost-policies/{id}/allocate   Preview a split
  POST   /billing/shared-cost-policies/{id}/apply      Persist a split for a month
  GET    /billing/cost-allocations                     Applied splits (?period=)
  DELETE /billing/cost-allocations/{id}

Signing
  GET    /billing/signing-key, POST /billing/signing-key/rotate, POST /billing/verify
"""

from __future__ import annotations

import asyncio as _asyncio
import csv
import io
import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Any

import sqlalchemy as sa
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import AsyncSessionLocal, get_db
from runledger_api.core.deps import (
    require_billing_access,
    require_org_admin,
    require_workspace_admin,
)
from runledger_api.core.pagination import PageDep, paginate, paginate_list
from runledger_api.core.ratelimit import management_rate_limit
from runledger_api.models.access_groups import AccessGroup, AccessGroupMember
from runledger_api.models.approvals import Approval
from runledger_api.models.billing import (
    BillingAdjustment,
    BillingPeriod,
    ChargebackRule,
    CostAllocation,
    CostCenter,
    SharedCostPolicy,
)
from runledger_api.models.events import ProviderCall
from runledger_api.models.tenant import ApiKey, Workspace
from runledger_api.schemas.billing import (
    BillingAdjustmentCreate,
    BillingAdjustmentList,
    BillingAdjustmentResponse,
    BillingAdjustmentUpdate,
    BillingPeriodCreate,
    BillingPeriodList,
    BillingPeriodReopen,
    BillingPeriodResponse,
    BillingPeriodUpdate,
    BillingSigningKey,
    BillingVerifyRequest,
    BillingVerifyResult,
    ChargebackReportList,
    ChargebackRuleCreate,
    ChargebackRuleList,
    ChargebackRuleResponse,
    ChargebackRuleUpdate,
    CostAllocationList,
    CostAllocationResponse,
    CostCenterCreate,
    CostCenterList,
    CostCenterNode,
    CostCenterReport,
    CostCenterResponse,
    CostCenterUpdate,
    PeriodBreakdown,
    ReconciliationResult,
    SharedCostAllocationResult,
    SharedCostApply,
    SharedCostPolicyCreate,
    SharedCostPolicyList,
    SharedCostPolicyResponse,
    SharedCostPolicyUpdate,
    UsageSnapshotResponse,
)
from runledger_api.services import billing_signing
from runledger_api.services.audit import emit_audit_event
from runledger_api.services.billable import billable_filters
from runledger_api.services.billing import (
    BillingConflict,
    add_adjustment,
    apply_shared_cost_policy,
    build_chargeback_report,
    build_cost_center_report,
    check_period_overlap,
    close_billing_period,
    compute_shared_cost_allocation,
    csv_safe,
    export_csv,
    export_signed_json,
    get_cost_center_tree,
    get_period_adjustments,
    get_period_breakdown,
    reopen_billing_period,
    run_reconciliation,
    validate_cost_center_parent,
    validate_rule,
    validate_shared_cost_allocations,
)
from runledger_api.services.email import send_billing_period_closed_email
from runledger_api.services.email_utils import get_email_preference, get_workspace_admin_users

router = APIRouter(
    prefix="/billing", tags=["billing"], dependencies=[Depends(management_rate_limit)]
)
log = structlog.get_logger()

OrgAdminAuth = Annotated[tuple[Any, ...], Depends(require_org_admin)]
WorkspaceAdminAuth = Annotated[tuple[Any, ...], Depends(require_workspace_admin)]
BillingReadAuth = Annotated[tuple[Any, ...], Depends(require_billing_access)]
DbDep = Annotated[AsyncSession, Depends(get_db)]


def _actor(auth: tuple[Any, ...]) -> tuple[uuid.UUID | None, str | None]:
    """(user id, email) of the caller, for created_by fields and audit."""
    user = auth[1] if len(auth) > 1 else None
    return (getattr(user, "id", None), getattr(user, "email", None))


def _conflict(exc: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


def _bad(exc: Exception) -> HTTPException:
    msg = str(exc)
    code = (
        status.HTTP_404_NOT_FOUND
        if "not found" in msg.lower()
        else status.HTTP_422_UNPROCESSABLE_CONTENT
    )
    return HTTPException(status_code=code, detail=msg)


async def _audit(
    db: AsyncSession,
    auth: tuple[Any, ...],
    action: str,
    target_type: str,
    target_id: Any,
    *,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> None:
    user_id, _ = _actor(auth)
    await emit_audit_event(
        db,
        auth[0].id,
        action,
        actor_user_id=user_id,
        target_type=target_type,
        target_id=str(target_id),
        before=before,
        after=after,
    )


async def _owned_period(
    db: AsyncSession, workspace: Workspace, period_id: uuid.UUID, *, lock: bool = False
) -> BillingPeriod:
    stmt = select(BillingPeriod).where(
        BillingPeriod.id == period_id, BillingPeriod.workspace_id == workspace.id
    )
    if lock:
        stmt = stmt.with_for_update()
    period = (await db.execute(stmt)).scalar_one_or_none()
    if period is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Billing period not found"
        )
    return period


def _period_audit(p: BillingPeriod) -> dict[str, Any]:
    return {
        "period_start": str(p.period_start),
        "period_end": str(p.period_end),
        "status": p.status,
        "currency": p.currency,
        "exchange_rate_to_usd": str(p.exchange_rate_to_usd),
    }


# ── Periods ───────────────────────────────────────────────────────────────────


@router.post("/periods", response_model=BillingPeriodResponse, status_code=status.HTTP_201_CREATED)
async def create_billing_period(
    body: BillingPeriodCreate, auth: OrgAdminAuth, db: DbDep
) -> BillingPeriodResponse:
    """Create a billing period. Dates may not overlap another period of the workspace."""
    workspace: Workspace = auth[0]
    # Serialize creates per workspace so two concurrent requests can't both pass the
    # overlap check.
    await db.execute(
        sa.text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
        {"k": f"billing-periods:{workspace.id}"},
    )
    try:
        await check_period_overlap(db, workspace.id, body.period_start, body.period_end)
    except BillingConflict as exc:
        raise _conflict(exc) from exc
    period = BillingPeriod(
        workspace_id=workspace.id,
        period_start=body.period_start,
        period_end=body.period_end,
        status="open",
        currency=body.currency,
        exchange_rate_to_usd=body.exchange_rate_to_usd,
    )
    db.add(period)
    await db.flush()
    await _audit(
        db, auth, "billing.period.created", "billing_period", period.id, after=_period_audit(period)
    )
    await db.commit()
    await db.refresh(period)
    return BillingPeriodResponse.model_validate(period)


@router.get("/periods", response_model=BillingPeriodList)
async def list_billing_periods(
    auth: BillingReadAuth,
    db: DbDep,
    page: PageDep,
    response: Response,
    status_filter: Annotated[
        str | None, Query(alias="status", pattern="^(open|closing|closed)$")
    ] = None,
    access_group_id: Annotated[uuid.UUID | None, Query()] = None,
    api_key_id: Annotated[uuid.UUID | None, Query()] = None,
) -> BillingPeriodList:
    """List billing periods, optionally only those with usage from a group or key."""
    workspace: Workspace = auth[0]
    stmt = select(BillingPeriod).where(BillingPeriod.workspace_id == workspace.id)
    if status_filter:
        stmt = stmt.where(BillingPeriod.status == status_filter)
    scope_filter: sa.ColumnElement[bool] | None = None
    if access_group_id is not None:
        group = (
            await db.execute(
                select(AccessGroup.id).where(
                    AccessGroup.id == access_group_id, AccessGroup.workspace_id == workspace.id
                )
            )
        ).scalar_one_or_none()
        if group is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Access group not found"
            )
        scope_filter = ProviderCall.end_user_id.in_(
            select(sa.cast(AccessGroupMember.user_id, sa.String)).where(
                AccessGroupMember.group_id == access_group_id
            )
        )
    if api_key_id is not None:
        key = (
            await db.execute(
                select(ApiKey.id).where(
                    ApiKey.id == api_key_id,
                    ApiKey.workspace_id == workspace.id,
                    ApiKey.revoked_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if key is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
        scope_filter = ProviderCall.api_key_id == api_key_id
    if scope_filter is not None:
        stmt = stmt.where(
            sa.exists(
                select(ProviderCall.id)
                .where(
                    ProviderCall.workspace_id == workspace.id,
                    sa.func.date(ProviderCall.created_at) >= BillingPeriod.period_start,
                    sa.func.date(ProviderCall.created_at) <= BillingPeriod.period_end,
                    *billable_filters(),
                    scope_filter,
                )
                .limit(1)
                .correlate(BillingPeriod)
            )
        )
    periods = await paginate(
        db, stmt.order_by(BillingPeriod.period_start.desc(), BillingPeriod.id), page, response
    )
    return BillingPeriodList(items=[BillingPeriodResponse.model_validate(p) for p in periods])


@router.get("/periods/{period_id}", response_model=BillingPeriodResponse)
async def get_billing_period(
    period_id: uuid.UUID, auth: BillingReadAuth, db: DbDep
) -> BillingPeriodResponse:
    return BillingPeriodResponse.model_validate(await _owned_period(db, auth[0], period_id))


@router.patch("/periods/{period_id}", response_model=BillingPeriodResponse)
async def update_billing_period(
    period_id: uuid.UUID, body: BillingPeriodUpdate, auth: OrgAdminAuth, db: DbDep
) -> BillingPeriodResponse:
    """Edit dates or currency of an open period."""
    workspace: Workspace = auth[0]
    period = await _owned_period(db, workspace, period_id, lock=True)
    if period.status != "open":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only an open billing period can be edited; reopen it first",
        )
    before = _period_audit(period)
    start = body.period_start or period.period_start
    end = body.period_end or period.period_end
    if end < start:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="period_end must be on or after period_start",
        )
    try:
        await check_period_overlap(db, workspace.id, start, end, exclude_id=period.id)
    except BillingConflict as exc:
        raise _conflict(exc) from exc
    period.period_start, period.period_end = start, end
    if body.currency is not None:
        period.currency = body.currency
    if body.exchange_rate_to_usd is not None:
        period.exchange_rate_to_usd = body.exchange_rate_to_usd
    await _audit(
        db,
        auth,
        "billing.period.updated",
        "billing_period",
        period.id,
        before=before,
        after=_period_audit(period),
    )
    await db.commit()
    await db.refresh(period)
    return BillingPeriodResponse.model_validate(period)


@router.delete("/periods/{period_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_billing_period(period_id: uuid.UUID, auth: OrgAdminAuth, db: DbDep) -> None:
    """Delete an open period that has no adjustments. Closed periods are kept as records."""
    period = await _owned_period(db, auth[0], period_id, lock=True)
    if period.status != "open":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A closed billing period cannot be deleted"
        )
    has_adj = (
        await db.execute(
            select(BillingAdjustment.id)
            .where(BillingAdjustment.billing_period_id == period.id)
            .limit(1)
        )
    ).first()
    if has_adj:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Remove the period's adjustments before deleting it",
        )
    await _audit(
        db,
        auth,
        "billing.period.deleted",
        "billing_period",
        period.id,
        before=_period_audit(period),
    )
    await db.delete(period)
    await db.commit()


@router.post("/periods/{period_id}/close", response_model=UsageSnapshotResponse)
async def close_period(
    period_id: uuid.UUID, auth: OrgAdminAuth, db: DbDep
) -> UsageSnapshotResponse:
    """Close a period: freeze its billing lines and totals and sign the snapshot."""
    workspace: Workspace = auth[0]
    await _owned_period(db, workspace, period_id)
    _, email = _actor(auth)
    try:
        snapshot = await close_billing_period(db, period_id, closed_by=email)
    except BillingConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Billing period is already closed"
        ) from exc
    except ValueError as exc:
        raise _bad(exc) from exc
    period = await _owned_period(db, workspace, period_id)
    await _audit(
        db,
        auth,
        "billing.period.closed",
        "billing_period",
        period.id,
        after={
            "total_cost_usd": str(period.total_cost_usd),
            "net_cost_usd": str(period.net_cost_usd),
            "snapshot_id": str(snapshot.id),
            "signing_key_id": snapshot.signing_key_id,
        },
    )
    await db.commit()

    async def _notify_billing_closed() -> None:
        # Runs after the response: use its own session, never the request's (which is
        # closed when the request ends).
        try:
            async with AsyncSessionLocal() as bg:
                prefs = await get_email_preference(bg, workspace.id)
                if prefs is not None and not prefs.billing_closed_enabled:
                    return
                admins = await get_workspace_admin_users(bg, workspace.id)
            await _asyncio.gather(
                *[
                    send_billing_period_closed_email(
                        to_email=u.email,
                        full_name=u.full_name,
                        period_start=str(period.period_start),
                        period_end=str(period.period_end),
                        total_cost_usd=str(period.total_cost_usd),
                        snapshot_hash=snapshot.signature[:16],
                        workspace_name=workspace.name,
                    )
                    for u in admins
                ],
                return_exceptions=True,
            )
        except Exception:  # noqa: BLE001
            log.warning("billing_closed_email_failed", period_id=str(period_id))

    _asyncio.create_task(_notify_billing_closed())
    return UsageSnapshotResponse(
        id=str(snapshot.id),
        billing_period_id=str(snapshot.billing_period_id),
        signature=snapshot.signature,
        signing_key_id=snapshot.signing_key_id,
        created_at=snapshot.created_at,
    )


@router.post("/periods/{period_id}/reopen", response_model=BillingPeriodResponse)
async def reopen_period(
    period_id: uuid.UUID, body: BillingPeriodReopen, auth: OrgAdminAuth, db: DbDep
) -> BillingPeriodResponse:
    """Reopen a closed period (e.g. late data or a correction). Earlier snapshots are
    kept; closing again freezes a new one."""
    await _owned_period(db, auth[0], period_id)
    try:
        period = await reopen_billing_period(db, period_id, body.reason)
    except BillingConflict as exc:
        raise _conflict(exc) from exc
    await _audit(
        db,
        auth,
        "billing.period.reopened",
        "billing_period",
        period.id,
        after={"reason": body.reason},
    )
    await db.commit()
    return BillingPeriodResponse.model_validate(period)


@router.get("/periods/{period_id}/breakdown", response_model=PeriodBreakdown)
async def get_breakdown(
    period_id: uuid.UUID,
    auth: BillingReadAuth,
    db: DbDep,
    access_group_id: Annotated[uuid.UUID | None, Query()] = None,
    api_key_id: Annotated[uuid.UUID | None, Query()] = None,
    end_user_id: Annotated[str | None, Query(max_length=255)] = None,
) -> PeriodBreakdown:
    await _owned_period(db, auth[0], period_id)
    try:
        return await get_period_breakdown(
            db,
            period_id,
            access_group_id=access_group_id,
            api_key_id=api_key_id,
            end_user_id=end_user_id,
        )
    except ValueError as exc:
        raise _bad(exc) from exc


@router.get("/periods/{period_id}/reconciliation", response_model=ReconciliationResult)
async def get_period_reconciliation(
    period_id: uuid.UUID,
    auth: BillingReadAuth,
    db: DbDep,
    access_group_id: Annotated[uuid.UUID | None, Query()] = None,
    api_key_id: Annotated[uuid.UUID | None, Query()] = None,
) -> ReconciliationResult:
    await _owned_period(db, auth[0], period_id)
    try:
        return await run_reconciliation(
            db, period_id, access_group_id=access_group_id, api_key_id=api_key_id
        )
    except ValueError as exc:
        raise _bad(exc) from exc


@router.get("/periods/{period_id}/export")
async def export_period(
    period_id: uuid.UUID,
    auth: BillingReadAuth,
    db: DbDep,
    format: Annotated[str, Query(pattern="^(csv|signed_json)$")] = "csv",
    access_group_id: Annotated[uuid.UUID | None, Query()] = None,
    api_key_id: Annotated[uuid.UUID | None, Query()] = None,
) -> Response:
    """Billing lines as CSV or signed JSON; a closed period exports its frozen lines."""
    await _owned_period(db, auth[0], period_id)
    try:
        if format == "csv":
            content = await export_csv(
                db, period_id, access_group_id=access_group_id, api_key_id=api_key_id
            )
            return Response(
                content=content,
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=period_{period_id}.csv"},
            )
        payload = await export_signed_json(
            db, period_id, access_group_id=access_group_id, api_key_id=api_key_id
        )
        return Response(
            content=json.dumps(payload, default=str),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=period_{period_id}.json"},
        )
    except ValueError as exc:
        raise _bad(exc) from exc


# ── Adjustments ───────────────────────────────────────────────────────────────


def _adj_audit(a: BillingAdjustment) -> dict[str, Any]:
    return {
        "adjustment_type": a.adjustment_type,
        "amount_usd": str(a.amount_usd),
        "description": a.description,
        "reference_id": a.reference_id,
    }


@router.post(
    "/periods/{period_id}/adjustments",
    response_model=BillingAdjustmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_adjustment(
    period_id: uuid.UUID, body: BillingAdjustmentCreate, auth: OrgAdminAuth, db: DbDep
) -> BillingAdjustmentResponse:
    """Add a credit, refund, prepaid deduction or surcharge to an open period."""
    workspace: Workspace = auth[0]
    _, email = _actor(auth)
    try:
        adj = await add_adjustment(
            db,
            workspace_id=workspace.id,
            billing_period_id=period_id,
            adjustment_type=body.adjustment_type,
            amount_usd=body.amount_usd,
            description=body.description,
            reference_id=body.reference_id,
            created_by=email,
        )
    except BillingConflict as exc:
        raise _conflict(exc) from exc
    except ValueError as exc:
        raise _bad(exc) from exc
    await _audit(
        db, auth, "billing.adjustment.created", "billing_adjustment", adj.id, after=_adj_audit(adj)
    )
    await db.commit()
    await db.refresh(adj)
    return BillingAdjustmentResponse.model_validate(adj)


@router.get("/periods/{period_id}/adjustments", response_model=BillingAdjustmentList)
async def list_adjustments(
    period_id: uuid.UUID, auth: BillingReadAuth, db: DbDep
) -> BillingAdjustmentList:
    workspace: Workspace = auth[0]
    await _owned_period(db, workspace, period_id)
    items = await get_period_adjustments(db, workspace.id, period_id)
    credits = sum((a.amount_usd for a in items if a.adjustment_type != "surcharge"), Decimal(0))
    surcharges = sum((a.amount_usd for a in items if a.adjustment_type == "surcharge"), Decimal(0))
    return BillingAdjustmentList(
        items=[BillingAdjustmentResponse.model_validate(a) for a in items],
        total_credits_usd=credits,
        total_surcharges_usd=surcharges,
        net_adjustment_usd=surcharges - credits,
    )


async def _open_period_adjustment(
    db: AsyncSession, workspace: Workspace, period_id: uuid.UUID, adjustment_id: uuid.UUID
) -> BillingAdjustment:
    period = await _owned_period(db, workspace, period_id, lock=True)
    if period.status != "open":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Adjustments on a closed billing period can't be changed; reopen it first",
        )
    adj = (
        await db.execute(
            select(BillingAdjustment).where(
                BillingAdjustment.id == adjustment_id,
                BillingAdjustment.billing_period_id == period_id,
                BillingAdjustment.workspace_id == workspace.id,
            )
        )
    ).scalar_one_or_none()
    if adj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Adjustment not found")
    return adj


@router.put(
    "/periods/{period_id}/adjustments/{adjustment_id}", response_model=BillingAdjustmentResponse
)
async def update_adjustment(
    period_id: uuid.UUID,
    adjustment_id: uuid.UUID,
    body: BillingAdjustmentUpdate,
    auth: OrgAdminAuth,
    db: DbDep,
) -> BillingAdjustmentResponse:
    adj = await _open_period_adjustment(db, auth[0], period_id, adjustment_id)
    before = _adj_audit(adj)
    for field in ("adjustment_type", "amount_usd", "description", "reference_id"):
        value = getattr(body, field)
        if value is not None:
            setattr(adj, field, value)
    await _audit(
        db,
        auth,
        "billing.adjustment.updated",
        "billing_adjustment",
        adj.id,
        before=before,
        after=_adj_audit(adj),
    )
    await db.commit()
    await db.refresh(adj)
    return BillingAdjustmentResponse.model_validate(adj)


@router.delete(
    "/periods/{period_id}/adjustments/{adjustment_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_adjustment(
    period_id: uuid.UUID, adjustment_id: uuid.UUID, auth: OrgAdminAuth, db: DbDep
) -> None:
    adj = await _open_period_adjustment(db, auth[0], period_id, adjustment_id)
    await _audit(
        db, auth, "billing.adjustment.deleted", "billing_adjustment", adj.id, before=_adj_audit(adj)
    )
    await db.delete(adj)
    await db.commit()


# ── Cost centers ──────────────────────────────────────────────────────────────


async def _owned_cost_center(
    db: AsyncSession, workspace: Workspace, cc_id: uuid.UUID
) -> CostCenter:
    cc = (
        await db.execute(
            select(CostCenter).where(
                CostCenter.id == cc_id, CostCenter.workspace_id == workspace.id
            )
        )
    ).scalar_one_or_none()
    if cc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cost center not found")
    return cc


@router.post(
    "/cost-centers", response_model=CostCenterResponse, status_code=status.HTTP_201_CREATED
)
async def create_cost_center(
    body: CostCenterCreate, auth: WorkspaceAdminAuth, db: DbDep
) -> CostCenterResponse:
    workspace: Workspace = auth[0]
    try:
        await validate_cost_center_parent(db, workspace.id, body.parent_id)
    except ValueError as exc:
        raise _bad(exc) from exc
    cc = CostCenter(
        workspace_id=workspace.id,
        name=body.name,
        code=body.code,
        parent_id=body.parent_id,
        description=body.description,
    )
    db.add(cc)
    await db.flush()
    await _audit(
        db,
        auth,
        "billing.cost_center.created",
        "cost_center",
        cc.id,
        after={"name": cc.name, "code": cc.code},
    )
    await db.commit()
    await db.refresh(cc)
    return CostCenterResponse.model_validate(cc)


@router.get("/cost-centers", response_model=CostCenterList)
async def list_cost_centers(
    auth: BillingReadAuth,
    db: DbDep,
    q: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> CostCenterList:
    workspace: Workspace = auth[0]
    stmt = select(CostCenter).where(CostCenter.workspace_id == workspace.id)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(sa.or_(CostCenter.name.ilike(like), CostCenter.code.ilike(like)))
    total = (await db.execute(select(sa.func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (await db.execute(stmt.order_by(CostCenter.name).limit(limit).offset(offset))).scalars()
    return CostCenterList(
        items=[CostCenterResponse.model_validate(c) for c in rows], total=int(total)
    )


@router.get("/cost-centers/tree", response_model=list[CostCenterNode])
async def cost_center_tree(auth: BillingReadAuth, db: DbDep) -> list[CostCenterNode]:
    return await get_cost_center_tree(db, auth[0].id)


@router.get("/cost-centers/{cc_id}", response_model=CostCenterResponse)
async def get_cost_center(cc_id: uuid.UUID, auth: BillingReadAuth, db: DbDep) -> CostCenterResponse:
    return CostCenterResponse.model_validate(await _owned_cost_center(db, auth[0], cc_id))


@router.put("/cost-centers/{cc_id}", response_model=CostCenterResponse)
async def update_cost_center(
    cc_id: uuid.UUID, body: CostCenterUpdate, auth: WorkspaceAdminAuth, db: DbDep
) -> CostCenterResponse:
    workspace: Workspace = auth[0]
    cc = await _owned_cost_center(db, workspace, cc_id)
    before = {
        "name": cc.name,
        "code": cc.code,
        "parent_id": str(cc.parent_id) if cc.parent_id else None,
    }
    if "parent_id" in body.model_fields_set:
        try:
            await validate_cost_center_parent(db, workspace.id, body.parent_id, cc.id)
        except ValueError as exc:
            raise _bad(exc) from exc
        cc.parent_id = body.parent_id
    for field in ("name", "code", "description"):
        if field in body.model_fields_set:
            setattr(cc, field, getattr(body, field))
    await _audit(
        db,
        auth,
        "billing.cost_center.updated",
        "cost_center",
        cc.id,
        before=before,
        after={
            "name": cc.name,
            "code": cc.code,
            "parent_id": str(cc.parent_id) if cc.parent_id else None,
        },
    )
    await db.commit()
    await db.refresh(cc)
    return CostCenterResponse.model_validate(cc)


@router.delete("/cost-centers/{cc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cost_center(cc_id: uuid.UUID, auth: WorkspaceAdminAuth, db: DbDep) -> None:
    """Delete a cost center that no rule, policy or child cost center uses."""
    workspace: Workspace = auth[0]
    cc = await _owned_cost_center(db, workspace, cc_id)
    in_rules = (
        await db.execute(
            select(ChargebackRule.id)
            .where(
                ChargebackRule.workspace_id == workspace.id,
                ChargebackRule.cost_center_id == cc.id,
                ChargebackRule.status.in_(["active", "pending_approval"]),
            )
            .limit(1)
        )
    ).first()
    children = (
        await db.execute(select(CostCenter.id).where(CostCenter.parent_id == cc.id).limit(1))
    ).first()
    policies = (
        await db.execute(
            select(SharedCostPolicy).where(SharedCostPolicy.workspace_id == workspace.id)
        )
    ).scalars()
    in_policy = any(
        str(a.get("cost_center_id")) == str(cc.id) for p in policies for a in (p.allocations or [])
    )
    if in_rules or children or in_policy:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cost center is used by an active rule, a shared-cost policy or a child cost center",
        )
    await _audit(
        db, auth, "billing.cost_center.deleted", "cost_center", cc.id, before={"name": cc.name}
    )
    await db.delete(cc)
    await db.commit()


# ── Chargeback rules ──────────────────────────────────────────────────────────


def _rule_audit(r: ChargebackRule) -> dict[str, Any]:
    return {
        "dimension": r.dimension,
        "dimension_value": r.dimension_value,
        "cost_center_id": str(r.cost_center_id) if r.cost_center_id else None,
        "weight": str(r.weight),
        "allocation_type": r.allocation_type,
        "status": r.status,
    }


async def _request_rule_approval(
    db: AsyncSession, workspace: Workspace, rule: ChargebackRule, requested_by: str | None
) -> None:
    """Send a rule through Approvals; it becomes active only when someone else approves."""
    approval = Approval(
        workspace_id=workspace.id,
        request_type="chargeback_rule",
        request={"rule_id": str(rule.id), **_rule_audit(rule)},
        requested_by=requested_by,
    )
    db.add(approval)
    await db.flush()
    rule.status = "pending_approval"
    rule.approval_id = approval.id


async def _owned_rule(db: AsyncSession, workspace: Workspace, rule_id: uuid.UUID) -> ChargebackRule:
    rule = (
        await db.execute(
            select(ChargebackRule)
            .where(ChargebackRule.id == rule_id, ChargebackRule.workspace_id == workspace.id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    return rule


@router.post(
    "/chargeback-rules", response_model=ChargebackRuleResponse, status_code=status.HTTP_201_CREATED
)
async def create_chargeback_rule(
    body: ChargebackRuleCreate, auth: WorkspaceAdminAuth, db: DbDep
) -> ChargebackRuleResponse:
    """Map a dimension value to a cost center. With ``require_approval`` the rule waits
    in Approvals and activates only when a different admin approves it."""
    workspace: Workspace = auth[0]
    _, email = _actor(auth)
    await db.execute(
        sa.text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
        {"k": f"chargeback-rules:{workspace.id}"},
    )
    try:
        await validate_rule(
            db,
            workspace.id,
            dimension=body.dimension,
            dimension_value=body.dimension_value,
            cost_center_id=body.cost_center_id,
            weight=body.weight,
            allocation_type=body.allocation_type,
            activating=not body.require_approval,
        )
    except BillingConflict as exc:
        raise _conflict(exc) from exc
    except ValueError as exc:
        raise _bad(exc) from exc
    rule = ChargebackRule(
        workspace_id=workspace.id,
        allocation_type=body.allocation_type,
        dimension=body.dimension,
        dimension_value=body.dimension_value,
        weight=body.weight,
        cost_center_id=body.cost_center_id,
        status="active",
        created_by=email,
    )
    db.add(rule)
    await db.flush()
    if body.require_approval:
        await _request_rule_approval(db, workspace, rule, email)
    await _audit(
        db,
        auth,
        "billing.chargeback_rule.created",
        "chargeback_rule",
        rule.id,
        after=_rule_audit(rule),
    )
    await db.commit()
    await db.refresh(rule)
    return ChargebackRuleResponse.model_validate(rule)


@router.get("/chargeback-rules", response_model=ChargebackRuleList)
async def list_chargeback_rules(
    auth: BillingReadAuth,
    db: DbDep,
    status_filter: Annotated[
        str | None, Query(alias="status", pattern="^(active|inactive|pending_approval|denied)$")
    ] = None,
) -> ChargebackRuleList:
    workspace: Workspace = auth[0]
    stmt = select(ChargebackRule).where(ChargebackRule.workspace_id == workspace.id)
    if status_filter:
        stmt = stmt.where(ChargebackRule.status == status_filter)
    rows = (await db.execute(stmt.order_by(ChargebackRule.created_at.desc()))).scalars()
    return ChargebackRuleList(items=[ChargebackRuleResponse.model_validate(r) for r in rows])


@router.get("/chargeback-rules/{rule_id}", response_model=ChargebackRuleResponse)
async def get_chargeback_rule(
    rule_id: uuid.UUID, auth: BillingReadAuth, db: DbDep
) -> ChargebackRuleResponse:
    workspace: Workspace = auth[0]
    rule = (
        await db.execute(
            select(ChargebackRule).where(
                ChargebackRule.id == rule_id, ChargebackRule.workspace_id == workspace.id
            )
        )
    ).scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    return ChargebackRuleResponse.model_validate(rule)


@router.put("/chargeback-rules/{rule_id}", response_model=ChargebackRuleResponse)
async def update_chargeback_rule(
    rule_id: uuid.UUID, body: ChargebackRuleUpdate, auth: WorkspaceAdminAuth, db: DbDep
) -> ChargebackRuleResponse:
    """Edit a rule or toggle it active/inactive.

    A rule pending approval or denied can't be activated here. Changing the mapping of
    an approval-gated rule sends it back to Approvals.
    """
    workspace: Workspace = auth[0]
    _, email = _actor(auth)
    await db.execute(
        sa.text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
        {"k": f"chargeback-rules:{workspace.id}"},
    )
    rule = await _owned_rule(db, workspace, rule_id)
    before = _rule_audit(rule)
    mapping_fields = ("allocation_type", "dimension", "dimension_value", "weight", "cost_center_id")
    changed_mapping = any(
        f in body.model_fields_set
        and getattr(body, f) is not None
        and getattr(body, f) != getattr(rule, f)
        for f in mapping_fields
    )
    if body.status == "active" and rule.status in ("pending_approval", "denied"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This rule is approval-gated; it becomes active when its approval is approved",
        )
    for f in mapping_fields:
        if f in body.model_fields_set and getattr(body, f) is not None:
            setattr(rule, f, getattr(body, f))
    target_status = body.status or rule.status
    gated = rule.approval_id is not None
    resubmit = gated and changed_mapping
    try:
        await validate_rule(
            db,
            workspace.id,
            dimension=rule.dimension,
            dimension_value=rule.dimension_value or "",
            cost_center_id=rule.cost_center_id,  # type: ignore[arg-type]
            weight=rule.weight,
            allocation_type=rule.allocation_type,
            exclude_rule_id=rule.id,
            activating=target_status == "active" and not resubmit,
        )
    except BillingConflict as exc:
        raise _conflict(exc) from exc
    except ValueError as exc:
        raise _bad(exc) from exc
    if resubmit:
        await _request_rule_approval(db, workspace, rule, email)
    elif body.status is not None:
        rule.status = body.status
    rule.updated_at = datetime.now(UTC)
    await _audit(
        db,
        auth,
        "billing.chargeback_rule.updated",
        "chargeback_rule",
        rule.id,
        before=before,
        after=_rule_audit(rule),
    )
    await db.commit()
    await db.refresh(rule)
    return ChargebackRuleResponse.model_validate(rule)


@router.delete("/chargeback-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chargeback_rule(rule_id: uuid.UUID, auth: WorkspaceAdminAuth, db: DbDep) -> None:
    workspace: Workspace = auth[0]
    rule = await _owned_rule(db, workspace, rule_id)
    if rule.approval_id is not None and rule.status == "pending_approval":
        await db.execute(
            sa.update(Approval)
            .where(Approval.id == rule.approval_id, Approval.status == "pending")
            .values(status="cancelled")
        )
    await _audit(
        db,
        auth,
        "billing.chargeback_rule.deleted",
        "chargeback_rule",
        rule.id,
        before=_rule_audit(rule),
    )
    await db.delete(rule)
    await db.commit()


# ── Chargeback reports ────────────────────────────────────────────────────────


@router.get("/chargeback-report", response_model=ChargebackReportList)
async def get_chargeback_report(
    auth: BillingReadAuth,
    db: DbDep,
    period: Annotated[str | None, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")] = None,
    dimension: Annotated[str | None, Query()] = None,
    access_group_id: Annotated[uuid.UUID | None, Query()] = None,
    api_key_id: Annotated[uuid.UUID | None, Query()] = None,
    end_user_id: Annotated[str | None, Query(max_length=255)] = None,
    page: PageDep = None,  # type: ignore[assignment]
    response: Response = None,  # type: ignore[assignment]
) -> ChargebackReportList:
    try:
        report = await build_chargeback_report(
            db,
            auth[0].id,
            period=period,
            dimension=dimension,
            access_group_id=access_group_id,
            api_key_id=api_key_id,
            end_user_id=end_user_id,
        )
    except ValueError as exc:
        raise _bad(exc) from exc
    # Totals cover the whole month; only the breakdown rows are paged.
    report.breakdown = paginate_list(report.breakdown, page, response)
    return ChargebackReportList(items=[report])


@router.get("/chargeback-report/cost-centers", response_model=CostCenterReport)
async def get_cost_center_report(
    auth: BillingReadAuth,
    db: DbDep,
    period: Annotated[str | None, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")] = None,
) -> CostCenterReport:
    """Cost per cost center for a month: active rules applied to billable cost, plus
    applied shared-cost pools; what no rule covers is reported as unassigned."""
    return await build_cost_center_report(db, auth[0].id, period=period)


@router.get("/chargeback-report/export")
async def export_chargeback_report(
    auth: BillingReadAuth,
    db: DbDep,
    period: Annotated[str | None, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")] = None,
    dimension: Annotated[str | None, Query()] = None,
    format: Annotated[str, Query(pattern="^(csv|json)$")] = "csv",
    access_group_id: Annotated[uuid.UUID | None, Query()] = None,
    api_key_id: Annotated[uuid.UUID | None, Query()] = None,
    end_user_id: Annotated[str | None, Query(max_length=255)] = None,
) -> Response:
    try:
        report = await build_chargeback_report(
            db,
            auth[0].id,
            period=period,
            dimension=dimension,
            access_group_id=access_group_id,
            api_key_id=api_key_id,
            end_user_id=end_user_id,
        )
    except ValueError as exc:
        raise _bad(exc) from exc
    filename = f"chargeback_{report.period}_{report.dimension}"
    if format == "json":
        return Response(
            content=json.dumps(report.model_dump(mode="json"), default=str),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}.json"},
        )
    buf = io.StringIO()
    writer = csv.writer(buf)
    cols = [
        "period",
        "dimension",
        "dimension_key",
        "dimension_value",
        "cost_usd",
        "pct_of_total",
        "budget_usd",
        "variance_usd",
        "call_count",
        "run_count",
        "allocation_status",
        "coverage_status",
    ]
    writer.writerow(cols)
    for item in report.breakdown:
        row = {"period": report.period, **item.model_dump()}
        writer.writerow([csv_safe(row.get(c)) for c in cols])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}.csv"},
    )


# ── Shared-cost policies ──────────────────────────────────────────────────────


async def _owned_policy(
    db: AsyncSession, workspace: Workspace, policy_id: uuid.UUID
) -> SharedCostPolicy:
    policy = (
        await db.execute(
            select(SharedCostPolicy).where(
                SharedCostPolicy.id == policy_id, SharedCostPolicy.workspace_id == workspace.id
            )
        )
    ).scalar_one_or_none()
    if policy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    return policy


@router.post(
    "/shared-cost-policies",
    response_model=SharedCostPolicyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_shared_cost_policy(
    body: SharedCostPolicyCreate, auth: OrgAdminAuth, db: DbDep
) -> SharedCostPolicyResponse:
    workspace: Workspace = auth[0]
    allocations = [a.model_dump(mode="json") for a in body.allocations]
    try:
        await validate_shared_cost_allocations(db, workspace.id, body.formula_type, allocations)
    except ValueError as exc:
        raise _bad(exc) from exc
    policy = SharedCostPolicy(
        workspace_id=workspace.id,
        name=body.name,
        description=body.description,
        formula_type=body.formula_type,
        allocations=allocations,
        is_active=body.is_active,
    )
    db.add(policy)
    await db.flush()
    await _audit(
        db,
        auth,
        "billing.shared_cost_policy.created",
        "shared_cost_policy",
        policy.id,
        after={"name": policy.name, "formula_type": policy.formula_type},
    )
    await db.commit()
    await db.refresh(policy)
    return SharedCostPolicyResponse.model_validate(policy)


@router.get("/shared-cost-policies", response_model=SharedCostPolicyList)
async def list_shared_cost_policies(
    auth: BillingReadAuth, db: DbDep, active_only: Annotated[bool, Query()] = False
) -> SharedCostPolicyList:
    stmt = select(SharedCostPolicy).where(SharedCostPolicy.workspace_id == auth[0].id)
    if active_only:
        stmt = stmt.where(SharedCostPolicy.is_active.is_(True))
    policies = list((await db.execute(stmt.order_by(SharedCostPolicy.created_at.desc()))).scalars())
    return SharedCostPolicyList(
        items=[SharedCostPolicyResponse.model_validate(p) for p in policies], total=len(policies)
    )


@router.get("/shared-cost-policies/{policy_id}", response_model=SharedCostPolicyResponse)
async def get_shared_cost_policy(
    policy_id: uuid.UUID, auth: BillingReadAuth, db: DbDep
) -> SharedCostPolicyResponse:
    return SharedCostPolicyResponse.model_validate(await _owned_policy(db, auth[0], policy_id))


@router.put("/shared-cost-policies/{policy_id}", response_model=SharedCostPolicyResponse)
async def update_shared_cost_policy(
    policy_id: uuid.UUID, body: SharedCostPolicyUpdate, auth: OrgAdminAuth, db: DbDep
) -> SharedCostPolicyResponse:
    workspace: Workspace = auth[0]
    policy = await _owned_policy(db, workspace, policy_id)
    formula = body.formula_type or policy.formula_type
    allocations = (
        [a.model_dump(mode="json") for a in body.allocations]
        if body.allocations is not None
        else policy.allocations
    )
    try:
        await validate_shared_cost_allocations(db, workspace.id, formula, allocations)
    except ValueError as exc:
        raise _bad(exc) from exc
    before = {
        "name": policy.name,
        "formula_type": policy.formula_type,
        "allocations": policy.allocations,
    }
    if body.name is not None:
        policy.name = body.name
    if body.description is not None:
        policy.description = body.description
    policy.formula_type = formula
    policy.allocations = allocations
    if body.is_active is not None:
        policy.is_active = body.is_active
    policy.updated_at = datetime.now(UTC)
    await _audit(
        db,
        auth,
        "billing.shared_cost_policy.updated",
        "shared_cost_policy",
        policy.id,
        before=before,
        after={
            "name": policy.name,
            "formula_type": policy.formula_type,
            "allocations": policy.allocations,
        },
    )
    await db.commit()
    await db.refresh(policy)
    return SharedCostPolicyResponse.model_validate(policy)


@router.delete("/shared-cost-policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shared_cost_policy(policy_id: uuid.UUID, auth: OrgAdminAuth, db: DbDep) -> None:
    """Delete a policy and its applied allocations."""
    policy = await _owned_policy(db, auth[0], policy_id)
    await _audit(
        db,
        auth,
        "billing.shared_cost_policy.deleted",
        "shared_cost_policy",
        policy.id,
        before={"name": policy.name},
    )
    await db.delete(policy)
    await db.commit()


@router.post(
    "/shared-cost-policies/{policy_id}/allocate", response_model=SharedCostAllocationResult
)
async def allocate_shared_cost(
    policy_id: uuid.UUID, body: dict[str, Any], auth: BillingReadAuth, db: DbDep
) -> SharedCostAllocationResult:
    """Preview how ``pool_usd`` splits under this policy (nothing is saved)."""
    await _owned_policy(db, auth[0], policy_id)
    try:
        pool_usd = Decimal(str(body.get("pool_usd")))
        if pool_usd <= 0:
            raise ValueError
    except (ArithmeticError, ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="pool_usd must be a positive decimal number",
        ) from exc
    return SharedCostAllocationResult(
        **await compute_shared_cost_allocation(db, policy_id, pool_usd)
    )


@router.post("/shared-cost-policies/{policy_id}/apply", response_model=CostAllocationList)
async def apply_shared_cost(
    policy_id: uuid.UUID, body: SharedCostApply, auth: OrgAdminAuth, db: DbDep
) -> CostAllocationList:
    """Split a pool (e.g. a platform or contract cost) across cost centers for a month
    and save it. The amounts appear in the cost-center chargeback report. Applying the
    same policy to the same month again replaces the earlier split."""
    workspace: Workspace = auth[0]
    policy = await _owned_policy(db, workspace, policy_id)
    if not policy.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Policy is inactive")
    if not policy.allocations:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Policy has no allocation targets",
        )
    try:
        await validate_shared_cost_allocations(
            db, workspace.id, policy.formula_type, policy.allocations
        )
    except ValueError as exc:
        raise _bad(exc) from exc
    _, email = _actor(auth)
    rows = await apply_shared_cost_policy(db, policy, body.period, body.pool_usd, email)
    await _audit(
        db,
        auth,
        "billing.shared_cost.applied",
        "shared_cost_policy",
        policy.id,
        after={"period": body.period, "pool_usd": str(body.pool_usd), "lines": len(rows)},
    )
    await db.commit()
    return CostAllocationList(
        items=[CostAllocationResponse.model_validate(r) for r in rows],
        total_usd=sum((r.amount_usd for r in rows), Decimal(0)),
    )


@router.get("/cost-allocations", response_model=CostAllocationList)
async def list_cost_allocations(
    auth: BillingReadAuth,
    db: DbDep,
    period: Annotated[str | None, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")] = None,
    policy_id: Annotated[uuid.UUID | None, Query()] = None,
) -> CostAllocationList:
    stmt = select(CostAllocation).where(CostAllocation.workspace_id == auth[0].id)
    if period:
        stmt = stmt.where(CostAllocation.period == period)
    if policy_id:
        stmt = stmt.where(CostAllocation.policy_id == policy_id)
    rows = list(
        (
            await db.execute(stmt.order_by(CostAllocation.period.desc(), CostAllocation.label))
        ).scalars()
    )
    return CostAllocationList(
        items=[CostAllocationResponse.model_validate(r) for r in rows],
        total_usd=sum((r.amount_usd for r in rows), Decimal(0)),
    )


@router.delete("/cost-allocations/{allocation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cost_allocation(allocation_id: uuid.UUID, auth: OrgAdminAuth, db: DbDep) -> None:
    row = (
        await db.execute(
            select(CostAllocation).where(
                CostAllocation.id == allocation_id, CostAllocation.workspace_id == auth[0].id
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Allocation not found")
    await _audit(
        db,
        auth,
        "billing.shared_cost.allocation_deleted",
        "cost_allocation",
        row.id,
        before={"period": row.period, "label": row.label, "amount_usd": str(row.amount_usd)},
    )
    await db.delete(row)
    await db.commit()


# ── Signing key ───────────────────────────────────────────────────────────────


@router.get("/signing-key", response_model=BillingSigningKey)
async def get_signing_key(auth: OrgAdminAuth) -> BillingSigningKey:
    """This workspace's current billing signing key, to verify snapshots and signed
    exports offline: hex HMAC-SHA256 over canonical JSON (sorted keys) of the payload
    without ``signature`` and ``signing_key_id``."""
    workspace: Workspace = auth[0]
    version = int(workspace.billing_signing_version or 1)
    return BillingSigningKey(
        workspace_id=workspace.id,
        signing_key_id=billing_signing.key_id(version),
        key=billing_signing.workspace_billing_key(workspace.id, version),
    )


@router.post("/signing-key/rotate", response_model=BillingSigningKey)
async def rotate_signing_key(auth: OrgAdminAuth, db: DbDep) -> BillingSigningKey:
    """Start signing with a new key. Existing signatures still verify by key id."""
    workspace: Workspace = auth[0]
    ws = await db.get(Workspace, workspace.id, with_for_update=True)
    assert ws is not None
    ws.billing_signing_version = int(ws.billing_signing_version or 1) + 1
    await _audit(
        db,
        auth,
        "billing.signing_key.rotated",
        "workspace",
        ws.id,
        after={"signing_key_id": billing_signing.key_id(ws.billing_signing_version)},
    )
    await db.commit()
    return BillingSigningKey(
        workspace_id=ws.id,
        signing_key_id=billing_signing.key_id(ws.billing_signing_version),
        key=billing_signing.workspace_billing_key(ws.id, ws.billing_signing_version),
    )


@router.post("/verify", response_model=BillingVerifyResult)
async def verify_signature(
    body: BillingVerifyRequest, auth: BillingReadAuth
) -> BillingVerifyResult:
    """Check a snapshot's or signed export's signature against this workspace's keys.

    For a signed export, send the downloaded JSON without ``signature`` and
    ``signing_key_id`` as ``payload``, and those two fields alongside.
    """
    payload = {k: v for k, v in body.payload.items() if k not in ("signature", "signing_key_id")}
    valid = billing_signing.verify(payload, body.signature, auth[0].id, body.signing_key_id)
    return BillingVerifyResult(valid=valid, signing_key_id=body.signing_key_id)
