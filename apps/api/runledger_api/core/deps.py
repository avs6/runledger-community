from __future__ import annotations

import hmac
import uuid
from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.config import settings
from runledger_api.core.db import get_db
from runledger_api.core.scopes import key_allows, required_scopes
from runledger_api.models.tenant import (
    ApiKey,
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
from runledger_api.services.audit import Actor, actor_from_api_key, set_actor
from runledger_api.services.auth import verify_api_key
from runledger_api.services.security import apply_tenant_context, authenticate_oidc_token
from runledger_api.services.sessions import ORG_ADMIN_ROLES, has_workspace_access

_bearer = HTTPBearer()

# Roles that have org-admin level access
_ORG_ADMIN_ROLES = set(ORG_ADMIN_ROLES)

_SESSION_INVALID = "Session is no longer valid. Please sign in again."


async def _validate_workspace_status(workspace: Workspace, db: AsyncSession) -> Workspace:
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
    tenant = (
        await db.execute(select(Tenant).where(Tenant.id == workspace.tenant_id))
    ).scalar_one_or_none()
    if tenant is not None and tenant.status == TenantStatusEnum.suspended:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This organization is suspended",
        )
    return workspace


async def _session_owner(api_key: ApiKey, db: AsyncSession) -> User | None:
    """Resolve the owner of a session key (``user_id``; creator email for old keys)."""
    if api_key.user_id is not None:
        return await db.get(User, api_key.user_id)
    if api_key.created_by:
        return (
            await db.execute(select(User).where(User.email == api_key.created_by))
        ).scalar_one_or_none()
    return None


async def authorize_api_key(api_key: ApiKey, db: AsyncSession) -> tuple[Workspace, User | None]:
    """Apply the access rules every API-key credential must pass, wherever it is used.

    Shared by the control-plane API and the gateway (runtime preflight, passthrough):

    - the key's workspace must exist and not be suspended or archived, and its org
      must not be suspended (403);
    - a dashboard session key is re-validated against its owner: the account must be
      active and still have access to the workspace (401 otherwise).

    Returns the workspace and, for session keys, the owning user.
    """
    result = await db.execute(select(Workspace).where(Workspace.id == api_key.workspace_id))
    workspace = result.scalar_one_or_none()
    if workspace is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Workspace not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    owner: User | None = None
    if api_key.is_session:
        owner = await _session_owner(api_key, db)
        if (
            owner is None
            or not owner.is_active
            or not await has_workspace_access(db, owner, workspace)
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=_SESSION_INVALID,
                headers={"WWW-Authenticate": "Bearer"},
            )
    return await _validate_workspace_status(workspace, db), owner


async def validate_workspace_status(workspace: Workspace, db: AsyncSession) -> Workspace:
    """Public alias: reject suspended/archived workspaces and suspended orgs (403)."""
    return await _validate_workspace_status(workspace, db)


def require_key_scope(api_key: ApiKey | None, needed: frozenset[str]) -> None:
    """Raise 403 when a workload key's scopes do not cover ``needed`` (any one of).

    Session keys and OIDC tokens (``api_key`` None) are not scope-limited.
    """
    if api_key is None or api_key.is_session:
        return
    if not key_allows(api_key.scopes, needed):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"API key scope does not allow this request (needs: {' or '.join(sorted(needed))})"
            ),
        )


def _enforce_route_scope(request: Request, api_key: ApiKey) -> None:
    route = request.scope.get("route")
    route_path = getattr(route, "path", None) or request.url.path
    needed = required_scopes(request.method, route_path)
    if needed is not None:
        require_key_scope(api_key, needed)


async def _verified_key(request: Request, token: str, db: AsyncSession) -> ApiKey | None:
    """Verify an API key once per request and cache the result on request.state.

    Workload keys are also checked against the scopes this route needs.
    """
    if getattr(request.state, "api_key_checked", False):
        return getattr(request.state, "api_key", None)
    api_key = await verify_api_key(token, db)
    request.state.api_key_checked = True
    request.state.api_key = api_key
    if api_key is not None:
        _enforce_route_scope(request, api_key)
        # Audit actor for every event this request writes (review S-16).
        set_actor(
            actor_from_api_key(api_key, client_ip=request.client.host if request.client else None)
        )
    return api_key


