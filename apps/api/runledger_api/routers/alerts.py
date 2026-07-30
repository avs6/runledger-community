"""
Alert Rules API.

Prefix: /alerts
Auth: Bearer API key (workspace-scoped)

Endpoints
---------
POST   /alerts/rules          Create alert rule
GET    /alerts/rules          List alert rules
PUT    /alerts/rules/{id}     Update / toggle rule
DELETE /alerts/rules/{id}     Delete rule
GET    /alerts/history        Recent alert firings
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import require_org_admin
from runledger_api.core.ratelimit import management_rate_limit
from runledger_api.models.alerts import AlertFiring, AlertRule
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.alerts import (
    AlertFiringResponse,
    AlertHistoryList,
    AlertRuleCreate,
    AlertRuleList,
    AlertRuleResponse,
    AlertRuleUpdate,
)

router = APIRouter(
    prefix="/alerts",
    tags=["alerts"],
    dependencies=[Depends(management_rate_limit)],
)

DbDep = Annotated[AsyncSession, Depends(get_db)]
OrgAdminDep = Annotated[tuple, Depends(require_org_admin)]


# ── Create rule ────────────────────────────────────────────────────────────────


@router.post("/rules", response_model=AlertRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_alert_rule(
    body: AlertRuleCreate,
    auth: OrgAdminDep,
    db: DbDep,
) -> AlertRuleResponse:
    workspace: Workspace = auth[0]
    rule = AlertRule(
        workspace_id=workspace.id,
        name=body.name,
        metric=body.metric,
        operator=body.operator,
        threshold=body.threshold,
        window_minutes=body.window_minutes,
        channel_id=body.channel_id,
        email_enabled=body.email_enabled,
    )
    db.add(rule)
    await db.flush()
    await db.commit()
    await db.refresh(rule)
    return AlertRuleResponse.model_validate(rule)


# ── List rules ─────────────────────────────────────────────────────────────────


@router.get("/rules", response_model=AlertRuleList)
async def list_alert_rules(
    auth: OrgAdminDep,
    db: DbDep,
    include_inactive: bool = Query(False),
) -> AlertRuleList:
    workspace: Workspace = auth[0]
    stmt = select(AlertRule).where(AlertRule.workspace_id == workspace.id)
    if not include_inactive:
        stmt = stmt.where(AlertRule.is_active.is_(True))
    stmt = stmt.order_by(AlertRule.created_at.desc())
    result = await db.execute(stmt)
    rules = list(result.scalars().all())
    return AlertRuleList(items=[AlertRuleResponse.model_validate(r) for r in rules])


# ── Update / toggle rule ───────────────────────────────────────────────────────


@router.put("/rules/{rule_id}", response_model=AlertRuleResponse)
async def update_alert_rule(
    rule_id: uuid.UUID,
    body: AlertRuleUpdate,
    auth: OrgAdminDep,
    db: DbDep,
) -> AlertRuleResponse:
    workspace: Workspace = auth[0]
    rule = await db.get(AlertRule, rule_id)
    if rule is None or rule.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Alert rule not found")

    if body.name is not None:
        rule.name = body.name
    if body.threshold is not None:
        rule.threshold = body.threshold
    if body.window_minutes is not None:
        rule.window_minutes = body.window_minutes
    if body.is_active is not None:
        rule.is_active = body.is_active
    if "channel_id" in body.model_fields_set:
        rule.channel_id = body.channel_id
    if body.email_enabled is not None:
        rule.email_enabled = body.email_enabled

    await db.commit()
    await db.refresh(rule)
    return AlertRuleResponse.model_validate(rule)


# ── Delete rule ────────────────────────────────────────────────────────────────


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert_rule(
    rule_id: uuid.UUID,
    auth: OrgAdminDep,
    db: DbDep,
) -> None:
    workspace: Workspace = auth[0]
    rule = await db.get(AlertRule, rule_id)
    if rule is None or rule.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Alert rule not found")
    await db.delete(rule)
    await db.commit()


# ── Alert history ──────────────────────────────────────────────────────────────


@router.get("/history", response_model=AlertHistoryList)
async def list_alert_history(
    auth: OrgAdminDep,
    db: DbDep,
    limit: int = Query(50, ge=1, le=200),
) -> AlertHistoryList:
    workspace: Workspace = auth[0]
    # Fetch firings ordered newest-first
    stmt = (
        select(AlertFiring, AlertRule.name.label("rule_name"))
        .join(AlertRule, AlertFiring.rule_id == AlertRule.id)
        .where(AlertFiring.workspace_id == workspace.id)
        .order_by(AlertFiring.fired_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.all()

    items = [
        AlertFiringResponse(
            id=firing.id,
            rule_id=firing.rule_id,
            workspace_id=firing.workspace_id,
            fired_at=firing.fired_at,
            metric_value=firing.metric_value,
            resolved_at=firing.resolved_at,
            rule_name=rule_name,
        )
        for firing, rule_name in rows
    ]
    return AlertHistoryList(items=items)
