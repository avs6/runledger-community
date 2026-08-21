"""
Approvals & Policy Workflow API.

Prefix: /approvals
Auth: Bearer API key (workspace-scoped)

Endpoints
---------
POST   /approvals                   Submit an approval request
GET    /approvals                   List approvals (filter by status/type)
GET    /approvals/summary           Count by status
GET    /approvals/{id}              Get single approval
PUT    /approvals/{id}/approve      Approve a pending request
PUT    /approvals/{id}/deny         Deny a pending request
DELETE /approvals/{id}              Cancel a pending request

Request types
-------------
budget_increase       Raise a budget limit_usd
prompt_promote        Promote a prompt version to production
tool_allow            Allow a privileged tool in the registry
capture_policy_full   Enable FULL payload capture mode
shadow_routing        Enable shadow routing to an external provider
"""

from __future__ import annotations

import fnmatch
import uuid
from datetime import UTC, datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.config import settings
from runledger_api.core.db import get_db
from runledger_api.core.deps import (
    get_current_api_key,
    get_current_workspace,
    require_workspace_admin,
)
from runledger_api.core.ratelimit import analytics_rate_limit, management_rate_limit
from runledger_api.models.approvals import Approval, AutoApprovalPolicy
from runledger_api.models.tenant import ApiKey, Workspace
from runledger_api.schemas.approvals import (
    AutoApprovalPolicyCreate,
    AutoApprovalPolicyList,
    AutoApprovalPolicyResponse,
    AutoApprovalPolicyUpdate,
    ApprovalCreate,
    ApprovalDecision,
    ApprovalList,
    ApprovalResponse,
    ApprovalSummary,
)
from runledger_api.services.audit import emit_audit_event
from runledger_api.services.email import send_approval_decision_email, send_approval_request_email
from runledger_api.services.email_utils import get_workspace_admin_users
from runledger_api.services import kafka_export

router = APIRouter(prefix="/approvals", tags=["approvals"])
log = structlog.get_logger()

WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]
WorkspaceAdminDep = Annotated[
    tuple[Workspace, object, object | None], Depends(require_workspace_admin)
]
ApiKeyDep = Annotated[ApiKey, Depends(get_current_api_key)]
DbDep = Annotated[AsyncSession, Depends(get_db)]

_VALID_STATUSES = {"pending", "approved", "denied", "cancelled"}
_VALID_TYPES = {
    "budget_increase",
    "prompt_promote",
    "tool_allow",
    "capture_policy_full",
    "shadow_routing",
    "premium_model_use",
    "external_mcp_tool",
    "long_agent_session",
    "sensitive_export",
    "route_policy_change",
    "chargeback_rule",
}


def _auto_policy_to_response(policy: AutoApprovalPolicy) -> AutoApprovalPolicyResponse:
    return AutoApprovalPolicyResponse.model_validate(policy)


def _auto_policy_matches(
    policy: AutoApprovalPolicy,
    request_type: str,
    request: dict[str, object],
    requested_by: str | None,
) -> bool:
    if policy.request_type != request_type:
        return False

    raw = policy.condition.strip()
    if not raw:
        return False
    if ":" not in raw:
        return False

    field, pattern = raw.split(":", 1)
    field = field.strip().lower()
    pattern = pattern.strip()
    if not pattern:
        return False

    if field == "user":
        candidate = requested_by or ""
        return fnmatch.fnmatch(candidate.lower(), pattern.lower())

    candidate = request.get(field)
    if candidate is None:
        return False
    return fnmatch.fnmatch(str(candidate).lower(), pattern.lower())


def _requester_label(api_key: ApiKey) -> str | None:
    """Best-effort identifier of who made the request."""
    return api_key.created_by  # email for session keys, None for raw API keys


