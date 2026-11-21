"""Workspace-level user management. Requires dashboard session."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import (
    get_current_api_key,
    require_org_admin,
    require_user,
    require_workspace_admin,
)
from runledger_api.models.approvals import Approval
from runledger_api.models.audit import AuditEvent
from runledger_api.models.budgets import Budget
from runledger_api.models.events import ProviderCall
from runledger_api.models.tenant import (
    ApiKey,
    MemberStatusEnum,
    TenantRoleEnum,
    TenantUser,
    User,
    Workspace,
    WorkspaceUser,
)
from runledger_api.schemas.auth import (
    AdminUserCreate,
    AdminUserUpdate,
    InviteUserRequest,
    OrgUserCreateResponse,
    OrgUserResponse,
    RoleUpdateRequest,
    UserResponse,
    UserUpdate,
    WorkspaceMemberResponse,
)
from runledger_api.services.passwords import (  # noqa: E402
    generate_temporary_password,
    hash_password_async,
    validate_password_policy,
    verify_password,
)
from runledger_api.services.sessions import (  # noqa: E402
    is_tenant_managed_user,
    revoke_user_sessions,
    tenant_workspace_ids,
)
from runledger_api.services.tenancy import log_audit  # noqa: E402

log = structlog.get_logger()
router = APIRouter(prefix="/users", tags=["users"])


class UserBudgetExposure(BaseModel):
    budget_id: str
    scope_type: str
    scope_id: str | None
    period_type: str
    limit_usd: Decimal
    is_active: bool


class UserFinanceSummary(BaseModel):
    user_id: str
    email: str
    full_name: str | None
    spend_30d_usd: Decimal
    spend_total_usd: Decimal
    run_count_30d: int
    call_count_30d: int
    budgets: list[UserBudgetExposure]


DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("/me", response_model=UserResponse)
async def get_me(
    workspace_user: Annotated[tuple[Workspace, User], Depends(require_user)],
) -> User:
    _, user = workspace_user
    return user


@router.put("/me", response_model=UserResponse)
async def update_me(
    body: UserUpdate,
    workspace_user: Annotated[tuple[Workspace, User], Depends(require_user)],
    current_key: Annotated[ApiKey, Depends(get_current_api_key)],
    db: DbDep,
) -> User:
    """Update your own profile. Changing the password requires the current one
    (unless the account has none yet) and signs out your other sessions."""
    _, user = workspace_user
    if body.full_name is not None:
        user.full_name = body.full_name
    if body.password is not None:
        if user.password_hash is not None and not await verify_password(
            body.current_password or "", user.password_hash
        ):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Current password is incorrect")
        validate_password_policy(body.password)
        user.password_hash = await hash_password_async(body.password)
        user.must_change_password = False
        await revoke_user_sessions(db, user.id, except_key_id=current_key.id)
    await db.commit()
    await db.refresh(user)
    return user


OrgAdminDep = Annotated[tuple[Any, ...], Depends(require_org_admin)]


def _org_user_response(
    u: User,
    org_role: Any | None,
    *,
    org_status: Any | None = None,
    can_manage_identity: bool = True,
) -> OrgUserResponse:
    return OrgUserResponse(
        id=u.id,
        email=u.email,
        full_name=u.full_name,
        is_active=u.is_active,
        email_verified=u.email_verified,
        org_role=(str(org_role) if org_role is not None else None),
        org_status=(str(org_status) if org_status is not None else None),
        last_login_at=u.last_login_at,
        created_at=u.created_at,
        can_manage_identity=can_manage_identity,
        must_change_password=bool(getattr(u, "must_change_password", False)),
    )


async def _assert_identity_manageable(
    db: AsyncSession, actor: User, target: User, tenant_id: uuid.UUID
) -> None:
    """Only the org that exclusively owns an identity (or a platform admin) may change
    its password, active or verified flags."""
    if actor.is_platform_admin:
        return
    if not await is_tenant_managed_user(db, target, tenant_id):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "This account is shared with another organization (or is a platform admin). "
            "You can manage its membership here, but not its password or account status.",
        )


@router.get("/all", response_model=list[OrgUserResponse])
async def list_org_users(
    auth: OrgAdminDep,
    db: DbDep,
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[OrgUserResponse]:
    """Every user in the caller's org — the identity registry (org-admin)."""
    workspace, actor, _tu = auth
    tenant_id = workspace.tenant_id
    tu_rows = (
        (await db.execute(select(TenantUser).where(TenantUser.tenant_id == tenant_id)))
        .scalars()
        .all()
    )
    role_by_user = {tu.user_id: tu.role for tu in tu_rows}
    status_by_user = {tu.user_id: tu.status for tu in tu_rows}
    ws_ids = (
        (await db.execute(select(Workspace.id).where(Workspace.tenant_id == tenant_id)))
        .scalars()
        .all()
    )
    user_ids = set(role_by_user.keys())
    if ws_ids:
        wu_users = (
            (
                await db.execute(
                    select(WorkspaceUser.user_id).where(
                        WorkspaceUser.workspace_id.in_(list(ws_ids))
                    )
                )
            )
            .scalars()
            .all()
        )
        user_ids.update(wu_users)
    if not user_ids:
        return []
    users = (
        (
            await db.execute(
                select(User)
                .where(User.id.in_(list(user_ids)))
                .order_by(User.created_at)
                .limit(limit)
                .offset(offset)
            )
        )
        .scalars()
        .all()
    )
    out = []
    for u in users:
        manageable = actor.is_platform_admin or await is_tenant_managed_user(db, u, tenant_id)
        out.append(
            _org_user_response(
                u,
                role_by_user.get(u.id),
                org_status=status_by_user.get(u.id),
                can_manage_identity=manageable,
            )
        )
    return out


