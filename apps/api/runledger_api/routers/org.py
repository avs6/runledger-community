"""Organization management for org admins."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any

import bcrypt
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import (
    _ORG_ADMIN_ROLES,
    require_org_admin,
    require_platform_admin,
    require_user,
)
from runledger_api.models.audit import AuditEvent
from runledger_api.models.billing import BillingPeriod, ChargebackRule
from runledger_api.models.budget_overrides import BudgetOverride
from runledger_api.models.budgets import Budget, BudgetNotification
from runledger_api.models.alerts import AlertRule
from runledger_api.models.events import AgentRun, ProviderCall
from runledger_api.models.gateway import GatewayRoute, RoutingPolicy
from runledger_api.models.guardrails import GuardrailRule
from runledger_api.models.tenant import (
    MemberStatusEnum,
    Tenant,
    TenantRoleEnum,
    TenantStatusEnum,
    TenantUser,
    User,
    Workspace,
    WorkspaceRoleEnum,
    WorkspaceStatusEnum,
    WorkspaceUser,
)
from runledger_api.models.tool_policies import ToolPolicy
from runledger_api.models.approvals import Approval
from runledger_api.models.tags import Tag
from runledger_api.models.mcp_registry import McpServer
from runledger_api.models.search_tools import SearchTool
from runledger_api.routers.auth import _make_slug
from runledger_api.services.ledger import get_ledger_closure_summary
from runledger_api.schemas.audit import AuditEventResponse as AuditEventResponse
from runledger_api.schemas.auth import (
    AddWorkspaceMemberRequest,
    InviteOrgMemberRequest,
    MemberStatusUpdate,
    OrgProfileResponse,
    OrgProfileUpdate,
    OrgRoleUpdateRequest,
    PlatformOrgCreate,
    PlatformTenantDelete,
    PlatformTenantUpdate,
    TenantMemberResponse,
    TenantResponse,
    WorkspaceCreateForOrg,
    WorkspaceMemberResponse,
    WorkspaceResponse,
    WorkspaceStatusUpdate,
)
from runledger_api.services.tenancy import assert_not_last_admin, log_audit

log = structlog.get_logger()
router = APIRouter(prefix="/org", tags=["organization"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


async def _tenant_response(db: AsyncSession, tenant: Tenant) -> dict[str, Any]:
    workspace_count = (
        await db.execute(
            select(func.count()).select_from(Workspace).where(Workspace.tenant_id == tenant.id)
        )
    ).scalar() or 0
    member_count = (
        await db.execute(
            select(func.count()).select_from(TenantUser).where(TenantUser.tenant_id == tenant.id)
        )
    ).scalar() or 0
    return {
        "id": tenant.id,
        "name": tenant.name,
        "plan": tenant.plan,
        "status": tenant.status,
        "is_default": tenant.is_default,
        "owner_user_id": tenant.owner_user_id,
        "created_at": tenant.created_at,
        "workspace_count": workspace_count,
        "member_count": member_count,
    }


@router.post("/tenants", status_code=status.HTTP_201_CREATED, response_model=TenantResponse)
async def create_org(
    body: PlatformOrgCreate,
    auth: Annotated[tuple[Workspace, User], Depends(require_platform_admin)],
    db: DbDep,
) -> dict[str, Any]:
    """Platform admin creates a new organization + default workspace + its own org admin.

    The seeded org admin (body.admin_email) is who logs in and runs the org; the creating
    platform admin is NOT added (they are not a member of this org's data plane).
    """
    _ws, _platform = auth
    dupe = (
        await db.execute(select(User).where(User.email == body.admin_email))
    ).scalar_one_or_none()
    if dupe is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Email '{body.admin_email}' already exists")
    tenant = Tenant(slug=_make_slug(body.name), name=body.name)
    db.add(tenant)
    await db.flush()
    pw_hash = bcrypt.hashpw(body.admin_password.encode(), bcrypt.gensalt()).decode()
    admin = User(
        email=body.admin_email,
        password_hash=pw_hash,
        full_name=body.admin_full_name or body.admin_email.split("@")[0],
        is_active=True,
        email_verified=body.skip_verification,
    )
    db.add(admin)
    await db.flush()
    tenant.owner_user_id = admin.id
    db.add(TenantUser(tenant_id=tenant.id, user_id=admin.id, role=TenantRoleEnum.org_admin))
    workspace = Workspace(tenant_id=tenant.id, name=f"{body.name} Workspace")
    db.add(workspace)
    await db.flush()
    db.add(
        WorkspaceUser(
            workspace_id=workspace.id, user_id=admin.id, role=WorkspaceRoleEnum.workspace_admin
        )
    )
    await db.commit()
    await db.refresh(tenant)
    log.info("org_created", tenant_id=str(tenant.id), admin=body.admin_email)
    return await _tenant_response(db, tenant)


@router.get("/tenants", response_model=list[TenantResponse])
async def list_platform_orgs(
    auth: Annotated[tuple[Workspace, User], Depends(require_platform_admin)],
    db: DbDep,
) -> list[dict[str, Any]]:
    """Return every organization for the platform-admin lifecycle hub."""
    _workspace, _platform = auth
    tenants = list(
        (await db.execute(select(Tenant).order_by(Tenant.created_at.desc()))).scalars().all()
    )
    workspace_counts = {
        tenant_id: count
        for tenant_id, count in (
            await db.execute(
                select(Workspace.tenant_id, func.count(Workspace.id)).group_by(Workspace.tenant_id)
            )
        ).all()
    }
    member_counts = {
        tenant_id: count
        for tenant_id, count in (
            await db.execute(
                select(TenantUser.tenant_id, func.count(TenantUser.user_id)).group_by(
                    TenantUser.tenant_id
                )
            )
        ).all()
    }
    return [
        {
            "id": tenant.id,
            "name": tenant.name,
            "plan": tenant.plan,
            "status": tenant.status,
            "is_default": tenant.is_default,
            "owner_user_id": tenant.owner_user_id,
            "created_at": tenant.created_at,
            "workspace_count": workspace_counts.get(tenant.id, 0),
            "member_count": member_counts.get(tenant.id, 0),
        }
        for tenant in tenants
    ]


@router.put("/tenants/{tenant_id}", response_model=TenantResponse)
async def update_platform_org(
    tenant_id: uuid.UUID,
    body: PlatformTenantUpdate,
    auth: Annotated[tuple[Workspace, User], Depends(require_platform_admin)],
    db: DbDep,
) -> dict[str, Any]:
    """Platform-admin lifecycle update for any organization."""
    current_workspace, platform_user = auth
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found")

    old_value = {
        "name": tenant.name,
        "plan": str(tenant.plan),
        "status": str(tenant.status),
    }
    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Organization name is required")
        tenant.name = name
    if body.plan is not None:
        tenant.plan = body.plan
    if (
        body.status is not None
        and body.status != TenantStatusEnum.active
        and (tenant.is_default or tenant.id == current_workspace.tenant_id)
    ):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Default or current organization cannot be suspended or archived",
        )
    if body.status is not None:
        tenant.status = body.status

    log_audit(
        db,
        actor_user_id=platform_user.id,
        scope_type="tenant",
        scope_id=tenant.id,
        action="lifecycle.updated",
        old_value=str(old_value),
        new_value=str(
            {
                "name": tenant.name,
                "plan": str(tenant.plan),
                "status": str(tenant.status),
            }
        ),
    )
    await db.commit()
    await db.refresh(tenant)
    return await _tenant_response(db, tenant)


@router.delete("/tenants/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_platform_org(
    tenant_id: uuid.UUID,
    body: PlatformTenantDelete,
    auth: Annotated[tuple[Workspace, User], Depends(require_platform_admin)],
    db: DbDep,
) -> None:
    """Delete a non-default organization from the platform lifecycle hub."""
    current_workspace, platform_user = auth
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found")
    if tenant.is_default:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot delete the default organization")
    if tenant.id == current_workspace.tenant_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Switch orgs before deleting this one")
    if body.confirmation != tenant.name:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Organization name confirmation mismatch")

    candidate_user_ids = list(
        (await db.execute(select(TenantUser.user_id).where(TenantUser.tenant_id == tenant.id)))
        .scalars()
        .all()
    )
    old_value = {
        "id": str(tenant.id),
        "name": tenant.name,
        "plan": str(tenant.plan),
        "status": str(tenant.status),
    }
    log_audit(
        db,
        actor_user_id=platform_user.id,
        scope_type="tenant",
        scope_id=tenant.id,
        action="lifecycle.deleted",
        old_value=str(old_value),
    )
    await db.delete(tenant)
    await db.flush()

    for user_id in candidate_user_ids:
        user = await db.get(User, user_id)
        if user is None or user.is_platform_admin:
            continue
        has_tenant = (
            await db.execute(select(TenantUser.id).where(TenantUser.user_id == user_id).limit(1))
        ).scalar_one_or_none()
        has_workspace = (
            await db.execute(
                select(WorkspaceUser.user_id).where(WorkspaceUser.user_id == user_id).limit(1)
            )
        ).scalar_one_or_none()
        if has_tenant is None and has_workspace is None:
            user.is_active = False

    await db.commit()


@router.get("/profile", response_model=OrgProfileResponse)
async def get_org_profile(
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)], db: DbDep
) -> Tenant:
    workspace, _, __ = auth
    tenant = await db.get(Tenant, workspace.tenant_id)
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found")
    return tenant


@router.put("/profile", response_model=OrgProfileResponse)
async def update_org_profile(
    body: OrgProfileUpdate, auth: Annotated[tuple[Any, ...], Depends(require_org_admin)], db: DbDep
) -> Tenant:
    workspace, _, __ = auth
    tenant = await db.get(Tenant, workspace.tenant_id)
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found")
    if body.name is not None:
        tenant.name = body.name
    if body.plan is not None:
        tenant.plan = body.plan
    await db.commit()
    await db.refresh(tenant)
    return tenant


@router.get("/dashboard")
async def get_org_dashboard(
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)],
    db: DbDep,
    from_dt: Annotated[datetime | None, Query(alias="from")] = None,
    to_dt: Annotated[datetime | None, Query(alias="to")] = None,
) -> dict[str, Any]:
    """Org-wide dashboard — spend, runs, and per-workspace breakdown for the last 7 days."""
    workspace, _user, _ = auth
    tenant = await db.get(Tenant, workspace.tenant_id)
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found")

    ws_rows = list(
        (await db.execute(select(Workspace).where(Workspace.tenant_id == workspace.tenant_id)))
        .scalars()
        .all()
    )
    ws_ids = [ws.id for ws in ws_rows]
    ws_name_map = {ws.id: ws.name for ws in ws_rows}

    now = to_dt or datetime.now(UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    cur_start = from_dt or (now - timedelta(days=7))
    if cur_start.tzinfo is None:
        cur_start = cur_start.replace(tzinfo=UTC)
    window_seconds = max((now - cur_start).total_seconds(), 1)
    prev_start = cur_start - timedelta(seconds=window_seconds)

    empty_kpis = {
        "tenant_name": tenant.name,
        "workspace_count": len(ws_ids),
        "member_count": 0,
        "total_cost_usd": "0",
        "run_count": 0,
        "total_tokens": 0,
        "cost_delta_pct": None,
        "workspaces": [],
        "top_models": [],
        "recent_runs": [],
    }
    if not ws_ids:
        return empty_kpis

    # ── Current 7-day aggregates ───────────────────────────────────────────────
    cur = (
        await db.execute(
            select(
                func.coalesce(func.sum(AgentRun.total_cost_usd), Decimal("0")).label("cost"),
                func.count(AgentRun.id).label("runs"),
                func.coalesce(
                    func.sum(AgentRun.total_input_tokens + AgentRun.total_output_tokens), 0
                ).label("tokens"),
            ).where(
                AgentRun.workspace_id.in_(ws_ids),
                AgentRun.started_at >= cur_start,
                AgentRun.started_at < now,
            )
        )
    ).one()

    # ── Prior 7-day cost for delta ─────────────────────────────────────────────
    prev_cost = (
        await db.execute(
            select(func.coalesce(func.sum(AgentRun.total_cost_usd), Decimal("0"))).where(
                AgentRun.workspace_id.in_(ws_ids),
                AgentRun.started_at >= prev_start,
                AgentRun.started_at < cur_start,
            )
        )
    ).scalar() or Decimal("0")

    cost_delta: float | None = None
    if float(prev_cost) > 0:
        cost_delta = (float(cur.cost) - float(prev_cost)) / float(prev_cost) * 100

    # ── Per-workspace breakdown ────────────────────────────────────────────────
    ws_stats_rows = (
        await db.execute(
            select(
                AgentRun.workspace_id,
                func.coalesce(func.sum(AgentRun.total_cost_usd), Decimal("0")).label("cost"),
                func.count(AgentRun.id).label("runs"),
            )
            .where(
                AgentRun.workspace_id.in_(ws_ids),
                AgentRun.started_at >= cur_start,
                AgentRun.started_at < now,
            )
            .group_by(AgentRun.workspace_id)
            .order_by(func.sum(AgentRun.total_cost_usd).desc().nullslast())
        )
    ).all()

    ws_cost_map = {r.workspace_id: {"cost": float(r.cost), "runs": r.runs} for r in ws_stats_rows}
    member_count_rows = (
        await db.execute(
            select(WorkspaceUser.workspace_id, func.count(WorkspaceUser.user_id).label("cnt"))
            .where(WorkspaceUser.workspace_id.in_(ws_ids))
            .group_by(WorkspaceUser.workspace_id)
        )
    ).all()
    mc_map = {r.workspace_id: r.cnt for r in member_count_rows}

    workspaces_out = sorted(
        [
            {
                "id": str(ws.id),
                "name": ws.name,
                "status": ws.status,
                "cost_usd": str(ws_cost_map.get(ws.id, {}).get("cost", 0)),
                "run_count": ws_cost_map.get(ws.id, {}).get("runs", 0),
                "member_count": mc_map.get(ws.id, 0),
            }
            for ws in ws_rows
        ],
        key=lambda x: float(x["cost_usd"]),
        reverse=True,
    )

    total_members = sum(mc_map.values())

    # ── Top models ────────────────────────────────────────────────────────────
    top_model_rows = (
        await db.execute(
            select(
                ProviderCall.model,
                func.coalesce(func.sum(ProviderCall.cost_usd), Decimal("0")).label("cost"),
                func.count(ProviderCall.id).label("calls"),
            )
            .where(
                ProviderCall.workspace_id.in_(ws_ids),
                ProviderCall.created_at >= cur_start,
                ProviderCall.created_at < now,
            )
            .group_by(ProviderCall.model)
            .order_by(func.sum(ProviderCall.cost_usd).desc().nullslast())
            .limit(8)
        )
    ).all()
    top_models = [
        {"model": r.model, "cost_usd": str(r.cost), "call_count": r.calls} for r in top_model_rows
    ]

    # ── Recent runs ───────────────────────────────────────────────────────────
    recent_run_rows = (
        (
            await db.execute(
                select(AgentRun)
                .where(
                    AgentRun.workspace_id.in_(ws_ids),
                    AgentRun.started_at >= cur_start,
                    AgentRun.started_at < now,
                )
                .order_by(AgentRun.started_at.desc())
                .limit(10)
            )
        )
        .scalars()
        .all()
    )
    recent_runs = [
        {
            "id": str(r.id),
            "workspace_name": ws_name_map.get(r.workspace_id, ""),
            "status": r.status,
            "feature_tag": r.feature_tag,
            "total_cost_usd": str(r.total_cost_usd) if r.total_cost_usd is not None else None,
            "started_at": r.started_at.isoformat() if r.started_at else None,
        }
        for r in recent_run_rows
    ]

    return {
        "tenant_name": tenant.name,
        "workspace_count": len(ws_ids),
        "member_count": total_members,
        "total_cost_usd": str(cur.cost),
        "run_count": cur.runs,
        "total_tokens": int(cur.tokens),
        "cost_delta_pct": str(round(cost_delta, 2)) if cost_delta is not None else None,
        "workspaces": workspaces_out,
        "top_models": top_models,
        "recent_runs": recent_runs,
    }


@router.get("/workspaces", response_model=list[WorkspaceResponse])
async def list_org_workspaces(
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)], db: DbDep
) -> list[Workspace]:
    workspace, _, __ = auth
    result = await db.execute(
        select(Workspace)
        .where(Workspace.tenant_id == workspace.tenant_id)
        .order_by(Workspace.created_at)
    )
    return list(result.scalars().all())


@router.post("/workspaces", status_code=status.HTTP_201_CREATED, response_model=WorkspaceResponse)
async def create_org_workspace(
    body: WorkspaceCreateForOrg,
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)],
    db: DbDep,
) -> Workspace:
    workspace, user, _ = auth
    existing = await db.execute(
        select(Workspace).where(
            Workspace.tenant_id == workspace.tenant_id,
            func.lower(Workspace.name) == body.name.lower(),
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "A workspace with that name already exists in this organization",
        )
    new_ws = Workspace(tenant_id=workspace.tenant_id, name=body.name)
    db.add(new_ws)
    await db.flush()
    db.add(
        WorkspaceUser(
            workspace_id=new_ws.id,
            user_id=user.id,
            role=WorkspaceRoleEnum.workspace_admin,
            invited_by=user.id,
        )
    )
    await db.commit()
    await db.refresh(new_ws)
    return new_ws


@router.put("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def rename_org_workspace(
    workspace_id: uuid.UUID,
    body: WorkspaceCreateForOrg,
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)],
    db: DbDep,
) -> Workspace:
    """Rename a workspace in the caller's org (org-admin) — full CRUD."""
    workspace, _user, _ = auth
    target = await db.get(Workspace, workspace_id)
    if target is None or target.tenant_id != workspace.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")
    clash = await db.execute(
        select(Workspace).where(
            Workspace.tenant_id == workspace.tenant_id,
            func.lower(Workspace.name) == body.name.lower(),
            Workspace.id != workspace_id,
        )
    )
    if clash.scalar_one_or_none() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "A workspace with that name already exists")
    target.name = body.name
    await db.commit()
    await db.refresh(target)
    return target