async def _notify_approval_request(
    db: AsyncSession,
    workspace: Workspace,
    approval: Approval,
    reason: str | None,
) -> None:
    """Fire-and-forget email to workspace admins when a new approval is requested."""
    try:
        admins = await get_workspace_admin_users(db, workspace.id)
        ws_name = getattr(workspace, "name", str(workspace.id))
        approval_url = f"{settings.app_base_url}/approvals"
        for u in admins:
            await send_approval_request_email(
                to_email=u.email,
                full_name=u.full_name,
                request_type=approval.request_type,
                reason=reason,
                requester=approval.requested_by,
                workspace_name=ws_name,
                approval_url=approval_url,
            )
    except Exception:
        log.warning("approval_email_request_failed", approval_id=str(approval.id))


async def _notify_approval_decision(workspace: Workspace, approval: Approval) -> None:
    """Fire-and-forget email to the requester when an approval is decided."""
    requester_email = approval.requested_by
    if not requester_email or "@" not in requester_email:
        return
    try:
        ws_name = getattr(workspace, "name", str(workspace.id))
        await send_approval_decision_email(
            to_email=requester_email,
            request_type=approval.request_type,
            decision=approval.status,
            decision_note=approval.decision_note,
            decided_by=approval.decided_by,
            workspace_name=ws_name,
        )
    except Exception:
        log.warning("approval_email_decision_failed", approval_id=str(approval.id))


async def _notify_slack(workspace: Workspace, approval: Approval) -> None:
    """Fire-and-forget Slack notification when a new approval is requested."""
    webhook_url: str | None = getattr(workspace, "slack_webhook_url", None)
    if not webhook_url:
        return
    try:
        from runledger_api.services.notifications import send_slack_message  # noqa: PLC0415

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*Approval requested* — `{approval.request_type}`\n"
                        f"Requested by: {approval.requested_by or 'API key'}\n"
                        f"Workspace: `{workspace.id}`\n"
                        f"Approval ID: `{approval.id}`"
                    ),
                },
            }
        ]
        await send_slack_message(
            webhook_url, blocks, f"Approval requested: {approval.request_type}"
        )
    except Exception:
        log.warning("approval_slack_notify_failed", approval_id=str(approval.id))


# ── Create approval request ────────────────────────────────────────────────────


