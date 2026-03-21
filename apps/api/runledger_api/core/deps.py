from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.config import settings
from runledger_api.core.db import get_db
from runledger_api.models.tenant import (
    ApiKey,
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
from runledger_api.services.auth import verify_api_key

_bearer = HTTPBearer()

# Roles that have org-admin level access
_ORG_ADMIN_ROLES = {TenantRoleEnum.org_admin, TenantRoleEnum.org_manager}


async def get_current_workspace(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Workspace:
    """Validates Bearer API key and returns the associated Workspace."""
    api_key = await verify_api_key(credentials.credentials, db)
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    result = await db.execute(select(Workspace).where(Workspace.id == api_key.workspace_id))
    workspace = result.scalar_one_or_none()
    if workspace is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Workspace not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Check workspace status
    if workspace.status == WorkspaceStatusEnum.suspended:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This workspace is suspended",
        )
    if workspace.status == WorkspaceStatusEnum.archived:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This workspace is archived",
        )
    # Check parent tenant status
    tenant = (await db.execute(select(Tenant).where(Tenant.id == workspace.tenant_id))).scalar_one_or_none()
    if tenant is not None and tenant.status == TenantStatusEnum.suspended:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This organization is suspended",
        )
    return workspace


async def get_current_api_key(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiKey:
    """Returns the validated ApiKey object."""
    api_key = await verify_api_key(credentials.credentials, db)
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return api_key


async def get_current_user(
    api_key: Annotated[ApiKey, Depends(get_current_api_key)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User | None:
    """Returns the User who owns the session key, or None for non-session keys."""
    if not api_key.is_session or not api_key.created_by:
        return None
    result = await db.execute(select(User).where(User.email == api_key.created_by))
    return result.scalar_one_or_none()


async def require_user(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    user: Annotated[User | None, Depends(get_current_user)],
) -> tuple[Workspace, User]:
    """Requires a session-authenticated user (not just an API key)."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This endpoint requires a user session (dashboard login)",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )
    return workspace, user


async def require_platform_admin(
    workspace_user: Annotated[tuple[Workspace, User], Depends(require_user)],
) -> tuple[Workspace, User]:
    """Requires is_platform_admin=True on the user."""
    workspace, user = workspace_user
    if not user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform admin access required",
        )
    return workspace, user


async def _get_tenant_user(
    user_id: uuid.UUID, tenant_id: uuid.UUID, db: AsyncSession
) -> TenantUser | None:
    result = await db.execute(
        select(TenantUser).where(
            TenantUser.user_id == user_id,
            TenantUser.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


async def _get_workspace_user(
    user_id: uuid.UUID, workspace_id: uuid.UUID, db: AsyncSession
) -> WorkspaceUser | None:
    result = await db.execute(
        select(WorkspaceUser).where(
            WorkspaceUser.user_id == user_id,
            WorkspaceUser.workspace_id == workspace_id,
        )
    )
    return result.scalar_one_or_none()


async def require_org_admin(
    workspace_user: Annotated[tuple[Workspace, User], Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> tuple[Workspace, User, TenantUser | None]:
    """Requires org_admin role in the current tenant (or platform_admin bypasses)."""
    workspace, user = workspace_user
    if user.is_platform_admin:
        return workspace, user, None
    tu = await _get_tenant_user(user.id, workspace.tenant_id, db)
    if tu is None or tu.role not in _ORG_ADMIN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization admin access required",
        )
    return workspace, user, tu


async def require_workspace_admin(
    workspace_user: Annotated[tuple[Workspace, User], Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> tuple[Workspace, User, WorkspaceUser | None]:
    """Requires workspace_admin role (or org_admin/platform_admin bypasses)."""
    workspace, user = workspace_user
    if user.is_platform_admin:
        return workspace, user, None
    tu = await _get_tenant_user(user.id, workspace.tenant_id, db)
    if tu and tu.role in _ORG_ADMIN_ROLES:
        return workspace, user, None
    wu = await _get_workspace_user(user.id, workspace.id, db)
    if wu is None or wu.role != WorkspaceRoleEnum.workspace_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Workspace admin access required",
        )
    return workspace, user, wu


async def require_member(
    workspace_user: Annotated[tuple[Workspace, User], Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> tuple[Workspace, User, WorkspaceUser | None]:
    """Requires at least member role (not viewer)."""
    workspace, user = workspace_user
    if user.is_platform_admin:
        return workspace, user, None
    tu = await _get_tenant_user(user.id, workspace.tenant_id, db)
    if tu and tu.role in _ORG_ADMIN_ROLES:
        return workspace, user, None
    wu = await _get_workspace_user(user.id, workspace.id, db)
    if wu is None or wu.role == WorkspaceRoleEnum.viewer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Member access required",
        )
    return workspace, user, wu


async def resolve_workspace_ids(
    workspace: Workspace,
    tenant_id: uuid.UUID | None,
    user: User | None,
    db: AsyncSession,
) -> list[uuid.UUID]:
    """
    Returns workspace_ids to filter on.
    - tenant_id=None → [workspace.id]
    - tenant_id provided + org_admin → all workspaces in that tenant
    """
    if tenant_id is None:
        return [workspace.id]
    if user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User session required for cross-workspace queries")
    if not user.is_platform_admin:
        tu = await _get_tenant_user(user.id, tenant_id, db)
        if tu is None or tu.role not in _ORG_ADMIN_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organization admin role required for cross-workspace queries",
            )
    result = await db.execute(select(Workspace.id).where(Workspace.tenant_id == tenant_id))
    return list(result.scalars().all())


async def require_admin(x_admin_secret: Annotated[str, Header()]) -> None:
    """Validates X-Admin-Secret header for admin-only endpoints (backward compat)."""
    if x_admin_secret != settings.effective_admin_secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin secret",
        )