@router.get("/workspaces/my", response_model=list[WorkspaceResponse])
async def list_my_workspaces(
    auth: Annotated[tuple[Any, ...], Depends(require_user)], db: DbDep
) -> list[Workspace]:
    """Returns workspaces the current user belongs to.
    Org admins and platform admins see all workspaces in the org.
    Regular members see only workspaces they've been assigned to.
    """
    workspace, user = auth
    if user.is_platform_admin:
        result = await db.execute(
            select(Workspace)
            .where(Workspace.tenant_id == workspace.tenant_id)
            .order_by(Workspace.created_at)
        )
        return list(result.scalars().all())
    tu = (
        await db.execute(
            select(TenantUser).where(
                TenantUser.user_id == user.id, TenantUser.tenant_id == workspace.tenant_id
            )
        )
    ).scalar_one_or_none()
    if tu and tu.role in _ORG_ADMIN_ROLES:
        result = await db.execute(
            select(Workspace)
            .where(Workspace.tenant_id == workspace.tenant_id)
            .order_by(Workspace.created_at)
        )
        return list(result.scalars().all())
    # Regular member — return only their assigned workspaces
    result = await db.execute(
        select(Workspace)
        .join(WorkspaceUser, WorkspaceUser.workspace_id == Workspace.id)
        .where(WorkspaceUser.user_id == user.id, Workspace.tenant_id == workspace.tenant_id)
        .order_by(Workspace.created_at)
    )
    return list(result.scalars().all())


