"""
Billing CRUD + reconciliation + export endpoints.

Prefix: /billing
Auth: Bearer API key (workspace-scoped)

Endpoints
---------
POST   /billing/periods                    Create a billing period
GET    /billing/periods                    List periods (optional ?status=)
GET    /billing/periods/{id}               Single period
POST   /billing/periods/{id}/close         Close + sign
GET    /billing/periods/{id}/reconciliation Run reconciliation check
GET    /billing/periods/{id}/breakdown     Hierarchical breakdown by app/user
GET    /billing/periods/{id}/export        Export CSV or signed JSON
POST   /billing/chargeback-rules           Create a chargeback rule
GET    /billing/chargeback-rules           List chargeback rules
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
from runledger_api.models.billing import BillingPeriod, ChargebackRule
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.billing import (
    BillingPeriodCreate,
    BillingPeriodList,
    BillingPeriodResponse,
    ChargebackRuleCreate,
    ChargebackRuleList,
    ChargebackRuleResponse,
    PeriodBreakdown,
    ReconciliationResult,
    UsageSnapshotResponse,
)
from runledger_api.services.billing import (
    close_billing_period,
    export_csv,
    export_signed_json,
    get_period_breakdown,
    run_reconciliation,
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
    )

    return BillingPeriodResponse(
        id=str(period.id),
        period_start=period.period_start,
        period_end=period.period_end,
        status=period.status,
        total_cost_usd=period.total_cost_usd,
        snapshot_hash=period.snapshot_hash,
        closed_at=period.closed_at,
        created_at=period.created_at,
    )


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
        items=[
            BillingPeriodResponse(
                id=str(p.id),
                period_start=p.period_start,
                period_end=p.period_end,
                status=p.status,
                total_cost_usd=p.total_cost_usd,
                snapshot_hash=p.snapshot_hash,
                closed_at=p.closed_at,
                created_at=p.created_at,
            )
            for p in periods
        ]
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

    return BillingPeriodResponse(
        id=str(period.id),
        period_start=period.period_start,
        period_end=period.period_end,
        status=period.status,
        total_cost_usd=period.total_cost_usd,
        snapshot_hash=period.snapshot_hash,
        closed_at=period.closed_at,
        created_at=period.created_at,
    )


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


# ── GET /billing/periods/{id}/reconciliation ──────────────────────────────────


@router.get("/periods/{period_id}/reconciliation", response_model=ReconciliationResult)
async def get_reconciliation(
    period_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReconciliationResult:
    workspace: Workspace = auth[0]
    """Run a reconciliation check for the billing period."""
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
    format: Annotated[str, Query(pattern="^(csv|signed_json)$")] = "csv",
) -> Response:
    workspace: Workspace = auth[0]
    """Export billing period data as CSV or signed JSON."""
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
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)

    log.info(
        "chargeback_rule_created",
        rule_id=str(rule.id),
        workspace_id=str(workspace.id),
        allocation_type=rule.allocation_type,
        dimension=rule.dimension,
        weight=str(rule.weight),
    )

    return ChargebackRuleResponse(
        id=str(rule.id),
        allocation_type=rule.allocation_type,
        dimension=rule.dimension,
        weight=rule.weight,
        created_at=rule.created_at,
    )


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
        items=[
            ChargebackRuleResponse(
                id=str(r.id),
                allocation_type=r.allocation_type,
                dimension=r.dimension,
                weight=r.weight,
                created_at=r.created_at,
            )
            for r in rules
        ]
    )
