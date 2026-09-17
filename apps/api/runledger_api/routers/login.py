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
from runledger_api.models.security import LDAPProvider, OAuth2Provider, OIDCProvider
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
from runledger_api.schemas.security import (
    AuthProviderInfo,
    AuthProvidersResponse,
    LDAPLoginRequest,
    OAuth2AuthorizeResponse,
    OAuth2CallbackRequest,
    OIDCAuthorizeResponse,
    OIDCCallbackRequest,
)
from runledger_api.services.auth import generate_api_key
from runledger_api.services.security import (
    authenticate_ldap,
    build_oauth2_authorize_url,
    build_oidc_authorize_url,
    exchange_oauth2_code,
    exchange_oidc_code,
    fetch_oauth2_userinfo,
    find_or_create_user_from_ldap,
    find_or_create_user_from_oauth2,
    find_or_create_user_from_oidc,
    generate_oauth2_state,
    generate_oidc_state,
    validate_oauth2_state,
    validate_oidc_id_token,
    validate_oidc_state,
)

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


# ── OIDC / External Auth ──────────────────────────────────────────────────────


@router.get("/auth/providers", response_model=AuthProvidersResponse)
async def list_auth_providers(
    db: DbDep,
    tenant_id: str | None = None,
    workspace_id: str | None = None,
) -> AuthProvidersResponse:
    """Public endpoint: lists available external login providers."""
    tid = uuid.UUID(tenant_id) if tenant_id else None
    wid = uuid.UUID(workspace_id) if workspace_id else None

    result_providers: list[AuthProviderInfo] = []

    # OIDC providers (those with client_id for login)
    oidc_query = select(OIDCProvider).where(
        OIDCProvider.is_active.is_(True),
        OIDCProvider.client_id.isnot(None),
    )
    if tid:
        oidc_query = oidc_query.where(OIDCProvider.tenant_id == tid)
    elif wid:
        oidc_query = oidc_query.where(OIDCProvider.workspace_id == wid)
    for p in (await db.execute(oidc_query)).scalars().all():
        result_providers.append(AuthProviderInfo(id=p.id, name=p.name, type="oidc"))

    # OAuth2 providers
    oauth2_query = select(OAuth2Provider).where(OAuth2Provider.is_active.is_(True))
    if tid:
        oauth2_query = oauth2_query.where(OAuth2Provider.tenant_id == tid)
    elif wid:
        oauth2_query = oauth2_query.where(OAuth2Provider.workspace_id == wid)
    for p in (await db.execute(oauth2_query)).scalars().all():
        result_providers.append(AuthProviderInfo(id=p.id, name=p.name, type="oauth2"))

    # LDAP providers
    ldap_query = select(LDAPProvider).where(LDAPProvider.is_active.is_(True))
    if tid:
        ldap_query = ldap_query.where(LDAPProvider.tenant_id == tid)
    elif wid:
        ldap_query = ldap_query.where(LDAPProvider.workspace_id == wid)
    for p in (await db.execute(ldap_query)).scalars().all():
        result_providers.append(AuthProviderInfo(id=p.id, name=p.name, type="ldap"))

    return AuthProvidersResponse(providers=result_providers)


@router.get("/auth/oidc/{provider_id}/authorize", response_model=OIDCAuthorizeResponse)
async def oidc_authorize(
    provider_id: uuid.UUID,
    redirect_uri: str,
    db: DbDep,
) -> OIDCAuthorizeResponse:
    """Start OIDC authorization code flow — returns the IdP authorization URL."""
    provider = await db.get(OIDCProvider, provider_id)
    if provider is None or not provider.is_active or not provider.client_id:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "OIDC provider not found or not configured for login"
        )

    state = generate_oidc_state(provider_id)
    auth_url = await build_oidc_authorize_url(provider, redirect_uri, state)
    return OIDCAuthorizeResponse(authorization_url=auth_url, state=state)