@router.post("", status_code=status.HTTP_201_CREATED, response_model=OrgUserCreateResponse)
async def create_user(body: AdminUserCreate, auth: OrgAdminDep, db: DbDep) -> OrgUserCreateResponse:
    """Create an account and add it to the caller's org as a member (org-admin).

    The temporary password (generated unless supplied) is returned once and must be
    changed at first sign-in. Unless ``skip_verification`` is set, a verification
    email is sent and the user can sign in after confirming it.
    """
    workspace, actor, _tu = auth
    existing = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Email '{body.email}' already exists")
    temporary_password = body.temporary_password or generate_temporary_password()
    if body.temporary_password:
        validate_password_policy(body.temporary_password)
    user = User(
        email=body.email,
        password_hash=await hash_password_async(temporary_password),
        full_name=body.full_name or body.email.split("@")[0],
        is_active=True,
        email_verified=body.skip_verification,
        must_change_password=True,
    )
    db.add(user)
    await db.flush()
    # New users join the org as a plain member; grant workspace access separately.
    db.add(
        TenantUser(tenant_id=workspace.tenant_id, user_id=user.id, role=TenantRoleEnum.org_member)
    )
    log_audit(
        db,
        actor_user_id=actor.id,
        scope_type="tenant",
        scope_id=workspace.tenant_id,
        action="user.created",
        target_user_id=user.id,
    )
    if not body.skip_verification:
        from runledger_api.routers.login import issue_verification_email  # noqa: PLC0415

        await issue_verification_email(db, user)
    await db.commit()
    await db.refresh(user)
    log.info("user_created", user_id=str(user.id), verified=body.skip_verification)
    base = _org_user_response(user, TenantRoleEnum.org_member, org_status=MemberStatusEnum.active)
    return OrgUserCreateResponse(**base.model_dump(), temporary_password=temporary_password)


