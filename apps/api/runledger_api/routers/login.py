"""
Public login endpoints for the NextAuth dashboard.

POST /auth/login          — email + password
POST /auth/switch-workspace

POST /auth/login — verifies email + password, generates a short-lived
dashboard session API key, and returns it in the response body.
NextAuth stores the raw key in the encrypted JWT session.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import bcrypt
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import require_user
from runledger_api.models.tenant import (
    ApiKey,
    EnvironmentEnum,
    Tenant,
    TenantUser,
    User,
    Workspace,
    WorkspaceUser,
)
from runledger_api.schemas.runs import LoginRequest, LoginResponse
from runledger_api.services.auth import generate_api_key

log = structlog.get_logger()

router = APIRouter(tags=["auth"])

DbDep = Annotated[AsyncSession, Depends(get_db)]

_SESSION_EXPIRY = timedelta(days=30)


@router.post("/auth/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: DbDep) -> LoginResponse:
    """
    Authenticate with email + password.
    Returns a workspace-scoped API key for the dashboard session.
    """
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if (
        user is None
        or user.password_hash is None
        or not bcrypt.checkpw(body.password.encode(), user.password_hash.encode())
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is deactivated")

    if not user.email_verified:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Please verify your email before signing in")

    # Load all workspace memberships
    wu_result = await db.execute(
        select(WorkspaceUser)
        .where(WorkspaceUser.user_id == user.id)
        .order_by(WorkspaceUser.created_at)
    )
    workspace_users = list(wu_result.scalars().all())

    if not workspace_users:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User has no workspace access")

    # Pick requested workspace or default to first
    workspace_user = workspace_users[0]
    if body.workspace_id:
        for wu in workspace_users:
            if str(wu.workspace_id) == body.workspace_id:
                workspace_user = wu
                break

    workspace = await db.get(Workspace, workspace_user.workspace_id)
    if workspace is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Workspace not found")
    tenant = await db.get(Tenant, workspace.tenant_id)
    if tenant is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Organization not found")

    # Load tenant role
    tu_result = await db.execute(
        select(TenantUser).where(
            TenantUser.user_id == user.id,
            TenantUser.tenant_id == workspace.tenant_id,
        )
    )
    tenant_user = tu_result.scalar_one_or_none()
    tenant_role = tenant_user.role.value if tenant_user else None
    workspace_role = workspace_user.role.value

    # All workspaces this user can access
    workspace_ids = [str(wu.workspace_id) for wu in workspace_users]

    # Update last login
    user.last_login_at = datetime.now(UTC)

    # Generate session key
    raw_key, key_hash, key_prefix = generate_api_key(EnvironmentEnum.dev)
    session_key = ApiKey(
        workspace_id=workspace.id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name="dashboard-session",
        scopes=[],
        expires_at=datetime.now(UTC) + _SESSION_EXPIRY,
        is_session=True,
        created_by=user.email,
    )
    db.add(session_key)
    await db.commit()

    log.info(
        "dashboard_login",
        user_id=str(user.id),
        workspace_id=str(workspace.id),
        tenant_id=str(workspace.tenant_id),
        is_platform_admin=user.is_platform_admin,
    )

    return LoginResponse(
        email=user.email,
        full_name=user.full_name,
        user_id=str(user.id),
        workspace_id=str(workspace.id),
        workspace_name=workspace.name,
        tenant_id=str(workspace.tenant_id),
        tenant_name=tenant.name,
        api_key=raw_key,
        is_platform_admin=user.is_platform_admin,
        tenant_role=tenant_role,
        workspace_role=workspace_role,
        workspace_ids=workspace_ids,
    )


class SwitchWorkspaceRequest(BaseModel):
    workspace_id: str


@router.post("/auth/switch-workspace", response_model=LoginResponse)
async def switch_workspace(
    body: SwitchWorkspaceRequest,
    auth: Annotated[tuple[Any, ...], Depends(require_user)],
    db: DbDep,
) -> LoginResponse:
    """
    Switch to a different workspace without re-entering credentials.
    Validates the user has access, issues a new session API key, returns full session data.
    """
    _, user = auth
    target_ws_id = uuid.UUID(body.workspace_id)

    # Verify user has access to the target workspace
    wu_result = await db.execute(
        select(WorkspaceUser).where(
            WorkspaceUser.workspace_id == target_ws_id,
            WorkspaceUser.user_id == user.id,
        )
    )
    workspace_user = wu_result.scalar_one_or_none()
    if workspace_user is None and not user.is_platform_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No access to this workspace")

    target_workspace = await db.get(Workspace, target_ws_id)
    if target_workspace is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")
    tenant = await db.get(Tenant, target_workspace.tenant_id)
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found")

    # Load tenant role
    tu_result = await db.execute(
        select(TenantUser).where(
            TenantUser.user_id == user.id,
            TenantUser.tenant_id == target_workspace.tenant_id,
        )
    )
    tenant_user = tu_result.scalar_one_or_none()
    tenant_role = tenant_user.role.value if tenant_user else None
    workspace_role = workspace_user.role.value if workspace_user else None

    # All workspaces this user can access
    wu_all = await db.execute(
        select(WorkspaceUser)
        .where(WorkspaceUser.user_id == user.id)
        .order_by(WorkspaceUser.created_at)
    )
    workspace_ids = [str(wu.workspace_id) for wu in wu_all.scalars().all()]

    # Generate new session key for target workspace
    raw_key, key_hash, key_prefix = generate_api_key(EnvironmentEnum.dev)
    session_key = ApiKey(
        workspace_id=target_workspace.id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name="dashboard-session",
        scopes=[],
        expires_at=datetime.now(UTC) + _SESSION_EXPIRY,
        is_session=True,
        created_by=user.email,
    )
    db.add(session_key)
    await db.commit()

    log.info("workspace_switch", user_id=str(user.id), workspace_id=str(target_workspace.id))

    return LoginResponse(
        email=user.email,
        full_name=user.full_name,
        user_id=str(user.id),
        workspace_id=str(target_workspace.id),
        workspace_name=target_workspace.name,
        tenant_id=str(target_workspace.tenant_id),
        tenant_name=tenant.name,
        api_key=raw_key,
        is_platform_admin=user.is_platform_admin,
        tenant_role=tenant_role,
        workspace_role=workspace_role,
        workspace_ids=workspace_ids,
    )


# ── Unsubscribe / Resubscribe ──────────────────────────────────────────────────


@router.get("/auth/unsubscribe")
async def unsubscribe_email(token: str, db: DbDep) -> dict[str, Any]:
    """Unsubscribe a user from email notifications using their unsubscribe token."""
    result = await db.execute(select(User).where(User.email_unsubscribe_token == token))
    user = result.scalar_one_or_none()
    if user is None:
        return {"ok": False, "message": "Invalid or expired token"}
    user.email_notifications_enabled = False
    await db.commit()
    return {"ok": True, "message": "Unsubscribed successfully"}


@router.post("/auth/resubscribe")
async def resubscribe_email(
    auth: Annotated[Any, Depends(require_user)],
    db: DbDep,
) -> dict[str, Any]:
    """Re-enable email notifications for the authenticated user."""
    user_obj: User = auth[1] if isinstance(auth, (tuple, list)) else auth
    user_obj.email_notifications_enabled = True
    await db.commit()
    return {"ok": True, "message": "Resubscribed successfully"}