@router.put("/workspaces/{workspace_id}/status", response_model=WorkspaceResponse)
async def update_workspace_status(
    workspace_id: uuid.UUID,
    body: WorkspaceStatusUpdate,
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)],
    db: DbDep,
) -> Workspace:
    current_ws, current_user, _ = auth
    target = await db.get(Workspace, workspace_id)
    if target is None or target.tenant_id != current_ws.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found in this organization")
    if body.status == WorkspaceStatusEnum.archived:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Only Platform Admins can archive workspaces"
        )
    old_status = target.status
    target.status = body.status
    log_audit(
        db,
        actor_user_id=current_user.id,
        scope_type="workspace",
        scope_id=workspace_id,
        action="workspace.status_changed",
        old_value=str(old_status),
        new_value=str(body.status),
    )
    await db.commit()
    await db.refresh(target)
    return target


@router.delete("/workspaces/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_org_workspace(
    workspace_id: uuid.UUID, auth: Annotated[tuple[Any, ...], Depends(require_org_admin)], db: DbDep
) -> None:
    current_ws, _, __ = auth
    target = await db.get(Workspace, workspace_id)
    if target is None or target.tenant_id != current_ws.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found in this organization")
    count = len(
        (await db.execute(select(Workspace).where(Workspace.tenant_id == current_ws.tenant_id)))
        .scalars()
        .all()
    )
    if count <= 1:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot delete the last workspace")
    await db.delete(target)
    await db.commit()