@router.post(
    "",
    response_model=ApprovalResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(management_rate_limit)],
)
async def create_approval(
    body: ApprovalCreate,
    workspace: WorkspaceDep,
    api_key: ApiKeyDep,
    db: DbDep,
) -> ApprovalResponse:
    """Submit an approval request for a sensitive action."""
    request_data = dict(body.request)
    if body.reason:
        request_data["_reason"] = body.reason
    requested_by = _requester_label(api_key)

    auto_policies = (
        await db.execute(
            select(AutoApprovalPolicy)
            .where(
                AutoApprovalPolicy.workspace_id == workspace.id,
                AutoApprovalPolicy.request_type == body.request_type,
            )
            .order_by(AutoApprovalPolicy.created_at.asc())
        )
    ).scalars().all()
    matched_policy = next(
        (
            policy
            for policy in auto_policies
            if _auto_policy_matches(policy, body.request_type, request_data, requested_by)
        ),
        None,
    )

    approval = Approval(
        workspace_id=workspace.id,
        request_type=body.request_type,
        request=request_data,
        status="approved" if matched_policy else "pending",
        requested_by=requested_by,
        decided_by="auto-policy" if matched_policy else None,
        decided_at=datetime.now(UTC) if matched_policy else None,
        decision_note=(
            f"Auto-approved by policy: {matched_policy.condition}" if matched_policy else None
        ),
    )
    db.add(approval)
    await db.flush()
    await db.commit()
    await db.refresh(approval)

    log.info(
        "approval_created",
        workspace_id=str(workspace.id),
        request_type=body.request_type,
        approval_id=str(approval.id),
        requested_by=approval.requested_by,
    )
    try:
        await kafka_export.publish_event(
            db,
            workspace_id=workspace.id,
            event_type="approval.requested",
            payload={
                "run_id": str(approval.id),
                "approval_id": str(approval.id),
                "request_type": approval.request_type,
                "status": approval.status,
                "requested_by": approval.requested_by,
                "reason": body.reason,
                "requested_at": approval.created_at.isoformat() if approval.created_at else None,
                "idempotency_key": f"approval-requested:{approval.id}",
                "source": "runledger.approvals",
                "event_summary": f"Approval requested: {approval.request_type}",
            },
        )
    except Exception:
        log.exception("kafka_export.approval_requested_failed", approval_id=str(approval.id))
    if matched_policy:
        await emit_audit_event(
            db,
            workspace.id,
            "approval.auto_approved",
            target_type="approval",
            target_id=str(approval.id),
            after={
                "request_type": approval.request_type,
                "policy_id": str(matched_policy.id),
                "policy_condition": matched_policy.condition,
            },
        )
        try:
            await kafka_export.publish_event(
                db,
                workspace_id=workspace.id,
                event_type="approval.decided",
                payload={
                    "run_id": str(approval.id),
                    "approval_id": str(approval.id),
                    "request_type": approval.request_type,
                    "status": approval.status,
                    "decided_by": approval.decided_by,
                    "decision_note": approval.decision_note,
                    "decided_at": approval.decided_at.isoformat() if approval.decided_at else None,
                    "idempotency_key": f"approval-decided:{approval.id}:auto-approved",
                    "source": "runledger.approvals",
                    "event_summary": "Approval auto-approved",
                },
            )
        except Exception:
            log.exception("kafka_export.approval_auto_approved_failed", approval_id=str(approval.id))
        await _notify_approval_decision(workspace, approval)
    else:
        await _notify_slack(workspace, approval)
        await _notify_approval_request(db, workspace, approval, body.reason)
    return ApprovalResponse.model_validate(approval)


@router.get(
    "/auto-policies",
    response_model=AutoApprovalPolicyList,
    dependencies=[Depends(analytics_rate_limit)],
)
async def list_auto_approval_policies(
    auth: WorkspaceAdminDep,
    db: DbDep,
) -> AutoApprovalPolicyList:
    workspace = auth[0]
    items = (
        await db.execute(
            select(AutoApprovalPolicy)
            .where(AutoApprovalPolicy.workspace_id == workspace.id)
            .order_by(AutoApprovalPolicy.created_at.desc())
        )
    ).scalars().all()
    return AutoApprovalPolicyList(items=[_auto_policy_to_response(item) for item in items])


@router.post(
    "/auto-policies",
    response_model=AutoApprovalPolicyResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(management_rate_limit)],
)
async def create_auto_approval_policy(
    body: AutoApprovalPolicyCreate,
    auth: WorkspaceAdminDep,
    api_key: ApiKeyDep,
    db: DbDep,
) -> AutoApprovalPolicyResponse:
    workspace = auth[0]
    policy = AutoApprovalPolicy(
        workspace_id=workspace.id,
        request_type=body.request_type,
        condition=body.condition.strip(),
        created_by=_requester_label(api_key),
    )
    db.add(policy)
    await db.flush()
    await db.commit()
    await db.refresh(policy)
    await emit_audit_event(
        db,
        workspace.id,
        "approval_policy.created",
        target_type="auto_approval_policy",
        target_id=str(policy.id),
        after={"request_type": policy.request_type, "condition": policy.condition},
    )
    return _auto_policy_to_response(policy)


