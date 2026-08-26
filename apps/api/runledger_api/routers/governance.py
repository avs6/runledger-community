"""Governance evidence and audit-pack endpoints."""

from __future__ import annotations

import csv
import io
import json
from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import require_workspace_admin
from runledger_api.core.ratelimit import analytics_rate_limit
from runledger_api.models.alerts import AlertFiring
from runledger_api.models.approvals import Approval
from runledger_api.models.budgets import Budget, BudgetBreach
from runledger_api.models.events import ProviderCall, ToolCall
from runledger_api.models.ledger import CapturePolicy, CapturePolicyScope
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.governance import (
    GovernanceApprovalRecord,
    GovernanceAuditPack,
    GovernanceAuditSummary,
    GovernanceBudgetAlert,
    GovernanceCapturePolicy,
    GovernanceModelUsage,
    GovernancePolicyAction,
)

router = APIRouter(
    prefix="/governance",
    tags=["governance"],
    dependencies=[Depends(analytics_rate_limit)],
)

DbDep = Annotated[AsyncSession, Depends(get_db)]
AdminDep = Annotated[tuple[Any, ...], Depends(require_workspace_admin)]


def _range_bounds(
    from_date: str | None, to_date: str | None
) -> tuple[datetime, datetime, str, str]:
    today = datetime.now(UTC).date()
    start_day = date.fromisoformat(from_date) if from_date else today.replace(day=1)
    end_day = date.fromisoformat(to_date) if to_date else today
    start = datetime.combine(start_day, time.min, tzinfo=UTC)
    end = datetime.combine(end_day, time.max, tzinfo=UTC)
    return start, end, start_day.isoformat(), end_day.isoformat()