@router.get("/members", response_model=list[TenantMemberResponse])
async def list_org_members(
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)], db: DbDep
) -> list[TenantMemberResponse]:
    workspace, _, __ = auth
    result = await db.execute(
        select(TenantUser, User)
        .join(User, TenantUser.user_id == User.id)
        .where(TenantUser.tenant_id == workspace.tenant_id)
        .order_by(TenantUser.created_at)
    )
    return [
        TenantMemberResponse(
            user_id=tu.user_id,
            tenant_id=tu.tenant_id,
            role=tu.role,
            status=tu.status,
            email=u.email,
            full_name=u.full_name,
            is_active=u.is_active,
            last_login_at=u.last_login_at,
            created_at=tu.created_at,
        )
        for tu, u in result.all()
    ]


@router.post(
    "/members/invite", status_code=status.HTTP_201_CREATED, response_model=TenantMemberResponse
)
async def invite_org_member(
    body: InviteOrgMemberRequest,
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)],
    db: DbDep,
) -> TenantMemberResponse:
    workspace, inviting_user, _ = auth

    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user is None:
        pw_hash = bcrypt.hashpw(body.temporary_password.encode(), bcrypt.gensalt()).decode()
        user = User(
            email=body.email, password_hash=pw_hash, full_name=body.full_name, is_active=True
        )
        db.add(user)
        await db.flush()

    existing = await db.execute(
        select(TenantUser).where(
            TenantUser.tenant_id == workspace.tenant_id, TenantUser.user_id == user.id
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "User is already a member of this organization"
        )

    tu = TenantUser(
        tenant_id=workspace.tenant_id, user_id=user.id, role=body.role, invited_by=inviting_user.id
    )
    db.add(tu)
    await db.commit()
    await db.refresh(tu)
    return TenantMemberResponse(
        user_id=tu.user_id,
        tenant_id=tu.tenant_id,
        role=tu.role,
        status=tu.status,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        last_login_at=user.last_login_at,
        created_at=tu.created_at,
    )


@router.put("/members/{user_id}/role", response_model=TenantMemberResponse)
async def update_org_member_role(
    user_id: uuid.UUID,
    body: OrgRoleUpdateRequest,
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)],
    db: DbDep,
) -> TenantMemberResponse:
    workspace, current_user, _ = auth
    if user_id == current_user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot change your own org role")
    result = await db.execute(
        select(TenantUser, User)
        .join(User, TenantUser.user_id == User.id)
        .where(TenantUser.tenant_id == workspace.tenant_id, TenantUser.user_id == user_id)
    )
    row = result.first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found in this organization")
    tu, u = row
    if tu.role == TenantRoleEnum.org_admin and body.role != TenantRoleEnum.org_admin:
        await assert_not_last_admin(workspace.tenant_id, user_id, db)
    old_role = tu.role
    tu.role = body.role
    log_audit(
        db,
        actor_user_id=current_user.id,
        scope_type="tenant",
        scope_id=workspace.tenant_id,
        action="org.member.role_changed",
        target_user_id=user_id,
        old_value=str(old_role),
        new_value=str(body.role),
    )
    await db.commit()
    await db.refresh(tu)
    return TenantMemberResponse(
        user_id=tu.user_id,
        tenant_id=tu.tenant_id,
        role=tu.role,
        status=tu.status,
        email=u.email,
        full_name=u.full_name,
        is_active=u.is_active,
        last_login_at=u.last_login_at,
        created_at=tu.created_at,
    )


@router.delete("/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_org_member(
    user_id: uuid.UUID, auth: Annotated[tuple[Any, ...], Depends(require_org_admin)], db: DbDep
) -> None:
    workspace, current_user, _ = auth
    if user_id == current_user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot remove yourself from organization")
    result = await db.execute(
        select(TenantUser).where(
            TenantUser.tenant_id == workspace.tenant_id, TenantUser.user_id == user_id
        )
    )
    tu = result.scalar_one_or_none()
    if tu is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    if tu.role == TenantRoleEnum.org_admin:
        await assert_not_last_admin(workspace.tenant_id, user_id, db)
    log_audit(
        db,
        actor_user_id=current_user.id,
        scope_type="tenant",
        scope_id=workspace.tenant_id,
        action="org.member.removed",
        target_user_id=user_id,
        old_value=str(tu.role),
    )
    await db.delete(tu)
    ws_ids = list(
        (await db.execute(select(Workspace.id).where(Workspace.tenant_id == workspace.tenant_id)))
        .scalars()
        .all()
    )
    for wu in (
        (
            await db.execute(
                select(WorkspaceUser).where(
                    WorkspaceUser.user_id == user_id, WorkspaceUser.workspace_id.in_(ws_ids)
                )
            )
        )
        .scalars()
        .all()
    ):
        await db.delete(wu)
    await db.commit()


