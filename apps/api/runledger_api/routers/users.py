"""Workspace-level user management. Requires dashboard session."""

from __future__ import annotations

import uuid
from typing import Annotated

import bcrypt
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import require_user, require_workspace_admin
from runledger_api.models.tenant import User, Workspace, WorkspaceUser
from runledger_api.schemas.auth import (
    InviteUserRequest,
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


@router.get("", response_model=list[WorkspaceMemberResponse])
async def list_workspace_users(
    auth: Annotated[tuple, Depends(require_workspace_admin)],
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
            user_id=wu.user_id, workspace_id=wu.workspace_id, role=wu.role,
            email=u.email, full_name=u.full_name, is_active=u.is_active,
            last_login_at=u.last_login_at, joined_at=wu.created_at,
        )
        for wu, u in result.all()
    ]


@router.post("/invite", status_code=status.HTTP_201_CREATED, response_model=WorkspaceMemberResponse)
async def invite_user(
    body: InviteUserRequest,
    auth: Annotated[tuple, Depends(require_workspace_admin)],
    db: DbDep,
) -> WorkspaceMemberResponse:
    workspace, inviting_user, _ = auth

    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user is None:
        pw_hash = bcrypt.hashpw(body.temporary_password.encode(), bcrypt.gensalt()).decode()
        user = User(email=body.email, password_hash=pw_hash, full_name=body.full_name, is_active=True)
        db.add(user)
        await db.flush()

    existing = await db.execute(
        select(WorkspaceUser).where(
            WorkspaceUser.workspace_id == workspace.id, WorkspaceUser.user_id == user.id
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "User is already a member of this workspace")

    wu = WorkspaceUser(workspace_id=workspace.id, user_id=user.id, role=body.role, invited_by=inviting_user.id)
    db.add(wu)
    await db.commit()
    await db.refresh(wu)
    return WorkspaceMemberResponse(
        user_id=wu.user_id, workspace_id=wu.workspace_id, role=wu.role,
        email=user.email, full_name=user.full_name, is_active=user.is_active,
        last_login_at=user.last_login_at, joined_at=wu.created_at,
    )


@router.put("/{user_id}/role", response_model=WorkspaceMemberResponse)
async def update_workspace_role(
    user_id: uuid.UUID,
    body: RoleUpdateRequest,
    auth: Annotated[tuple, Depends(require_workspace_admin)],
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
        user_id=wu.user_id, workspace_id=wu.workspace_id, role=wu.role,
        email=u.email, full_name=u.full_name, is_active=u.is_active,
        last_login_at=u.last_login_at, joined_at=wu.created_at,
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_workspace_user(
    user_id: uuid.UUID,
    auth: Annotated[tuple, Depends(require_workspace_admin)],
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
