"""Workspace-level user management. Requires dashboard session."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

import bcrypt
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import require_org_admin, require_user, require_workspace_admin
from runledger_api.models.tenant import (
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
    OrgUserResponse,
    RoleUpdateRequest,
    UserResponse,
    UserUpdate,
    WorkspaceMemberResponse,
)

log = structlog.get_logger()
router = APIRouter(prefix="/users", tags=["users"])

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
    db: DbDep,
) -> User:
    _, user = workspace_user
    if body.full_name is not None:
        user.full_name = body.full_name
    if body.password is not None:
        user.password_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    await db.commit()
    await db.refresh(user)
    return user


OrgAdminDep = Annotated[tuple[Any, ...], Depends(require_org_admin)]


def _org_user_response(u: User, org_role: Any | None) -> OrgUserResponse:
    return OrgUserResponse(
        id=u.id,
        email=u.email,
        full_name=u.full_name,
        is_active=u.is_active,
        email_verified=u.email_verified,
        org_role=(org_role.value if org_role is not None else None),
        last_login_at=u.last_login_at,
        created_at=u.created_at,
    )


@router.get("/all", response_model=list[OrgUserResponse])
async def list_org_users(auth: OrgAdminDep, db: DbDep) -> list[OrgUserResponse]:
    """Every user in the caller's org — the identity registry (org-admin)."""
    workspace, _u, _tu = auth
    tenant_id = workspace.tenant_id
    tu_rows = (
        (await db.execute(select(TenantUser).where(TenantUser.tenant_id == tenant_id)))
        .scalars()
        .all()
    )
    role_by_user = {tu.user_id: tu.role for tu in tu_rows}
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
                select(User).where(User.id.in_(list(user_ids))).order_by(User.created_at)
            )
        )
        .scalars()
        .all()
    )
    return [_org_user_response(u, role_by_user.get(u.id)) for u in users]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=OrgUserResponse)
async def create_user(body: AdminUserCreate, auth: OrgAdminDep, db: DbDep) -> OrgUserResponse:
    """Create a user identity and add them to the caller's org as a member (org-admin).

    ``skip_verification`` (default true here) marks the account verified so it can sign
    in immediately when no SMTP is configured.
    """
    workspace, _u, _tu = auth
    existing = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Email '{body.email}' already exists")
    pw_hash = bcrypt.hashpw(body.temporary_password.encode(), bcrypt.gensalt()).decode()
    user = User(
        email=body.email,
        password_hash=pw_hash,
        full_name=body.full_name or body.email.split("@")[0],
        is_active=True,
        email_verified=body.skip_verification,
    )
    db.add(user)
    await db.flush()
    # New users join the org as a plain member; grant workspace access separately.
    db.add(
        TenantUser(tenant_id=workspace.tenant_id, user_id=user.id, role=TenantRoleEnum.org_member)
    )
    await db.commit()
    await db.refresh(user)
    log.info("user_created", user_id=str(user.id), verified=body.skip_verification)
    return _org_user_response(user, TenantRoleEnum.org_member)


@router.put("/{user_id}", response_model=OrgUserResponse)
async def admin_update_user(
    user_id: uuid.UUID, body: AdminUserUpdate, auth: OrgAdminDep, db: DbDep
) -> OrgUserResponse:
    """Edit another user's identity (name / password / active / verified) — org-admin."""
    workspace, _u, _tu = auth
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
    if body.full_name is not None:
        user.full_name = body.full_name
    if body.password is not None:
        user.password_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.email_verified is not None:
        user.email_verified = body.email_verified
    await db.commit()
    await db.refresh(user)
    log.info("user_updated", user_id=str(user.id))
    return _org_user_response(user, membership.role)


@router.get("", response_model=list[WorkspaceMemberResponse])
async def list_workspace_users(
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: DbDep,
) -> list[WorkspaceMemberResponse]:
    workspace, _, __ = auth
    result = await db.execute(
        select(WorkspaceUser, User)
        .join(User, WorkspaceUser.user_id == User.id)
        .where(WorkspaceUser.workspace_id == workspace.id)
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


@router.post("/invite", status_code=status.HTTP_201_CREATED, response_model=WorkspaceMemberResponse)
async def invite_user(
    body: InviteUserRequest,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: DbDep,
) -> WorkspaceMemberResponse:
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
    wu.role = body.role
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
    await db.delete(wu)
    await db.commit()