@router.put("/members/{user_id}/status", response_model=TenantMemberResponse)
async def update_org_member_status(
    user_id: uuid.UUID,
    body: MemberStatusUpdate,
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)],
    db: DbDep,
) -> TenantMemberResponse:
    workspace, current_user, _ = auth
    if user_id == current_user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot change your own membership status")
    result = await db.execute(
        select(TenantUser, User)
        .join(User, TenantUser.user_id == User.id)
        .where(TenantUser.tenant_id == workspace.tenant_id, TenantUser.user_id == user_id)
    )
    row = result.first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    tu, u = row
    # Last-admin guard: suspending the last org_admin is also blocked
    if tu.role == TenantRoleEnum.org_admin and body.status != MemberStatusEnum.active:
        await assert_not_last_admin(workspace.tenant_id, user_id, db)
    old_status = tu.status
    tu.status = body.status
    log_audit(
        db,
        actor_user_id=current_user.id,
        scope_type="tenant",
        scope_id=workspace.tenant_id,
        action="org.member.status_changed",
        target_user_id=user_id,
        old_value=str(old_status),
        new_value=str(body.status),
    )
    await db.commit()
    await db.refresh(tu)
    return TenantMemberResponse(
        user_id=tu.user_id,
        tenant_id=tu.tenant_id,
        role=tu.role,
        status=tu.status,
        email=u.email,
        full_name=u.full_name,
        is_active=u.is_active,
        last_login_at=u.last_login_at,
        created_at=tu.created_at,
    )


# ── Workspace membership (org-admin scoped) ────────────────────────────────────


@router.get("/workspaces/{workspace_id}/members", response_model=list[WorkspaceMemberResponse])
async def list_workspace_members(
    workspace_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)],
    db: DbDep,
) -> list[WorkspaceMemberResponse]:
    current_ws, _, __ = auth
    target = await db.get(Workspace, workspace_id)
    if target is None or target.tenant_id != current_ws.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")
    result = await db.execute(
        select(WorkspaceUser, User)
        .join(User, WorkspaceUser.user_id == User.id)
        .where(WorkspaceUser.workspace_id == workspace_id)
        .order_by(WorkspaceUser.created_at)
    )
    return [
        WorkspaceMemberResponse(
            user_id=wu.user_id,
            workspace_id=wu.workspace_id,
            role=wu.role,
            email=u.email,
            full_name=u.full_name,
            is_active=u.is_active,
            last_login_at=u.last_login_at,
            joined_at=wu.created_at,
        )
        for wu, u in result.all()
    ]


@router.post(
    "/workspaces/{workspace_id}/members",
    status_code=status.HTTP_201_CREATED,
    response_model=WorkspaceMemberResponse,
)
async def add_workspace_member(
    workspace_id: uuid.UUID,
    body: AddWorkspaceMemberRequest,
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)],
    db: DbDep,
) -> WorkspaceMemberResponse:
    current_ws, inviting_user, _ = auth
    target = await db.get(Workspace, workspace_id)
    if target is None or target.tenant_id != current_ws.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")
    user = await db.get(User, body.user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    tu = await db.execute(
        select(TenantUser).where(
            TenantUser.tenant_id == current_ws.tenant_id, TenantUser.user_id == body.user_id
        )
    )
    if tu.scalar_one_or_none() is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "User must be an org member first")
    existing = await db.execute(
        select(WorkspaceUser).where(
            WorkspaceUser.workspace_id == workspace_id, WorkspaceUser.user_id == body.user_id
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "User is already a member of this workspace")
    wu = WorkspaceUser(
        workspace_id=workspace_id, user_id=body.user_id, role=body.role, invited_by=inviting_user.id
    )
    db.add(wu)
    await db.commit()
    await db.refresh(wu)
    return WorkspaceMemberResponse(
        user_id=wu.user_id,
        workspace_id=wu.workspace_id,
        role=wu.role,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        last_login_at=user.last_login_at,
        joined_at=wu.created_at,
    )


@router.delete(
    "/workspaces/{workspace_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_workspace_member(
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)],
    db: DbDep,
) -> None:
    current_ws, current_user, _ = auth
    target = await db.get(Workspace, workspace_id)
    if target is None or target.tenant_id != current_ws.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")
    result = await db.execute(
        select(WorkspaceUser).where(
            WorkspaceUser.workspace_id == workspace_id, WorkspaceUser.user_id == user_id
        )
    )
    wu = result.scalar_one_or_none()
    if wu is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found in workspace")
    # Prevent removing yourself from your current workspace
    if user_id == current_user.id and workspace_id == current_ws.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Cannot remove yourself from your current workspace"
        )
    await db.delete(wu)
    await db.commit()


# ── Org Finance Summary ────────────────────────────────────────────────────────


class WorkspaceFinanceSummary(BaseModel):
    workspace_id: uuid.UUID
    workspace_name: str
    spend_30d_usd: Decimal
    active_budget_count: int
    total_budget_limit_usd: Decimal
    active_override_count: int
    active_notification_count: int
    open_billing_periods: int
    closed_billing_periods: int
    overdue_billing_periods: int
    chargeback_rule_count: int
    chargeback_status: str
    ledger_readiness_status: str
    ledger_evidence_score: int


class OrgFinanceSummary(BaseModel):
    workspaces: list[WorkspaceFinanceSummary]
    org_spend_30d_usd: Decimal
    org_total_budget_limit_usd: Decimal
    active_budget_count: int
    active_override_count: int
    active_notification_count: int
    open_billing_period_count: int
    closed_billing_period_count: int
    overdue_billing_period_count: int
    chargeback_rule_count: int
    chargeback_ready_workspace_count: int
    ledger_readiness_status: str
    ledger_ready_workspace_count: int
    ledger_partial_workspace_count: int
    ledger_at_risk_workspace_count: int