@router.put(
    "/auto-policies/{policy_id}",
    response_model=AutoApprovalPolicyResponse,
    dependencies=[Depends(management_rate_limit)],
)
async def update_auto_approval_policy(
    policy_id: uuid.UUID,
    body: AutoApprovalPolicyUpdate,
    auth: WorkspaceAdminDep,
    db: DbDep,
) -> AutoApprovalPolicyResponse:
    workspace = auth[0]
    policy = await db.get(AutoApprovalPolicy, policy_id)
    if policy is None or policy.workspace_id != workspace.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auto-approval policy not found")
    if body.request_type is not None:
        policy.request_type = body.request_type
    if body.condition is not None:
        policy.condition = body.condition.strip()
    await db.commit()
    await db.refresh(policy)
    await emit_audit_event(
        db,
        workspace.id,
        "approval_policy.updated",
        target_type="auto_approval_policy",
        target_id=str(policy.id),
        after={"request_type": policy.request_type, "condition": policy.condition},
    )
    return _auto_policy_to_response(policy)


@router.delete(
    "/auto-policies/{policy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(management_rate_limit)],
)
async def delete_auto_approval_policy(
    policy_id: uuid.UUID,
    auth: WorkspaceAdminDep,
    db: DbDep,
) -> None:
    workspace = auth[0]
    policy = await db.get(AutoApprovalPolicy, policy_id)
    if policy is None or policy.workspace_id != workspace.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auto-approval policy not found")
    await db.delete(policy)
    await db.commit()
    await emit_audit_event(
        db,
        workspace.id,
        "approval_policy.deleted",
        target_type="auto_approval_policy",
        target_id=str(policy_id),
        after={"request_type": policy.request_type, "condition": policy.condition},
    )


# ── List approvals ─────────────────────────────────────────────────────────────