async def _build_pack(
    db: AsyncSession,
    workspace: Workspace,
    from_date: str | None,
    to_date: str | None,
    user_id: str | None = None,
    access_group_id: str | None = None,
    api_key_id: str | None = None,
) -> GovernanceAuditPack:
    start, end, period_from, period_to = _range_bounds(from_date, to_date)

    import uuid as _uuid

    identity_user_ids: list[str] | None = None
    identity_emails: list[str] | None = None
    if access_group_id:
        from runledger_api.models.access_groups import AccessGroupMember

        member_rows = (
            (
                await db.execute(
                    select(AccessGroupMember.user_id).where(
                        AccessGroupMember.group_id == _uuid.UUID(access_group_id)
                    )
                )
            )
            .scalars()
            .all()
        )
        identity_user_ids = [str(uid) for uid in member_rows]
    elif user_id:
        identity_user_ids = [user_id]
    if identity_user_ids is not None:
        from runledger_api.models.tenant import User as UserModel

        identity_emails = list(
            (
                await db.execute(
                    select(UserModel.email).where(
                        UserModel.id.in_([_uuid.UUID(uid) for uid in identity_user_ids])
                    )
                )
            )
            .scalars()
            .all()
        )

    _provider_base = select(ProviderCall).where(
        ProviderCall.workspace_id == workspace.id,
        ProviderCall.created_at >= start,
        ProviderCall.created_at <= end,
    )
    summary_q = select(
        func.count(ProviderCall.id),
        func.coalesce(func.sum(ProviderCall.cost_usd), 0),
        func.count(distinct(ProviderCall.model)),
        func.count(distinct(ProviderCall.end_user_id)),
    ).where(
        ProviderCall.workspace_id == workspace.id,
        ProviderCall.created_at >= start,
        ProviderCall.created_at <= end,
    )
    if identity_user_ids is not None:
        summary_q = summary_q.where(ProviderCall.end_user_id.in_(identity_user_ids))
    if api_key_id:
        summary_q = summary_q.where(ProviderCall.api_key_id == api_key_id)
    summary_row = (await db.execute(summary_q)).one()

    approvals_q = select(func.count(Approval.id)).where(
        Approval.workspace_id == workspace.id,
        Approval.created_at >= start,
        Approval.created_at <= end,
    )
    if identity_emails is not None:
        if identity_emails:
            approvals_q = approvals_q.where(Approval.requested_by.in_(identity_emails))
        else:
            approvals_q = approvals_q.where(False)
    approvals_processed = int((await db.execute(approvals_q)).scalar() or 0)
    alerts_fired = int(
        (
            await db.execute(
                select(func.count(AlertFiring.id)).where(
                    AlertFiring.workspace_id == workspace.id,
                    AlertFiring.fired_at >= start,
                    AlertFiring.fired_at <= end,
                )
            )
        ).scalar()
        or 0
    )
    policy_count = int(
        (
            await db.execute(
                select(func.count(ToolCall.id)).where(
                    ToolCall.workspace_id == workspace.id,
                    ToolCall.created_at >= start,
                    ToolCall.created_at <= end,
                    ToolCall.status.in_(["blocked", "audited"]),
                )
            )
        ).scalar()
        or 0
    )

    model_q = select(
        ProviderCall.model,
        ProviderCall.provider,
        func.count(ProviderCall.id),
        func.coalesce(func.sum(ProviderCall.cost_usd), 0),
        func.min(ProviderCall.created_at),
        func.max(ProviderCall.created_at),
    ).where(
        ProviderCall.workspace_id == workspace.id,
        ProviderCall.created_at >= start,
        ProviderCall.created_at <= end,
    )
    if identity_user_ids is not None:
        model_q = model_q.where(ProviderCall.end_user_id.in_(identity_user_ids))
    if api_key_id:
        model_q = model_q.where(ProviderCall.api_key_id == api_key_id)
    model_rows = (
        await db.execute(
            model_q.group_by(ProviderCall.model, ProviderCall.provider).order_by(
                func.coalesce(func.sum(ProviderCall.cost_usd), 0).desc()
            )
        )
    ).all()

    from runledger_api.models.events import AgentRun

    enforcement_q = select(
        ToolCall.tool_name,
        ToolCall.status,
        func.count(ToolCall.id),
        func.max(ToolCall.created_at),
    ).where(
        ToolCall.workspace_id == workspace.id,
        ToolCall.created_at >= start,
        ToolCall.created_at <= end,
        ToolCall.status.in_(["blocked", "audited"]),
    )
    if identity_user_ids is not None or api_key_id:
        enforcement_q = enforcement_q.join(AgentRun, AgentRun.id == ToolCall.run_id)
        if identity_user_ids is not None:
            enforcement_q = enforcement_q.where(AgentRun.end_user_id.in_(identity_user_ids))
        if api_key_id:
            enforcement_q = enforcement_q.where(AgentRun.api_key_id == api_key_id)
    enforcement_rows = (
        await db.execute(
            enforcement_q.group_by(ToolCall.tool_name, ToolCall.status).order_by(
                func.max(ToolCall.created_at).desc()
            )
        )
    ).all()

    approval_q = select(Approval).where(
        Approval.workspace_id == workspace.id,
        Approval.created_at >= start,
        Approval.created_at <= end,
    )
    if identity_emails is not None:
        if identity_emails:
            approval_q = approval_q.where(Approval.requested_by.in_(identity_emails))
        else:
            approval_q = approval_q.where(False)
    approval_rows = (
        (await db.execute(approval_q.order_by(Approval.created_at.desc()).limit(100)))
        .scalars()
        .all()
    )

    workspace_capture = (
        await db.execute(select(CapturePolicy).where(CapturePolicy.workspace_id == workspace.id))
    ).scalar_one_or_none()
    scope_rows = (
        (
            await db.execute(
                select(CapturePolicyScope)
                .where(CapturePolicyScope.workspace_id == workspace.id)
                .order_by(CapturePolicyScope.scope_type.asc(), CapturePolicyScope.scope_id.asc())
            )
        )
        .scalars()
        .all()
    )

    breach_rows = (
        await db.execute(
            select(BudgetBreach, Budget)
            .join(Budget, Budget.id == BudgetBreach.budget_id)
            .where(
                Budget.workspace_id == workspace.id,
                BudgetBreach.occurred_at >= start,
                BudgetBreach.occurred_at <= end,
            )
            .order_by(BudgetBreach.occurred_at.desc())
            .limit(100)
        )
    ).all()

    data_capture_policies: list[GovernanceCapturePolicy] = []
    if workspace_capture is not None:
        data_capture_policies.append(
            GovernanceCapturePolicy(
                scope="workspace.default",
                privacy_mode=workspace_capture.privacy_mode,
                retention_days=None,
            )
        )
    data_capture_policies.extend(
        GovernanceCapturePolicy(
            scope=f"{scope.scope_type}:{scope.scope_id}",
            privacy_mode=scope.privacy_mode,
            retention_days=None,
        )
        for scope in scope_rows
    )

    return GovernanceAuditPack(
        generated_at=datetime.now(UTC),
        period_from=period_from,
        period_to=period_to,
        summary=GovernanceAuditSummary(
            total_requests=int(summary_row[0] or 0),
            total_cost_usd=summary_row[1] or Decimal("0"),
            models_used=int(summary_row[2] or 0),
            users_active=int(summary_row[3] or 0),
            policies_enforced=policy_count,
            approvals_processed=approvals_processed,
            alerts_fired=alerts_fired,
        ),
        model_usage=[
            GovernanceModelUsage(
                model=row[0],
                provider=row[1],
                request_count=int(row[2] or 0),
                cost_usd=row[3] or Decimal("0"),
                first_used=row[4],
                last_used=row[5],
            )
            for row in model_rows
        ],
        policy_enforcements=[
            GovernancePolicyAction(
                policy_type=row[0],
                action="block" if row[1] == "blocked" else "audit",
                count=int(row[2] or 0),
                last_triggered=row[3],
            )
            for row in enforcement_rows
        ],
        approvals=[
            GovernanceApprovalRecord(
                request_type=row.request_type,
                status=row.status,
                requested_by=row.requested_by,
                decided_by=row.decided_by,
                created_at=row.created_at,
            )
            for row in approval_rows
        ],
        data_capture_policies=data_capture_policies,
        budget_alerts=[
            GovernanceBudgetAlert(
                budget_name=f"{budget.scope_type}:{budget.scope_id or 'workspace'}",
                threshold_pct=int(
                    round(
                        float((breach.spend_at_breach_usd or Decimal("0")) / budget.limit_usd * 100)
                    )
                    if budget.limit_usd
                    else 100
                ),
                triggered_at=breach.occurred_at,
                current_spend_usd=breach.spend_at_breach_usd or Decimal("0"),
                limit_usd=budget.limit_usd,
            )
            for breach, budget in breach_rows
        ],
    )