@router.put("/{user_id}", response_model=OrgUserResponse)
async def admin_update_user(
    user_id: uuid.UUID, body: AdminUserUpdate, auth: OrgAdminDep, db: DbDep
) -> OrgUserResponse:
    """Edit another user's identity (name / password / active / verified) — org-admin.

    Allowed only for accounts this org manages exclusively (see
    ``is_tenant_managed_user``); platform admins may edit anyone. Password resets set a
    temporary password and sign the user out everywhere; deactivation does too.
    """
    workspace, actor, _tu = auth
    if user_id == actor.id and body.is_active is False:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot deactivate yourself")
    membership = (
        await db.execute(
            select(TenantUser).where(
                TenantUser.tenant_id == workspace.tenant_id, TenantUser.user_id == user_id
            )
        )
    ).scalar_one_or_none()
    if membership is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User is not a member of your organization")
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    touches_identity = (
        body.password is not None
        or body.is_active is not None
        or body.email_verified is not None
        or body.full_name is not None
    )
    if touches_identity and user_id != actor.id:
        await _assert_identity_manageable(db, actor, user, workspace.tenant_id)
    changed: list[str] = []
    if body.full_name is not None:
        user.full_name = body.full_name
        changed.append("full_name")
    if body.password is not None:
        validate_password_policy(body.password)
        user.password_hash = await hash_password_async(body.password)
        user.must_change_password = user_id != actor.id
        await revoke_user_sessions(db, user.id)
        changed.append("password")
    if body.is_active is not None:
        user.is_active = body.is_active
        if not body.is_active:
            await revoke_user_sessions(db, user.id)
        changed.append(f"is_active={body.is_active}")
    if body.email_verified is not None:
        user.email_verified = body.email_verified
        changed.append(f"email_verified={body.email_verified}")
    if changed:
        log_audit(
            db,
            actor_user_id=actor.id,
            scope_type="tenant",
            scope_id=workspace.tenant_id,
            action="user.identity_updated",
            target_user_id=user.id,
            new_value=", ".join(changed),
        )
    await db.commit()
    await db.refresh(user)
    log.info("user_updated", user_id=str(user.id))
    return _org_user_response(user, membership.role, org_status=membership.status)


@router.get("/{user_id}", response_model=OrgUserResponse)
async def get_user(
    user_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)],
    db: DbDep,
) -> OrgUserResponse:
    """Get a specific user by ID (org-admin)."""
    workspace, _, __ = auth
    membership = (
        (
            await db.execute(
                select(TenantUser).where(
                    TenantUser.tenant_id == workspace.tenant_id, TenantUser.user_id == user_id
                )
            )
        )
        .scalars()
        .first()
    )
    if membership is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User is not a member of your organization")
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return _org_user_response(user, membership.role)


@router.get("/{user_id}/finance", response_model=UserFinanceSummary)
async def get_user_finance(
    user_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)],
    db: DbDep,
) -> UserFinanceSummary:
    """Get financial exposure for a platform user."""
    workspace, _, __ = auth
    membership = (
        (
            await db.execute(
                select(TenantUser).where(
                    TenantUser.tenant_id == workspace.tenant_id,
                    TenantUser.user_id == user_id,
                )
            )
        )
        .scalars()
        .first()
    )
    if membership is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User is not a member of your organization")
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    user_id_str = str(user_id)
    now = datetime.now(UTC)
    thirty_days_ago = now - timedelta(days=30)

    spend_30d_result = await db.execute(
        select(
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)),
            func.count(ProviderCall.id),
            func.count(func.distinct(ProviderCall.run_id)),
        ).where(
            ProviderCall.workspace_id == workspace.id,
            ProviderCall.end_user_id == user_id_str,
            ProviderCall.status == "success",
            func.date(ProviderCall.created_at) >= thirty_days_ago.date(),
        )
    )
    row_30d = spend_30d_result.one()
    spend_30d = row_30d[0]
    call_count_30d = row_30d[1]
    run_count_30d = row_30d[2]

    spend_total_result = await db.execute(
        select(
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)),
        ).where(
            ProviderCall.workspace_id == workspace.id,
            ProviderCall.end_user_id == user_id_str,
            ProviderCall.status == "success",
        )
    )
    spend_total = spend_total_result.scalar_one()

    budgets_result = await db.execute(
        select(Budget).where(
            Budget.workspace_id == workspace.id,
            Budget.scope_type == "end_user",
            Budget.scope_id == user_id_str,
        )
    )
    budgets = [
        UserBudgetExposure(
            budget_id=str(b.id),
            scope_type=b.scope_type,
            scope_id=b.scope_id,
            period_type=b.period_type,
            limit_usd=b.limit_usd,
            is_active=b.is_active,
        )
        for b in budgets_result.scalars().all()
    ]

    return UserFinanceSummary(
        user_id=user_id_str,
        email=user.email,
        full_name=user.full_name,
        spend_30d_usd=spend_30d,
        spend_total_usd=spend_total,
        run_count_30d=run_count_30d,
        call_count_30d=call_count_30d,
        budgets=budgets,
    )