async def get_current_workspace(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Workspace:
    """Validates Bearer token (API key or OIDC JWT) and returns the associated Workspace.

    Dashboard session keys are additionally checked against their owner: the account
    must be active and must still have access to the workspace (active membership or
    an active org-level role). Otherwise the session is rejected with 401.
    """
    token = credentials.credentials

    # Try API key first
    api_key = await _verified_key(request, token, db)
    if api_key is not None:
        workspace, owner = await authorize_api_key(api_key, db)
        # Postgres RLS context: org-wide for session keys, workspace-pinned for
        # workload keys (tr-security defence in depth).
        await apply_tenant_context(db, workspace, pin_workspace=not api_key.is_session)
        if owner is not None:
            request.state.session_user = owner
            set_actor(
                actor_from_api_key(
                    api_key,
                    user=owner,
                    client_ip=request.client.host if request.client else None,
                )
            )
        return workspace

    # Fallback: try OIDC bearer token validation
    oidc_result = await authenticate_oidc_token(token, db)
    if oidc_result is not None:
        oidc_user = getattr(oidc_result, "user", None)
        set_actor(
            Actor(
                kind="oidc",
                user_id=getattr(oidc_user, "id", None),
                label=getattr(oidc_user, "email", None),
                client_ip=request.client.host if request.client else None,
            )
        )
        await apply_tenant_context(db, oidc_result.workspace, pin_workspace=False)
        return await _validate_workspace_status(oidc_result.workspace, db)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or revoked API key",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_api_key(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiKey:
    """Returns the validated ApiKey object."""
    api_key = await _verified_key(request, credentials.credentials, db)
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return api_key


async def get_current_user(
    request: Request,
    api_key: Annotated[ApiKey, Depends(get_current_api_key)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User | None:
    """Returns the User who owns the session key, or None for non-session keys."""
    if not api_key.is_session:
        return None
    cached = getattr(request.state, "session_user", None)
    if cached is not None:
        return cached
    return await _session_owner(api_key, db)


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
    """Active org membership only — suspended/invited members hold no role power."""
    result = await db.execute(
        select(TenantUser).where(
            TenantUser.user_id == user_id,
            TenantUser.tenant_id == tenant_id,
            TenantUser.status == MemberStatusEnum.active,
        )
    )
    return result.scalar_one_or_none()


async def _get_workspace_user(
    user_id: uuid.UUID, workspace_id: uuid.UUID, db: AsyncSession
) -> WorkspaceUser | None:
    """Active workspace membership only."""
    result = await db.execute(
        select(WorkspaceUser).where(
            WorkspaceUser.user_id == user_id,
            WorkspaceUser.workspace_id == workspace_id,
            WorkspaceUser.status == MemberStatusEnum.active,
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


_READ_ONLY_WORKSPACE_ROLES = frozenset({WorkspaceRoleEnum.viewer})


async def can_write_workspace(db: AsyncSession, user: User, workspace: Workspace) -> bool:
    """Whether a dashboard user may change data in ``workspace``.

    Platform admins, org admins/managers, and workspace members with any role other
    than ``viewer`` may write. Org billing admins and auditors see every workspace in
    the org but read only, unless they also hold a writable workspace role.
    """
    if user.is_platform_admin:
        return True
    tu = await _get_tenant_user(user.id, workspace.tenant_id, db)
    if tu is not None and tu.role in _ORG_ADMIN_ROLES:
        return True
    wu = await _get_workspace_user(user.id, workspace.id, db)
    return wu is not None and wu.role not in _READ_ONLY_WORKSPACE_ROLES


async def require_workspace_writer(
    request: Request,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Workspace:
    """Allow writes from workload credentials and from users with a writable role.

    Workload API keys and OIDC workload tokens are workspace credentials and keep full
    write access (SDK, OTLP, ingest, automation). Dashboard sessions are checked
    against the signed-in user's role: viewers and read-only org roles get 403.
    """
    api_key = getattr(request.state, "api_key", None)
    if api_key is None or not api_key.is_session:
        return workspace
    user = getattr(request.state, "session_user", None) or await _session_owner(api_key, db)
    if user is None or not await can_write_workspace(db, user, workspace):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your role in this workspace is read-only",
        )
    return workspace


def _org_role_or_workspace_admin(
    org_roles: frozenset[TenantRoleEnum], detail: str
) -> Callable[..., Awaitable[tuple[Workspace, User, TenantUser | None]]]:
    """Dependency factory: workspace admin, platform admin, or one of ``org_roles``."""

    async def _dep(
        workspace_user: Annotated[tuple[Workspace, User], Depends(require_user)],
        db: Annotated[AsyncSession, Depends(get_db)],
    ) -> tuple[Workspace, User, TenantUser | None]:
        workspace, user = workspace_user
        if user.is_platform_admin:
            return workspace, user, None
        tu = await _get_tenant_user(user.id, workspace.tenant_id, db)
        if tu is not None and tu.role in org_roles:
            return workspace, user, tu
        wu = await _get_workspace_user(user.id, workspace.id, db)
        if wu is not None and wu.role == WorkspaceRoleEnum.workspace_admin:
            return workspace, user, tu
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

    return _dep


# Billing admins read and export billing/chargeback data across the org's workspaces.
require_billing_access = _org_role_or_workspace_admin(
    frozenset(
        {TenantRoleEnum.org_admin, TenantRoleEnum.org_manager, TenantRoleEnum.org_billing_admin}
    ),
    "Billing access required",
)
# Auditors read audit logs and the governance audit pack across the org's workspaces.
require_audit_access = _org_role_or_workspace_admin(
    frozenset({TenantRoleEnum.org_admin, TenantRoleEnum.org_manager, TenantRoleEnum.org_auditor}),
    "Audit access required",
)


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
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User session required for cross-workspace queries",
        )
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
    if not hmac.compare_digest(x_admin_secret.encode(), settings.effective_admin_secret.encode()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin secret",
        )
    set_actor(Actor(kind="admin_secret", label="x-admin-secret"))


def _internal_channel(
    token: str | None, admin_secret: str | None, channels: dict[str, str]
) -> None:
    configured = {label: value for label, value in channels.items() if value}
    if configured:
        for label, expected in configured.items():
            if token and hmac.compare_digest(token.encode(), expected.encode()):
                set_actor(Actor(kind="service", label=label))
                return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid internal token")
    if admin_secret and hmac.compare_digest(
        admin_secret.encode(), settings.effective_admin_secret.encode()
    ):
        set_actor(Actor(kind="service", label="internal (admin secret)"))
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid internal token")


async def require_runtime_key_resolver(
    x_gateway_internal_token: Annotated[str | None, Header()] = None,
    x_admin_secret: Annotated[str | None, Header()] = None,
) -> None:
    """``/gateway/runtime/internal/resolve-api-key``: gateway-rs or mcp-gateway, each
    with its own token (GATEWAY_INTERNAL_TOKEN / MCP_INTERNAL_TOKEN)."""
    _internal_channel(
        x_gateway_internal_token,
        x_admin_secret,
        {"gateway-rs": settings.gateway_internal_token, "mcp-gateway": settings.mcp_internal_token},
    )


async def require_gateway_internal(
    x_gateway_internal_token: Annotated[str | None, Header()] = None,
    x_admin_secret: Annotated[str | None, Header()] = None,
) -> None:
    """Auth for gateway-rs -> API internal calls (review tr-security, cd:S-05).

    With GATEWAY_INTERNAL_TOKEN set, only ``x-gateway-internal-token`` is accepted,
    so the shared admin secret no longer authorizes the runtime channel. Without
    it, the legacy ``x-admin-secret`` is still accepted for compatibility.
    """
    _internal_channel(
        x_gateway_internal_token, x_admin_secret, {"gateway-rs": settings.gateway_internal_token}
    )