@router.get("", response_model=ApprovalList, dependencies=[Depends(analytics_rate_limit)])
async def list_approvals(
    auth: WorkspaceAdminDep,
    db: DbDep,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    request_type: Annotated[str | None, Query()] = None,
    requested_by: Annotated[str | None, Query()] = None,
    access_group_id: Annotated[uuid.UUID | None, Query()] = None,
    api_key_prefix: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ApprovalList:
    """List approval requests for this workspace."""
    workspace = auth[0]
    stmt = select(Approval).where(Approval.workspace_id == workspace.id)

    if status_filter and status_filter in _VALID_STATUSES:
        stmt = stmt.where(Approval.status == status_filter)
    if request_type and request_type in _VALID_TYPES:
        stmt = stmt.where(Approval.request_type == request_type)
    if requested_by:
        stmt = stmt.where(Approval.requested_by.ilike(f"%{requested_by}%"))
    if api_key_prefix:
        api_key_rows = (
            await db.execute(
                select(ApiKey).where(
                    ApiKey.workspace_id == workspace.id,
                    ApiKey.key_prefix == api_key_prefix,
                )
            )
        ).scalars().all()
        emails = [k.created_by for k in api_key_rows if k.created_by]
        if emails:
            stmt = stmt.where(Approval.requested_by.in_(emails))
        else:
            stmt = stmt.where(False)
    if access_group_id:
        from runledger_api.models.access_groups import AccessGroupMember
        from runledger_api.models.tenant import User
        member_emails_result = await db.execute(
            select(User.email)
            .join(AccessGroupMember, AccessGroupMember.user_id == User.id)
            .where(AccessGroupMember.group_id == access_group_id)
        )
        member_emails = [e for e in member_emails_result.scalars().all() if e]
        if member_emails:
            stmt = stmt.where(Approval.requested_by.in_(member_emails))
        else:
            stmt = stmt.where(False)

    count_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = int(count_result.scalar() or 0)

    stmt = stmt.order_by(Approval.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    items = result.scalars().all()

    return ApprovalList(
        items=[ApprovalResponse.model_validate(a) for a in items],
        total=total,
    )


# ── Summary count by status ────────────────────────────────────────────────────


@router.get(
    "/summary",
    response_model=ApprovalSummary,
    dependencies=[Depends(analytics_rate_limit)],
)
async def approval_summary(
    auth: WorkspaceAdminDep,
    db: DbDep,
) -> ApprovalSummary:
    """Return counts of approvals grouped by status."""
    workspace = auth[0]
    result = await db.execute(
        select(Approval.status, func.count(Approval.id).label("cnt"))
        .where(Approval.workspace_id == workspace.id)
        .group_by(Approval.status)
    )
    counts = {row.status: int(row.cnt) for row in result.all()}
    return ApprovalSummary(
        pending=counts.get("pending", 0),
        approved=counts.get("approved", 0),
        denied=counts.get("denied", 0),
        cancelled=counts.get("cancelled", 0),
    )


# ── Get single approval ────────────────────────────────────────────────────────


@router.get(
    "/{approval_id}", response_model=ApprovalResponse, dependencies=[Depends(analytics_rate_limit)]
)
async def get_approval(
    approval_id: uuid.UUID,
    auth: WorkspaceAdminDep,
    db: DbDep,
) -> ApprovalResponse:
    """Get a single approval by ID."""
    workspace = auth[0]
    result = await db.execute(
        select(Approval).where(
            Approval.id == approval_id,
            Approval.workspace_id == workspace.id,
        )
    )
    approval = result.scalar_one_or_none()
    if approval is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval not found")
    return ApprovalResponse.model_validate(approval)


# ── Approve ────────────────────────────────────────────────────────────────────


@router.put(
    "/{approval_id}/approve",
    response_model=ApprovalResponse,
    dependencies=[Depends(management_rate_limit)],
)
async def approve_approval(
    approval_id: uuid.UUID,
    body: ApprovalDecision,
    auth: WorkspaceAdminDep,
    api_key: ApiKeyDep,
    db: DbDep,
) -> ApprovalResponse:
    """Approve a pending request. Requires workspace admin or higher."""
    workspace = auth[0]
    result = await db.execute(
        select(Approval).where(
            Approval.id == approval_id,
            Approval.workspace_id == workspace.id,
        )
    )
    approval = result.scalar_one_or_none()
    if approval is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval not found")
    if approval.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot approve an approval in '{approval.status}' status",
        )

    approval.status = "approved"
    approval.decided_by = _requester_label(api_key)
    approval.decided_at = datetime.now(UTC)
    approval.decision_note = body.note

    # Side-effects on the referenced resource
    if approval.request_type == "chargeback_rule":
        await _activate_chargeback_rule(db, approval)
    elif approval.request_type == "budget_increase":
        await _activate_budget_override(db, approval)

    await db.commit()
    await db.refresh(approval)

    log.info(
        "approval_approved",
        approval_id=str(approval.id),
        request_type=approval.request_type,
        decided_by=approval.decided_by,
    )
    await emit_audit_event(
        db,
        workspace.id,
        "approval.approved",
        target_type="approval",
        target_id=str(approval.id),
        after={"request_type": approval.request_type, "decided_by": approval.decided_by},
    )
    try:
        await kafka_export.publish_event(
            db,
            workspace_id=workspace.id,
            event_type="approval.decided",
            payload={
                "run_id": str(approval.id),
                "approval_id": str(approval.id),
                "request_type": approval.request_type,
                "status": approval.status,
                "decided_by": approval.decided_by,
                "decision_note": approval.decision_note,
                "decided_at": approval.decided_at.isoformat() if approval.decided_at else None,
                "idempotency_key": f"approval-decided:{approval.id}:{approval.status}",
                "source": "runledger.approvals",
                "event_summary": f"Approval {approval.status}",
            },
        )
    except Exception:
        log.exception("kafka_export.approval_decided_failed", approval_id=str(approval.id))
    await _notify_approval_decision(workspace, approval)
    return ApprovalResponse.model_validate(approval)


# ── Deny ───────────────────────────────────────────────────────────────────────


@router.put(
    "/{approval_id}/deny",
    response_model=ApprovalResponse,
    dependencies=[Depends(management_rate_limit)],
)
async def deny_approval(
    approval_id: uuid.UUID,
    body: ApprovalDecision,
    auth: WorkspaceAdminDep,
    api_key: ApiKeyDep,
    db: DbDep,
) -> ApprovalResponse:
    """Deny a pending request."""
    workspace = auth[0]
    result = await db.execute(
        select(Approval).where(
            Approval.id == approval_id,
            Approval.workspace_id == workspace.id,
        )
    )
    approval = result.scalar_one_or_none()
    if approval is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval not found")
    if approval.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot deny an approval in '{approval.status}' status",
        )

    approval.status = "denied"
    approval.decided_by = _requester_label(api_key)
    approval.decided_at = datetime.now(UTC)
    approval.decision_note = body.note

    # Side-effects on the referenced resource
    if approval.request_type == "chargeback_rule":
        await _deny_chargeback_rule(db, approval)
    elif approval.request_type == "budget_increase":
        await _deny_budget_override(db, approval)

    await db.commit()
    await db.refresh(approval)

    log.info(
        "approval_denied",
        approval_id=str(approval.id),
        request_type=approval.request_type,
        decided_by=approval.decided_by,
    )
    await emit_audit_event(
        db,
        workspace.id,
        "approval.denied",
        target_type="approval",
        target_id=str(approval.id),
        after={"request_type": approval.request_type, "decided_by": approval.decided_by},
    )
    try:
        await kafka_export.publish_event(
            db,
            workspace_id=workspace.id,
            event_type="approval.decided",
            payload={
                "run_id": str(approval.id),
                "approval_id": str(approval.id),
                "request_type": approval.request_type,
                "status": approval.status,
                "decided_by": approval.decided_by,
                "decision_note": approval.decision_note,
                "decided_at": approval.decided_at.isoformat() if approval.decided_at else None,
                "idempotency_key": f"approval-decided:{approval.id}:{approval.status}",
                "source": "runledger.approvals",
                "event_summary": f"Approval {approval.status}",
            },
        )
    except Exception:
        log.exception("kafka_export.approval_decided_failed", approval_id=str(approval.id))
    await _notify_approval_decision(workspace, approval)
    return ApprovalResponse.model_validate(approval)