@router.post("/auth/oidc/callback", response_model=LoginResponse)
async def oidc_callback(body: OIDCCallbackRequest, db: DbDep) -> LoginResponse:
    """
    Complete the OIDC authorization code flow.
    Exchanges the code for tokens, validates the id_token,
    finds or creates the user, and returns a session API key.
    """
    provider_id = validate_oidc_state(body.state)
    if provider_id != body.provider_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "State/provider mismatch")

    provider = await db.get(OIDCProvider, provider_id)
    if provider is None or not provider.is_active or not provider.client_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "OIDC provider not found")

    from runledger_api.core.config import settings as app_settings  # noqa: PLC0415

    callback_redirect_uri = f"{app_settings.app_base_url}/auth/oidc/callback"

    token_response = await exchange_oidc_code(provider, body.code, callback_redirect_uri)
    id_token = token_response.get("id_token")
    if not id_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "OIDC token response missing id_token")

    claims = await validate_oidc_id_token(provider, id_token)
    user, _ext_id = await find_or_create_user_from_oidc(db, provider, claims)

    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is deactivated")

    user.last_login_at = datetime.now(UTC)

    wu_result = await db.execute(
        select(WorkspaceUser)
        .where(WorkspaceUser.user_id == user.id)
        .order_by(WorkspaceUser.created_at)
    )
    workspace_users = list(wu_result.scalars().all())
    if not workspace_users:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User has no workspace access")

    workspace_user = workspace_users[0]
    for wu in workspace_users:
        if wu.workspace_id == provider.workspace_id:
            workspace_user = wu
            break

    workspace = await db.get(Workspace, workspace_user.workspace_id)
    if workspace is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Workspace not found")
    tenant = await db.get(Tenant, workspace.tenant_id)
    if tenant is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Organization not found")

    tu_result = await db.execute(
        select(TenantUser).where(
            TenantUser.user_id == user.id,
            TenantUser.tenant_id == workspace.tenant_id,
        )
    )
    tenant_user = tu_result.scalar_one_or_none()
    tenant_role = tenant_user.role.value if tenant_user else None
    workspace_role = workspace_user.role.value

    workspace_ids = [str(wu.workspace_id) for wu in workspace_users]

    raw_key, key_hash, key_prefix = generate_api_key(EnvironmentEnum.dev)
    session_key = ApiKey(
        workspace_id=workspace.id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name="dashboard-session-oidc",
        scopes=[],
        expires_at=datetime.now(UTC) + _SESSION_EXPIRY,
        is_session=True,
        created_by=user.email,
    )
    db.add(session_key)
    await db.commit()

    log.info(
        "oidc_login",
        user_id=str(user.id),
        workspace_id=str(workspace.id),
        provider_id=str(provider.id),
        provider_name=provider.name,
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


async def _build_session_response(
    db: AsyncSession, user: User, preferred_workspace_id: uuid.UUID | None, session_name: str
) -> LoginResponse:
    """Shared helper: loads memberships, picks workspace, creates session key, returns LoginResponse."""
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is deactivated")

    user.last_login_at = datetime.now(UTC)

    wu_result = await db.execute(
        select(WorkspaceUser)
        .where(WorkspaceUser.user_id == user.id)
        .order_by(WorkspaceUser.created_at)
    )
    workspace_users = list(wu_result.scalars().all())
    if not workspace_users:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User has no workspace access")

    workspace_user = workspace_users[0]
    if preferred_workspace_id:
        for wu in workspace_users:
            if wu.workspace_id == preferred_workspace_id:
                workspace_user = wu
                break

    workspace = await db.get(Workspace, workspace_user.workspace_id)
    if workspace is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Workspace not found")
    tenant = await db.get(Tenant, workspace.tenant_id)
    if tenant is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Organization not found")

    tu_result = await db.execute(
        select(TenantUser).where(
            TenantUser.user_id == user.id, TenantUser.tenant_id == workspace.tenant_id
        )
    )
    tenant_user = tu_result.scalar_one_or_none()

    raw_key, key_hash, key_prefix = generate_api_key(EnvironmentEnum.dev)
    session_key = ApiKey(
        workspace_id=workspace.id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=session_name,
        scopes=[],
        expires_at=datetime.now(UTC) + _SESSION_EXPIRY,
        is_session=True,
        created_by=user.email,
    )
    db.add(session_key)
    await db.commit()

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
        tenant_role=tenant_user.role.value if tenant_user else None,
        workspace_role=workspace_user.role.value,
        workspace_ids=[str(wu.workspace_id) for wu in workspace_users],
    )


# ── OAuth2 ───────────────────────────────────────────────────────────────────


@router.get("/auth/oauth2/{provider_id}/authorize", response_model=OAuth2AuthorizeResponse)
async def oauth2_authorize(
    provider_id: uuid.UUID,
    redirect_uri: str,
    db: DbDep,
) -> OAuth2AuthorizeResponse:
    """Start OAuth2 authorization code flow."""
    provider = await db.get(OAuth2Provider, provider_id)
    if provider is None or not provider.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "OAuth2 provider not found")

    state_value = generate_oauth2_state(provider_id)
    auth_url = build_oauth2_authorize_url(provider, redirect_uri, state_value)
    return OAuth2AuthorizeResponse(authorization_url=auth_url, state=state_value)


@router.post("/auth/oauth2/callback", response_model=LoginResponse)
async def oauth2_callback(body: OAuth2CallbackRequest, db: DbDep) -> LoginResponse:
    """Complete OAuth2 authorization code flow."""
    provider_id = validate_oauth2_state(body.state)
    if provider_id != body.provider_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "State/provider mismatch")

    provider = await db.get(OAuth2Provider, provider_id)
    if provider is None or not provider.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "OAuth2 provider not found")

    from runledger_api.core.config import settings as app_settings  # noqa: PLC0415

    callback_redirect_uri = f"{app_settings.app_base_url}/auth/oauth2/callback"

    token_response = await exchange_oauth2_code(provider, body.code, callback_redirect_uri)
    access_token = token_response.get("access_token")
    if not access_token:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "OAuth2 token response missing access_token"
        )

    userinfo = await fetch_oauth2_userinfo(provider, access_token)
    user, _ext_id = await find_or_create_user_from_oauth2(db, provider, userinfo)

    log.info(
        "oauth2_login",
        user_id=str(user.id),
        provider_id=str(provider.id),
        provider_name=provider.name,
    )

    return await _build_session_response(
        db, user, provider.workspace_id, "dashboard-session-oauth2"
    )


# ── LDAP ─────────────────────────────────────────────────────────────────────


@router.post("/auth/ldap/login", response_model=LoginResponse)
async def ldap_login(body: LDAPLoginRequest, db: DbDep) -> LoginResponse:
    """Authenticate with LDAP username + password."""
    provider = await db.get(LDAPProvider, body.provider_id)
    if provider is None or not provider.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "LDAP provider not found")

    ldap_user = await authenticate_ldap(provider, body.username, body.password)
    user, _ext_id = await find_or_create_user_from_ldap(db, provider, ldap_user)

    log.info(
        "ldap_login",
        user_id=str(user.id),
        provider_id=str(provider.id),
        provider_name=provider.name,
        ldap_uid=ldap_user.get("uid"),
    )

    return await _build_session_response(db, user, provider.workspace_id, "dashboard-session-ldap")


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