@router.get("/audit-pack", response_model=GovernanceAuditPack)
async def get_governance_audit_pack(
    auth: AdminDep,
    db: DbDep,
    from_date: str | None = Query(None, alias="from"),
    to_date: str | None = Query(None, alias="to"),
    user_id: str | None = Query(None),
    access_group_id: str | None = Query(None),
    api_key_id: str | None = Query(None),
) -> GovernanceAuditPack:
    workspace: Workspace = auth[0]
    return await _build_pack(
        db,
        workspace,
        from_date,
        to_date,
        user_id=user_id,
        access_group_id=access_group_id,
        api_key_id=api_key_id,
    )


@router.get("/audit-pack/export")
async def export_governance_audit_pack(
    auth: AdminDep,
    db: DbDep,
    format: str = Query("json", pattern="^(csv|json)$"),
    from_date: str | None = Query(None, alias="from"),
    to_date: str | None = Query(None, alias="to"),
    user_id: str | None = Query(None),
    access_group_id: str | None = Query(None),
    api_key_id: str | None = Query(None),
) -> StreamingResponse:
    workspace: Workspace = auth[0]
    pack = await _build_pack(
        db,
        workspace,
        from_date,
        to_date,
        user_id=user_id,
        access_group_id=access_group_id,
        api_key_id=api_key_id,
    )
    if format == "json":
        body = json.dumps(pack.model_dump(mode="json"), indent=2, default=str)
        return StreamingResponse(
            iter([body]),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=governance_audit_pack.json"},
        )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["section", "key", "value"])
    for key, value in pack.summary.model_dump(mode="json").items():
        writer.writerow(["summary", key, value])
    for item in pack.model_usage:
        writer.writerow(
            ["model_usage", item.model, json.dumps(item.model_dump(mode="json"), default=str)]
        )
    for item in pack.policy_enforcements:
        writer.writerow(
            [
                "policy_enforcements",
                item.policy_type,
                json.dumps(item.model_dump(mode="json"), default=str),
            ]
        )
    for item in pack.approvals:
        writer.writerow(
            ["approvals", item.request_type, json.dumps(item.model_dump(mode="json"), default=str)]
        )
    for item in pack.data_capture_policies:
        writer.writerow(
            [
                "data_capture_policies",
                item.scope,
                json.dumps(item.model_dump(mode="json"), default=str),
            ]
        )
    for item in pack.budget_alerts:
        writer.writerow(
            [
                "budget_alerts",
                item.budget_name,
                json.dumps(item.model_dump(mode="json"), default=str),
            ]
        )
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=governance_audit_pack.csv"},
    )