# ── Cancel ─────────────────────────────────────────────────────────────────────


@router.delete(
    "/{approval_id}",
    response_model=ApprovalResponse,
    dependencies=[Depends(management_rate_limit)],
)
async def cancel_approval(
    approval_id: uuid.UUID,
    auth: WorkspaceAdminDep,
    db: DbDep,
) -> ApprovalResponse:
    """Cancel a pending approval request (by the requester or an admin)."""
    workspace = auth[0]
    result = await db.execute(
        select(Approval).where(
            Approval.id == approval_id,
            Approval.workspace_id == workspace.id,
        )
    )
    approval = result.scalar_one_or_none()
    if approval is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval not found")
    if approval.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot cancel an approval in '{approval.status}' status",
        )

    approval.status = "cancelled"
    if approval.request_type == "budget_increase":
        await _cancel_budget_override(db, approval)
    await db.commit()
    await db.refresh(approval)

    log.info("approval_cancelled", approval_id=str(approval.id))
    await emit_audit_event(
        db,
        workspace.id,
        "approval.cancelled",
        target_type="approval",
        target_id=str(approval.id),
        after={"request_type": approval.request_type},
    )
    return ApprovalResponse.model_validate(approval)


# ── Chargeback rule side-effects ───────────────────────────────────────────────


async def _activate_chargeback_rule(db: AsyncSession, approval: Approval) -> None:
    """Set chargeback rule status → 'active' when its approval is approved."""
    rule_id_str = approval.request.get("rule_id") if approval.request else None
    if not rule_id_str:
        return
    try:
        rule_id = uuid.UUID(rule_id_str)
    except ValueError:
        return
    from sqlalchemy import update as sa_update  # noqa: PLC0415

    from runledger_api.models.billing import ChargebackRule  # noqa: PLC0415

    await db.execute(
        sa_update(ChargebackRule)
        .where(
            ChargebackRule.id == rule_id,
            ChargebackRule.workspace_id == approval.workspace_id,
        )
        .values(status="active")
    )
    log.info("chargeback_rule_activated", rule_id=rule_id_str, approval_id=str(approval.id))