@router.get("/finance", response_model=OrgFinanceSummary)
async def get_org_finance(
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)],
    db: DbDep,
) -> OrgFinanceSummary:
    """Cross-workspace financial summary for org admins."""
    current_ws, _, __ = auth
    since = datetime.now(UTC) - timedelta(days=30)
    today = datetime.now(UTC).date()

    # All workspaces in this org
    ws_result = await db.execute(
        select(Workspace)
        .where(Workspace.tenant_id == current_ws.tenant_id)
        .order_by(Workspace.name)
    )
    workspaces = list(ws_result.scalars().all())
    ws_ids = [ws.id for ws in workspaces]

    if not ws_ids:
        return OrgFinanceSummary(
            workspaces=[],
            org_spend_30d_usd=Decimal(0),
            org_total_budget_limit_usd=Decimal(0),
            active_budget_count=0,
            active_override_count=0,
            active_notification_count=0,
            open_billing_period_count=0,
            closed_billing_period_count=0,
            overdue_billing_period_count=0,
            chargeback_rule_count=0,
            chargeback_ready_workspace_count=0,
            ledger_readiness_status="empty",
            ledger_ready_workspace_count=0,
            ledger_partial_workspace_count=0,
            ledger_at_risk_workspace_count=0,
        )

    # 30-day spend per workspace — query provider_calls directly so intra-day
    # costs appear immediately without waiting for the nightly rollup.
    spend_result = await db.execute(
        select(ProviderCall.workspace_id, func.sum(ProviderCall.cost_usd).label("total"))
        .where(
            ProviderCall.workspace_id.in_(ws_ids),
            ProviderCall.created_at >= since,
            ProviderCall.cost_usd.is_not(None),
        )
        .group_by(ProviderCall.workspace_id)
    )
    spend_by_ws: dict[uuid.UUID, Decimal] = {
        row.workspace_id: row.total or Decimal(0) for row in spend_result.all()
    }

    # Active budgets per workspace
    budget_result = await db.execute(
        select(
            Budget.workspace_id,
            func.count().label("cnt"),
            func.sum(Budget.limit_usd).label("total_limit"),
        )
        .where(Budget.workspace_id.in_(ws_ids), Budget.is_active.is_(True))
        .group_by(Budget.workspace_id)
    )
    budget_by_ws: dict[uuid.UUID, tuple[int, Decimal]] = {
        row.workspace_id: (row.cnt, row.total_limit or Decimal(0)) for row in budget_result.all()
    }

    override_result = await db.execute(
        select(Budget.workspace_id, func.count().label("cnt"))
        .join(BudgetOverride, BudgetOverride.budget_id == Budget.id)
        .where(
            Budget.workspace_id.in_(ws_ids),
            BudgetOverride.status == "active",
        )
        .group_by(Budget.workspace_id)
    )
    overrides_by_ws: dict[uuid.UUID, int] = {
        row.workspace_id: row.cnt for row in override_result.all()
    }

    notification_result = await db.execute(
        select(BudgetNotification.workspace_id, func.count().label("cnt"))
        .where(
            BudgetNotification.workspace_id.in_(ws_ids),
            BudgetNotification.is_active.is_(True),
        )
        .group_by(BudgetNotification.workspace_id)
    )
    notifications_by_ws: dict[uuid.UUID, int] = {
        row.workspace_id: row.cnt for row in notification_result.all()
    }

    # Open/closed/overdue billing periods per workspace
    period_result = await db.execute(
        select(
            BillingPeriod.workspace_id,
            func.sum(
                case(
                    (BillingPeriod.status.in_(("open", "closing")), 1),
                    else_=0,
                )
            ).label("open_cnt"),
            func.sum(
                case(
                    (BillingPeriod.status == "closed", 1),
                    else_=0,
                )
            ).label("closed_cnt"),
            func.sum(
                case(
                    (
                        and_(
                            BillingPeriod.status.in_(("open", "closing")),
                            BillingPeriod.period_end < today,
                        ),
                        1,
                    ),
                    else_=0,
                )
            ).label("overdue_cnt"),
        )
        .where(BillingPeriod.workspace_id.in_(ws_ids))
        .group_by(BillingPeriod.workspace_id)
    )
    open_periods: dict[uuid.UUID, int] = {}
    closed_periods: dict[uuid.UUID, int] = {}
    overdue_periods: dict[uuid.UUID, int] = {}
    for row in period_result.all():
        open_periods[row.workspace_id] = row.open_cnt or 0
        closed_periods[row.workspace_id] = row.closed_cnt or 0
        overdue_periods[row.workspace_id] = row.overdue_cnt or 0

    chargeback_result = await db.execute(
        select(ChargebackRule.workspace_id, func.count().label("cnt"))
        .where(
            ChargebackRule.workspace_id.in_(ws_ids),
            ChargebackRule.status == "active",
        )
        .group_by(ChargebackRule.workspace_id)
    )
    chargeback_rules_by_ws: dict[uuid.UUID, int] = {
        row.workspace_id: row.cnt for row in chargeback_result.all()
    }

    ledger_by_ws: dict[uuid.UUID, tuple[str, int, bool]] = {}
    for ws in workspaces:
        ledger_summary = await get_ledger_closure_summary(db, ws.id)
        chargeback_rule_count = chargeback_rules_by_ws.get(ws.id, 0)
        chargeback_ready = False
        if chargeback_rule_count > 0 and ledger_summary.chargeback is not None:
            try:
                chargeback_ready = Decimal(ledger_summary.chargeback.unallocated_cost_usd) <= Decimal(
                    "0.000001"
                )
            except Exception:  # pragma: no cover - defensive parsing
                chargeback_ready = False
        ledger_by_ws[ws.id] = (
            ledger_summary.readiness_status,
            ledger_summary.evidence_score,
            chargeback_ready,
        )

    summaries = [
        WorkspaceFinanceSummary(
            workspace_id=ws.id,
            workspace_name=ws.name,
            spend_30d_usd=spend_by_ws.get(ws.id, Decimal(0)),
            active_budget_count=budget_by_ws.get(ws.id, (0, Decimal(0)))[0],
            total_budget_limit_usd=budget_by_ws.get(ws.id, (0, Decimal(0)))[1],
            active_override_count=overrides_by_ws.get(ws.id, 0),
            active_notification_count=notifications_by_ws.get(ws.id, 0),
            open_billing_periods=open_periods.get(ws.id, 0),
            closed_billing_periods=closed_periods.get(ws.id, 0),
            overdue_billing_periods=overdue_periods.get(ws.id, 0),
            chargeback_rule_count=chargeback_rules_by_ws.get(ws.id, 0),
            chargeback_status=(
                "ready"
                if ledger_by_ws.get(ws.id, ("empty", 0, False))[2]
                else "partial"
                if chargeback_rules_by_ws.get(ws.id, 0) > 0
                else "missing"
            ),
            ledger_readiness_status=ledger_by_ws.get(ws.id, ("empty", 0, False))[0],
            ledger_evidence_score=ledger_by_ws.get(ws.id, ("empty", 0, False))[1],
        )
        for ws in workspaces
    ]

    ledger_ready_workspace_count = sum(
        1 for summary in summaries if summary.ledger_readiness_status == "ready"
    )
    ledger_partial_workspace_count = sum(
        1 for summary in summaries if summary.ledger_readiness_status == "partial"
    )
    ledger_at_risk_workspace_count = sum(
        1 for summary in summaries if summary.ledger_readiness_status == "at_risk"
    )
    if ledger_at_risk_workspace_count > 0:
        ledger_readiness_status = "at_risk"
    elif ledger_partial_workspace_count > 0:
        ledger_readiness_status = "partial"
    elif ledger_ready_workspace_count == len(summaries):
        ledger_readiness_status = "ready"
    else:
        ledger_readiness_status = "empty"

    return OrgFinanceSummary(
        workspaces=summaries,
        org_spend_30d_usd=sum((s.spend_30d_usd for s in summaries), Decimal(0)),
        org_total_budget_limit_usd=sum((s.total_budget_limit_usd for s in summaries), Decimal(0)),
        active_budget_count=sum(s.active_budget_count for s in summaries),
        active_override_count=sum(s.active_override_count for s in summaries),
        active_notification_count=sum(s.active_notification_count for s in summaries),
        open_billing_period_count=sum(s.open_billing_periods for s in summaries),
        closed_billing_period_count=sum(s.closed_billing_periods for s in summaries),
        overdue_billing_period_count=sum(s.overdue_billing_periods for s in summaries),
        chargeback_rule_count=sum(s.chargeback_rule_count for s in summaries),
        chargeback_ready_workspace_count=sum(
            1 for s in summaries if s.chargeback_status == "ready"
        ),
        ledger_readiness_status=ledger_readiness_status,
        ledger_ready_workspace_count=ledger_ready_workspace_count,
        ledger_partial_workspace_count=ledger_partial_workspace_count,
        ledger_at_risk_workspace_count=ledger_at_risk_workspace_count,
    )


