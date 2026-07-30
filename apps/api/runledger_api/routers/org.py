"""Organization management for org admins."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any

import bcrypt
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import (
    _ORG_ADMIN_ROLES,
    require_org_admin,
    require_platform_admin,
    require_user,
)
from runledger_api.models.audit import AuditEvent
from runledger_api.models.billing import BillingPeriod
from runledger_api.models.budgets import Budget
from runledger_api.models.events import AgentRun, ProviderCall
from runledger_api.models.tenant import (
    MemberStatusEnum,
    Tenant,
    TenantRoleEnum,
    TenantUser,
    User,
    Workspace,
    WorkspaceRoleEnum,
    WorkspaceStatusEnum,
    WorkspaceUser,
)
from runledger_api.routers.auth import _make_slug
from runledger_api.schemas.audit import AuditEventResponse as AuditEventResponse
from runledger_api.schemas.auth import (
    AddWorkspaceMemberRequest,
    InviteOrgMemberRequest,
    MemberStatusUpdate,
    OrgProfileResponse,
    OrgProfileUpdate,
    OrgRoleUpdateRequest,
    PlatformOrgCreate,
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
    return {
        "id": tenant.id,
        "name": tenant.name,
        "plan": tenant.plan,
        "is_default": tenant.is_default,
        "owner_user_id": tenant.owner_user_id,
        "created_at": tenant.created_at,
        "workspace_count": 1,
        "member_count": 1,
    }


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
                select(Workspace.tenant_id, func.count(Workspace.id))
                .group_by(Workspace.tenant_id)
            )
        ).all()
    }
    member_counts = {
        tenant_id: count
        for tenant_id, count in (
            await db.execute(
                select(TenantUser.tenant_id, func.count(TenantUser.user_id))
                .group_by(TenantUser.tenant_id)
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

    now = datetime.now(UTC)
    cur_start = now - timedelta(days=7)
    prev_start = cur_start - timedelta(days=7)

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
                .where(AgentRun.workspace_id.in_(ws_ids))
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
    open_billing_periods: int
    closed_billing_periods: int


class OrgFinanceSummary(BaseModel):
    workspaces: list[WorkspaceFinanceSummary]
    org_spend_30d_usd: Decimal
    org_total_budget_limit_usd: Decimal


@router.get("/finance", response_model=OrgFinanceSummary)
async def get_org_finance(
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)],
    db: DbDep,
) -> OrgFinanceSummary:
    """Cross-workspace financial summary for org admins."""
    current_ws, _, __ = auth
    since = datetime.now(UTC) - timedelta(days=30)

    # All workspaces in this org
    ws_result = await db.execute(
        select(Workspace)
        .where(Workspace.tenant_id == current_ws.tenant_id)
        .order_by(Workspace.name)
    )
    workspaces = list(ws_result.scalars().all())
    ws_ids = [ws.id for ws in workspaces]

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

    # Open/closed billing periods per workspace
    period_result = await db.execute(
        select(BillingPeriod.workspace_id, BillingPeriod.status, func.count().label("cnt"))
        .where(BillingPeriod.workspace_id.in_(ws_ids))
        .group_by(BillingPeriod.workspace_id, BillingPeriod.status)
    )
    open_periods: dict[uuid.UUID, int] = {}
    closed_periods: dict[uuid.UUID, int] = {}
    for row in period_result.all():
        if row.status == "open":
            open_periods[row.workspace_id] = row.cnt
        elif row.status == "closed":
            closed_periods[row.workspace_id] = row.cnt

    summaries = [
        WorkspaceFinanceSummary(
            workspace_id=ws.id,
            workspace_name=ws.name,
            spend_30d_usd=spend_by_ws.get(ws.id, Decimal(0)),
            active_budget_count=budget_by_ws.get(ws.id, (0, Decimal(0)))[0],
            total_budget_limit_usd=budget_by_ws.get(ws.id, (0, Decimal(0)))[1],
            open_billing_periods=open_periods.get(ws.id, 0),
            closed_billing_periods=closed_periods.get(ws.id, 0),
        )
        for ws in workspaces
    ]

    return OrgFinanceSummary(
        workspaces=summaries,
        org_spend_30d_usd=sum((s.spend_30d_usd for s in summaries), Decimal(0)),
        org_total_budget_limit_usd=sum((s.total_budget_limit_usd for s in summaries), Decimal(0)),
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