async def _deny_chargeback_rule(db: AsyncSession, approval: Approval) -> None:
    """Set chargeback rule status → 'denied' when its approval is denied."""
    rule_id_str = approval.request.get("rule_id") if approval.request else None
    if not rule_id_str:
        return
    try:
        rule_id = uuid.UUID(rule_id_str)
    except ValueError:
        return
    from sqlalchemy import update as sa_update  # noqa: PLC0415

    from runledger_api.models.billing import ChargebackRule  # noqa: PLC0415

    await db.execute(
        sa_update(ChargebackRule)
        .where(
            ChargebackRule.id == rule_id,
            ChargebackRule.workspace_id == approval.workspace_id,
        )
        .values(status="denied")
    )
    log.info("chargeback_rule_denied", rule_id=rule_id_str, approval_id=str(approval.id))


async def _activate_budget_override(
    db: AsyncSession,
    approval: Approval,
) -> None:
    override_id_str = approval.request.get("budget_override_id") if approval.request else None
    if not override_id_str:
        return
    try:
        override_id = uuid.UUID(str(override_id_str))
    except ValueError:
        return
    from sqlalchemy import update as sa_update  # noqa: PLC0415

    from runledger_api.models.budget_overrides import BudgetOverride  # noqa: PLC0415

    await db.execute(
        sa_update(BudgetOverride)
        .where(BudgetOverride.id == override_id, BudgetOverride.status == "pending")
        .values(status="active")
    )
    log.info("budget_override_activated", override_id=override_id_str, approval_id=str(approval.id))


async def _deny_budget_override(db: AsyncSession, approval: Approval) -> None:
    override_id_str = approval.request.get("budget_override_id") if approval.request else None
    if not override_id_str:
        return
    try:
        override_id = uuid.UUID(str(override_id_str))
    except ValueError:
        return
    from sqlalchemy import update as sa_update  # noqa: PLC0415

    from runledger_api.models.budget_overrides import BudgetOverride  # noqa: PLC0415

    await db.execute(
        sa_update(BudgetOverride)
        .where(BudgetOverride.id == override_id)
        .values(status="revoked")
    )
    log.info("budget_override_denied", override_id=override_id_str, approval_id=str(approval.id))


async def _cancel_budget_override(db: AsyncSession, approval: Approval) -> None:
    override_id_str = approval.request.get("budget_override_id") if approval.request else None
    if not override_id_str:
        return
    try:
        override_id = uuid.UUID(str(override_id_str))
    except ValueError:
        return
    from sqlalchemy import update as sa_update  # noqa: PLC0415

    from runledger_api.models.budget_overrides import BudgetOverride  # noqa: PLC0415

    await db.execute(
        sa_update(BudgetOverride)
        .where(BudgetOverride.id == override_id, BudgetOverride.status == "pending")
        .values(status="revoked")
    )
    log.info("budget_override_cancelled", override_id=override_id_str, approval_id=str(approval.id))


# ── Validation helper (used by other routers) ──────────────────────────────────


async def validate_approved(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    approval_id: uuid.UUID,
    request_type: str,
) -> Approval:
    """
    Validate that an approval exists, belongs to this workspace, is for the
    given request_type, and is in 'approved' status.

    Raises HTTPException 403 if validation fails.
    """
    result = await db.execute(
        select(Approval).where(
            Approval.id == approval_id,
            Approval.workspace_id == workspace_id,
        )
    )
    approval = result.scalar_one_or_none()
    if approval is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Approval not found — please create an approval request first",
        )
    if approval.request_type != request_type:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Approval type mismatch: expected '{request_type}', got '{approval.request_type}'",
        )
    if approval.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Approval is '{approval.status}', not 'approved'",
        )
    return approval