# ── Runtime posture ────────────────────────────────────────────────────────────


class WorkspaceRuntimeSummary(BaseModel):
    workspace_id: uuid.UUID
    workspace_name: str
    active_route_count: int
    distinct_provider_count: int
    routing_policy_count: int
    active_guardrail_count: int
    rate_limited_route_count: int


class OrgRuntimeSummary(BaseModel):
    workspaces: list[WorkspaceRuntimeSummary]
    total_active_routes: int
    total_distinct_providers: int
    total_routing_policies: int
    total_active_guardrails: int
    total_rate_limited_routes: int


@router.get("/runtime", response_model=OrgRuntimeSummary)
async def get_org_runtime(
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)],
    db: DbDep,
) -> OrgRuntimeSummary:
    """Cross-workspace runtime posture summary for org admins."""
    current_ws, _, __ = auth

    ws_result = await db.execute(
        select(Workspace)
        .where(Workspace.tenant_id == current_ws.tenant_id)
        .order_by(Workspace.name)
    )
    workspaces = list(ws_result.scalars().all())
    ws_ids = [ws.id for ws in workspaces]

    if not ws_ids:
        return OrgRuntimeSummary(
            workspaces=[],
            total_active_routes=0,
            total_distinct_providers=0,
            total_routing_policies=0,
            total_active_guardrails=0,
            total_rate_limited_routes=0,
        )

    route_result = await db.execute(
        select(
            GatewayRoute.workspace_id,
            func.count().label("cnt"),
            func.count(func.distinct(GatewayRoute.provider)).label("providers"),
            func.sum(
                case(
                    (GatewayRoute.per_user_rpm_limit.is_not(None), 1),
                    else_=0,
                )
            ).label("rate_limited"),
        )
        .where(GatewayRoute.workspace_id.in_(ws_ids), GatewayRoute.is_active.is_(True))
        .group_by(GatewayRoute.workspace_id)
    )
    routes_by_ws: dict[uuid.UUID, tuple[int, int, int]] = {
        row.workspace_id: (row.cnt, row.providers, row.rate_limited or 0)
        for row in route_result.all()
    }

    policy_result = await db.execute(
        select(RoutingPolicy.workspace_id, func.count().label("cnt"))
        .where(
            RoutingPolicy.workspace_id.in_(ws_ids),
            RoutingPolicy.status == "active",
        )
        .group_by(RoutingPolicy.workspace_id)
    )
    policies_by_ws: dict[uuid.UUID, int] = {
        row.workspace_id: row.cnt for row in policy_result.all()
    }

    guardrail_result = await db.execute(
        select(GuardrailRule.workspace_id, func.count().label("cnt"))
        .where(
            GuardrailRule.workspace_id.in_(ws_ids),
            GuardrailRule.status == "active",
        )
        .group_by(GuardrailRule.workspace_id)
    )
    guardrails_by_ws: dict[uuid.UUID, int] = {
        row.workspace_id: row.cnt for row in guardrail_result.all()
    }

    summaries = [
        WorkspaceRuntimeSummary(
            workspace_id=ws.id,
            workspace_name=ws.name,
            active_route_count=routes_by_ws.get(ws.id, (0, 0, 0))[0],
            distinct_provider_count=routes_by_ws.get(ws.id, (0, 0, 0))[1],
            routing_policy_count=policies_by_ws.get(ws.id, 0),
            active_guardrail_count=guardrails_by_ws.get(ws.id, 0),
            rate_limited_route_count=routes_by_ws.get(ws.id, (0, 0, 0))[2],
        )
        for ws in workspaces
    ]

    return OrgRuntimeSummary(
        workspaces=summaries,
        total_active_routes=sum(s.active_route_count for s in summaries),
        total_distinct_providers=sum(s.distinct_provider_count for s in summaries),
        total_routing_policies=sum(s.routing_policy_count for s in summaries),
        total_active_guardrails=sum(s.active_guardrail_count for s in summaries),
        total_rate_limited_routes=sum(s.rate_limited_route_count for s in summaries),
    )