@router.get("", response_model=list[WorkspaceMemberResponse])
async def list_workspace_users(
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: DbDep,
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[WorkspaceMemberResponse]:
    workspace, _, __ = auth
    result = await db.execute(
        select(WorkspaceUser, User)
        .join(User, WorkspaceUser.user_id == User.id)
        .where(WorkspaceUser.workspace_id == workspace.id)
        .order_by(WorkspaceUser.created_at)
        .limit(limit)
        .offset(offset)
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


@router.post("/invite", status_code=status.HTTP_201_CREATED, response_model=WorkspaceMemberResponse)
async def invite_user(
    body: InviteUserRequest,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: DbDep,
) -> WorkspaceMemberResponse:
    workspace, inviting_user, _ = auth

    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    temporary_password: str | None = None
    if user is None:
        temporary_password = body.temporary_password or generate_temporary_password()
        if body.temporary_password:
            validate_password_policy(body.temporary_password)
        user = User(
            email=body.email,
            password_hash=await hash_password_async(temporary_password),
            full_name=body.full_name,
            is_active=True,
            email_verified=body.skip_verification,
            must_change_password=True,
        )
        db.add(user)
        await db.flush()
        if not body.skip_verification:
            from runledger_api.routers.login import issue_verification_email  # noqa: PLC0415

            await issue_verification_email(db, user)
        db.add(
            TenantUser(
                tenant_id=workspace.tenant_id,
                user_id=user.id,
                role=TenantRoleEnum.org_member,
                invited_by=inviting_user.id,
            )
        )
    else:
        org_member = (
            await db.execute(
                select(TenantUser).where(
                    TenantUser.tenant_id == workspace.tenant_id,
                    TenantUser.user_id == user.id,
                    TenantUser.status == MemberStatusEnum.active,
                )
            )
        ).scalar_one_or_none()
        if org_member is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "This person is not an active member of your organization. Invite them to "
                "the organization first; they must accept before joining a workspace.",
            )

    existing = await db.execute(
        select(WorkspaceUser).where(
            WorkspaceUser.workspace_id == workspace.id, WorkspaceUser.user_id == user.id
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "User is already a member of this workspace")

    wu = WorkspaceUser(
        workspace_id=workspace.id, user_id=user.id, role=body.role, invited_by=inviting_user.id
    )
    db.add(wu)
    log_audit(
        db,
        actor_user_id=inviting_user.id,
        scope_type="workspace",
        scope_id=workspace.id,
        tenant_id=workspace.tenant_id,
        action="workspace.member.added",
        target_user_id=user.id,
        new_value=str(body.role),
    )
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
        temporary_password=temporary_password,
    )


@router.put("/{user_id}/role", response_model=WorkspaceMemberResponse)
async def update_workspace_role(
    user_id: uuid.UUID,
    body: RoleUpdateRequest,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: DbDep,
) -> WorkspaceMemberResponse:
    workspace, current_user, _ = auth
    if user_id == current_user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot change your own role")
    result = await db.execute(
        select(WorkspaceUser, User)
        .join(User, WorkspaceUser.user_id == User.id)
        .where(WorkspaceUser.workspace_id == workspace.id, WorkspaceUser.user_id == user_id)
    )
    row = result.first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found in this workspace")
    wu, u = row
    old_role = wu.role
    wu.role = body.role
    log_audit(
        db,
        actor_user_id=current_user.id,
        scope_type="workspace",
        scope_id=workspace.id,
        tenant_id=workspace.tenant_id,
        action="workspace.member.role_changed",
        target_user_id=user_id,
        old_value=str(old_role),
        new_value=str(body.role),
    )
    await db.commit()
    await db.refresh(wu)
    return WorkspaceMemberResponse(
        user_id=wu.user_id,
        workspace_id=wu.workspace_id,
        role=wu.role,
        email=u.email,
        full_name=u.full_name,
        is_active=u.is_active,
        last_login_at=u.last_login_at,
        joined_at=wu.created_at,
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_workspace_user(
    user_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: DbDep,
) -> None:
    workspace, current_user, _ = auth
    if user_id == current_user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot remove yourself from workspace")
    result = await db.execute(
        select(WorkspaceUser).where(
            WorkspaceUser.workspace_id == workspace.id, WorkspaceUser.user_id == user_id
        )
    )
    wu = result.scalar_one_or_none()
    if wu is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found in this workspace")
    log_audit(
        db,
        actor_user_id=current_user.id,
        scope_type="workspace",
        scope_id=workspace.id,
        tenant_id=workspace.tenant_id,
        action="workspace.member.removed",
        target_user_id=user_id,
        old_value=str(wu.role),
    )
    await db.delete(wu)
    await revoke_user_sessions(db, user_id, workspace_ids=[workspace.id])
    await db.commit()


@router.post("/{user_id}/sessions/revoke", status_code=status.HTTP_200_OK)
async def revoke_user_sessions_in_org(
    user_id: uuid.UUID, auth: OrgAdminDep, db: DbDep
) -> dict[str, Any]:
    """Sign a member out of every workspace in this org (org-admin)."""
    workspace, actor, _tu = auth
    membership = (
        await db.execute(
            select(TenantUser).where(
                TenantUser.tenant_id == workspace.tenant_id, TenantUser.user_id == user_id
            )
        )
    ).scalar_one_or_none()
    if membership is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User is not a member of your organization")
    revoked = await revoke_user_sessions(
        db, user_id, workspace_ids=await tenant_workspace_ids(db, workspace.tenant_id)
    )
    log_audit(
        db,
        actor_user_id=actor.id,
        scope_type="tenant",
        scope_id=workspace.tenant_id,
        action="user.sessions_revoked",
        target_user_id=user_id,
        new_value=str(revoked),
    )
    await db.commit()
    return {"revoked": revoked}


class UserGovernanceSummary(BaseModel):
    user_id: str
    email: str
    full_name: str | None
    approval_count: int
    recent_approvals: list[dict[str, Any]]
    audit_event_count: int
    recent_audit_events: list[dict[str, Any]]


@router.get("/{user_id}/governance", response_model=UserGovernanceSummary)
async def get_user_governance(
    user_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)],
    db: DbDep,
) -> UserGovernanceSummary:
    workspace, _, __ = auth
    membership = (
        (
            await db.execute(
                select(TenantUser).where(
                    TenantUser.tenant_id == workspace.tenant_id,
                    TenantUser.user_id == user_id,
                )
            )
        )
        .scalars()
        .first()
    )
    if membership is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User is not a member of your organization")
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    approval_count_result = await db.execute(
        select(func.count(Approval.id)).where(
            Approval.workspace_id == workspace.id,
            Approval.requested_by == user.email,
        )
    )
    approval_count = int(approval_count_result.scalar() or 0)

    recent_approvals_result = await db.execute(
        select(Approval)
        .where(
            Approval.workspace_id == workspace.id,
            Approval.requested_by == user.email,
        )
        .order_by(Approval.created_at.desc())
        .limit(5)
    )
    recent_approvals = [
        {
            "id": str(a.id),
            "request_type": a.request_type,
            "status": a.status,
            "created_at": a.created_at.isoformat(),
        }
        for a in recent_approvals_result.scalars().all()
    ]

    audit_count_result = await db.execute(
        select(func.count(AuditEvent.id)).where(
            AuditEvent.workspace_id == workspace.id,
            AuditEvent.actor_user_id == user_id,
        )
    )
    audit_event_count = int(audit_count_result.scalar() or 0)

    recent_audit_result = await db.execute(
        select(AuditEvent)
        .where(
            AuditEvent.workspace_id == workspace.id,
            AuditEvent.actor_user_id == user_id,
        )
        .order_by(AuditEvent.created_at.desc())
        .limit(5)
    )
    recent_audit_events = [
        {
            "id": str(e.id),
            "action": e.action,
            "target_type": e.target_type,
            "created_at": e.created_at.isoformat(),
        }
        for e in recent_audit_result.scalars().all()
    ]

    return UserGovernanceSummary(
        user_id=str(user_id),
        email=user.email,
        full_name=user.full_name,
        approval_count=approval_count,
        recent_approvals=recent_approvals,
        audit_event_count=audit_event_count,
        recent_audit_events=recent_audit_events,
    )