# ── Observability posture ──────────────────────────────────────────────────────


class WorkspaceObserveSummary(BaseModel):
    workspace_id: uuid.UUID
    workspace_name: str
    run_count_30d: int
    request_count_30d: int
    distinct_model_count: int
    error_count_30d: int
    active_alert_rule_count: int


class OrgObserveSummary(BaseModel):
    workspaces: list[WorkspaceObserveSummary]
    total_run_count_30d: int
    total_request_count_30d: int
    total_distinct_models: int
    total_error_count_30d: int
    total_active_alert_rules: int


@router.get("/observe", response_model=OrgObserveSummary)
async def get_org_observe(
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)],
    db: DbDep,
) -> OrgObserveSummary:
    """Cross-workspace observability posture summary for org admins."""
    current_ws, _, __ = auth
    since = datetime.now(UTC) - timedelta(days=30)

    ws_result = await db.execute(
        select(Workspace)
        .where(Workspace.tenant_id == current_ws.tenant_id)
        .order_by(Workspace.name)
    )
    workspaces = list(ws_result.scalars().all())
    ws_ids = [ws.id for ws in workspaces]

    if not ws_ids:
        return OrgObserveSummary(
            workspaces=[],
            total_run_count_30d=0,
            total_request_count_30d=0,
            total_distinct_models=0,
            total_error_count_30d=0,
            total_active_alert_rules=0,
        )

    run_result = await db.execute(
        select(AgentRun.workspace_id, func.count().label("cnt"))
        .where(AgentRun.workspace_id.in_(ws_ids), AgentRun.created_at >= since)
        .group_by(AgentRun.workspace_id)
    )
    runs_by_ws: dict[uuid.UUID, int] = {
        row.workspace_id: row.cnt for row in run_result.all()
    }

    request_result = await db.execute(
        select(
            ProviderCall.workspace_id,
            func.count().label("cnt"),
            func.count(func.distinct(ProviderCall.model)).label("models"),
            func.sum(
                case(
                    (ProviderCall.status_code >= 400, 1),
                    else_=0,
                )
            ).label("errors"),
        )
        .where(ProviderCall.workspace_id.in_(ws_ids), ProviderCall.created_at >= since)
        .group_by(ProviderCall.workspace_id)
    )
    requests_by_ws: dict[uuid.UUID, tuple[int, int, int]] = {
        row.workspace_id: (row.cnt, row.models, row.errors or 0)
        for row in request_result.all()
    }

    alert_result = await db.execute(
        select(AlertRule.workspace_id, func.count().label("cnt"))
        .where(AlertRule.workspace_id.in_(ws_ids), AlertRule.is_active.is_(True))
        .group_by(AlertRule.workspace_id)
    )
    alerts_by_ws: dict[uuid.UUID, int] = {
        row.workspace_id: row.cnt for row in alert_result.all()
    }

    summaries = [
        WorkspaceObserveSummary(
            workspace_id=ws.id,
            workspace_name=ws.name,
            run_count_30d=runs_by_ws.get(ws.id, 0),
            request_count_30d=requests_by_ws.get(ws.id, (0, 0, 0))[0],
            distinct_model_count=requests_by_ws.get(ws.id, (0, 0, 0))[1],
            error_count_30d=requests_by_ws.get(ws.id, (0, 0, 0))[2],
            active_alert_rule_count=alerts_by_ws.get(ws.id, 0),
        )
        for ws in workspaces
    ]

    return OrgObserveSummary(
        workspaces=summaries,
        total_run_count_30d=sum(s.run_count_30d for s in summaries),
        total_request_count_30d=sum(s.request_count_30d for s in summaries),
        total_distinct_models=sum(s.distinct_model_count for s in summaries),
        total_error_count_30d=sum(s.error_count_30d for s in summaries),
        total_active_alert_rules=sum(s.active_alert_rule_count for s in summaries),
    )


# ── Audit log ──────────────────────────────────────────────────────────────────


@router.get("/audit-log", response_model=list[AuditEventResponse])
async def get_org_audit_log(
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)],
    db: DbDep,
    limit: int = 100,
) -> list[AuditEvent]:
    workspace, _, __ = auth
    # Get all workspace IDs for this org
    ws_ids = list(
        (await db.execute(select(Workspace.id).where(Workspace.tenant_id == workspace.tenant_id)))
        .scalars()
        .all()
    )
    result = await db.execute(
        select(AuditEvent)
        .where(AuditEvent.workspace_id.in_(ws_ids))
        .order_by(AuditEvent.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


class OrgGovernanceSummary(BaseModel):
    tool_count: int
    tool_policy_count: int
    approval_count: int
    audit_event_count: int
    tag_count: int
    mcp_server_count: int
    search_tool_count: int


@router.get("/governance", response_model=OrgGovernanceSummary)
async def get_org_governance(
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)],
    db: DbDep,
) -> dict[str, Any]:
    workspace, _, __ = auth
    ws_ids = list(
        (await db.execute(select(Workspace.id).where(Workspace.tenant_id == workspace.tenant_id)))
        .scalars()
        .all()
    )

    tool_policy_count = (await db.execute(
        select(func.count()).select_from(ToolPolicy).where(ToolPolicy.workspace_id.in_(ws_ids))
    )).scalar() or 0

    approval_count = (await db.execute(
        select(func.count()).select_from(Approval).where(Approval.workspace_id.in_(ws_ids))
    )).scalar() or 0

    audit_event_count = (await db.execute(
        select(func.count()).select_from(AuditEvent).where(AuditEvent.workspace_id.in_(ws_ids))
    )).scalar() or 0

    tag_count = (await db.execute(
        select(func.count()).select_from(Tag).where(Tag.workspace_id.in_(ws_ids))
    )).scalar() or 0

    mcp_server_count = (await db.execute(
        select(func.count()).select_from(McpServer).where(McpServer.workspace_id.in_(ws_ids))
    )).scalar() or 0

    search_tool_count = (await db.execute(
        select(func.count()).select_from(SearchTool).where(SearchTool.workspace_id.in_(ws_ids))
    )).scalar() or 0

    return {
        "tool_count": mcp_server_count + search_tool_count,
        "tool_policy_count": tool_policy_count,
        "approval_count": approval_count,
        "audit_event_count": audit_event_count,
        "tag_count": tag_count,
        "mcp_server_count": mcp_server_count,
        "search_tool_count": search_tool_count,
    }
