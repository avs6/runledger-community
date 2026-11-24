"""
Dashboard authentication endpoints (NextAuth).

POST /auth/login                    email + password (rate limited)
POST /auth/switch-workspace         re-issue a session for another accessible workspace
POST /auth/logout                   revoke the current session key
GET  /auth/me                       current session, derived server-side
GET  /auth/sessions                 the caller's live dashboard sessions
DELETE /auth/sessions/{key_id}      revoke one of the caller's sessions
POST /auth/verify-email             confirm an email address with an emailed token
POST /auth/resend-verification      re-send the verification email (always 202)
POST /auth/password-reset/request   email a reset link (always 202)
POST /auth/password-reset/confirm   set a new password with a reset token
GET  /auth/providers                public list of external login providers
GET  /auth/oidc/{id}/authorize      start OIDC (state + nonce + PKCE kept in Redis)
POST /auth/oidc/callback            finish OIDC
GET  /auth/oauth2/{id}/authorize    start OAuth2 (state + PKCE kept in Redis)
POST /auth/oauth2/callback          finish OAuth2
POST /auth/ldap/login               LDAP username + password (rate limited)

Every successful login returns a short-lived workspace-scoped session key. The key
is tied to its user (``api_keys.user_id``) and re-validated on each request.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.config import DEV_SEED_ADMIN_EMAIL, settings
from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_api_key, require_user
from runledger_api.core.redis import get_redis
from runledger_api.models.security import LDAPProvider, OAuth2Provider, OIDCProvider
from runledger_api.models.tenant import ApiKey, Tenant, TenantUser, User, Workspace, WorkspaceUser
from runledger_api.schemas.auth import (
    EmailOnlyRequest,
    PasswordResetConfirm,
    SessionInfoResponse,
    SessionKeyResponse,
    VerifyEmailRequest,
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
from runledger_api.services.login_guard import (
    assert_login_allowed,
    clear_login_failures,
    record_login_failure,
)
from runledger_api.services.passwords import (
    hash_password_async,
    hash_token,
    new_token,
    validate_password_policy,
    verify_password,
)
from runledger_api.services.security import (
    authenticate_ldap,
    build_oauth2_authorize_url,
    build_oidc_authorize_url,
    consume_auth_state,
    create_auth_state,
    exchange_oauth2_code,
    exchange_oidc_code,
    fetch_oauth2_userinfo,
    find_or_create_user_from_ldap,
    find_or_create_user_from_oauth2,
    find_or_create_user_from_oidc,
    get_client_ip,
    sso_callback_url,
    validate_oidc_id_token,
)
from runledger_api.services.sessions import (
    accessible_workspaces,
    create_session_key,
    has_workspace_access,
    revoke_user_sessions,
    tenant_is_active,
)

log = structlog.get_logger()

router = APIRouter(tags=["auth"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
RedisDep = Annotated[Any, Depends(get_redis)]


def _client_ip(request: Request) -> str | None:
    return get_client_ip(
        request.headers.get("x-forwarded-for"),
        request.client.host if request.client else None,
    )


async def _session_payload(db: AsyncSession, user: User, workspace: Workspace) -> dict[str, Any]:
    """Session fields shared by LoginResponse and SessionInfoResponse."""
    tenant = await db.get(Tenant, workspace.tenant_id)
    tenant_user = (
        await db.execute(
            select(TenantUser).where(
                TenantUser.user_id == user.id, TenantUser.tenant_id == workspace.tenant_id
            )
        )
    ).scalar_one_or_none()
    workspace_user = (
        await db.execute(
            select(WorkspaceUser).where(
                WorkspaceUser.user_id == user.id, WorkspaceUser.workspace_id == workspace.id
            )
        )
    ).scalar_one_or_none()
    accessible = await accessible_workspaces(db, user)
    workspace_ids = [str(ws.id) for ws in accessible]
    if str(workspace.id) not in workspace_ids:
        workspace_ids.insert(0, str(workspace.id))
    active_tu = tenant_user if tenant_user is not None and tenant_user.status == "active" else None
    active_wu = (
        workspace_user if workspace_user is not None and workspace_user.status == "active" else None
    )
    return {
        "email": user.email,
        "full_name": user.full_name,
        "user_id": str(user.id),
        "workspace_id": str(workspace.id),
        "workspace_name": workspace.name,
        "tenant_id": str(workspace.tenant_id),
        "tenant_name": tenant.name if tenant else "",
        "is_platform_admin": user.is_platform_admin,
        "tenant_role": str(active_tu.role) if active_tu else None,
        "workspace_role": str(active_wu.role) if active_wu else None,
        "workspace_ids": workspace_ids,
        "must_change_password": bool(getattr(user, "must_change_password", False)),
    }


async def _issue_session(
    db: AsyncSession,
    user: User,
    preferred_workspace_id: uuid.UUID | None,
    session_name: str,
) -> LoginResponse:
    """Pick an accessible workspace, mint a session key and build the response."""
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is deactivated")

    candidates = [
        ws for ws in await accessible_workspaces(db, user) if await tenant_is_active(db, ws)
    ]
    if not candidates:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User has no workspace access")
    workspace = candidates[0]
    if preferred_workspace_id is not None:
        workspace = next((ws for ws in candidates if ws.id == preferred_workspace_id), workspace)

    user.last_login_at = datetime.now(UTC)
    raw_key, _key = await create_session_key(db, user=user, workspace=workspace, name=session_name)
    payload = await _session_payload(db, user, workspace)
    await db.commit()
    return LoginResponse(api_key=raw_key, **payload)


def _parse_uuid(value: str | None) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


# ── Password login ────────────────────────────────────────────────────────────


@router.post("/auth/login", response_model=LoginResponse)
async def login(body: LoginRequest, request: Request, db: DbDep, redis: RedisDep) -> LoginResponse:
    """Authenticate with email + password; returns a workspace session key."""
    email = body.email.strip()
    ip = _client_ip(request)
    await assert_login_allowed(redis, email, ip)

    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    # Always runs bcrypt (dummy hash for unknown users) so timing does not reveal
    # whether the email is registered.
    password_ok = await verify_password(body.password, user.password_hash if user else None)
    if user is None or not password_ok:
        await record_login_failure(redis, email, ip)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    await clear_login_failures(redis, email)
    # The demo admin seeded for local development must never work in production, even
    # if a database seeded in dev is promoted (review P-01).
    if not settings.is_development and user.email.lower() == DEV_SEED_ADMIN_EMAIL:
        log.warning("dev_seed_admin_login_refused", user_id=str(user.id))
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "The development demo account is disabled outside development. "
            "Create a platform admin with the setup page or POST /admin/bootstrap.",
        )
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is deactivated")
    if not user.email_verified:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Please verify your email before signing in")

    response = await _issue_session(db, user, _parse_uuid(body.workspace_id), "dashboard-session")
    log.info(
        "dashboard_login",
        user_id=str(user.id),
        workspace_id=response.workspace_id,
        is_platform_admin=user.is_platform_admin,
    )
    return response


# ── First-run bootstrap status ───────────────────────────────────────────────


class BootstrapStatusResponse(BaseModel):
    needs_bootstrap: bool
    environment: str


@router.get("/auth/bootstrap-status", response_model=BootstrapStatusResponse)
async def bootstrap_status(db: DbDep) -> BootstrapStatusResponse:
    """Public: whether this deployment still needs its first platform admin. The login
    page uses it to point operators at /setup instead of a seeded default account."""
    admins = (
        await db.execute(
            select(func.count()).select_from(User).where(User.is_platform_admin.is_(True))
        )
    ).scalar_one()
    return BootstrapStatusResponse(
        needs_bootstrap=not bool(admins), environment=settings.environment
    )


# ── Session management ────────────────────────────────────────────────────────


class SwitchWorkspaceRequest(BaseModel):
    workspace_id: str


@router.post("/auth/switch-workspace", response_model=LoginResponse)
async def switch_workspace(
    body: SwitchWorkspaceRequest,
    auth: Annotated[tuple[Any, ...], Depends(require_user)],
    current_key: Annotated[ApiKey, Depends(get_current_api_key)],
    db: DbDep,
) -> LoginResponse:
    """Issue a session for another workspace the user can access and revoke the old one.

    Access: active workspace membership, or an active org-level role (org admin,
    manager, billing admin, auditor) in the target org, or platform admin.
    """
    _, user = auth
    target_ws_id = _parse_uuid(body.workspace_id)
    if target_ws_id is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid workspace_id")
    target = await db.get(Workspace, target_ws_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")
    if not await has_workspace_access(db, user, target):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No access to this workspace")
    if target.status != "active" or not await tenant_is_active(db, target):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This workspace is not active")

    raw_key, _key = await create_session_key(db, user=user, workspace=target)
    current_key.revoked_at = datetime.now(UTC)
    payload = await _session_payload(db, user, target)
    await db.commit()
    log.info("workspace_switch", user_id=str(user.id), workspace_id=str(target.id))
    return LoginResponse(api_key=raw_key, **payload)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    current_key: Annotated[ApiKey, Depends(get_current_api_key)], db: DbDep
) -> Response:
    """Revoke the session key used for this request (no-op for non-session keys)."""
    if current_key.is_session and current_key.revoked_at is None:
        current_key.revoked_at = datetime.now(UTC)
        await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/auth/me", response_model=SessionInfoResponse)
async def get_session_info(
    auth: Annotated[tuple[Any, ...], Depends(require_user)], db: DbDep
) -> SessionInfoResponse:
    """The current session as the server sees it (roles re-read from memberships)."""
    workspace, user = auth
    return SessionInfoResponse(**await _session_payload(db, user, workspace))


@router.get("/auth/sessions", response_model=list[SessionKeyResponse])
async def list_my_sessions(
    auth: Annotated[tuple[Any, ...], Depends(require_user)],
    current_key: Annotated[ApiKey, Depends(get_current_api_key)],
    db: DbDep,
) -> list[SessionKeyResponse]:
    _, user = auth
    now = datetime.now(UTC)
    rows = (
        await db.execute(
            select(ApiKey, Workspace.name)
            .join(Workspace, Workspace.id == ApiKey.workspace_id)
            .where(
                ApiKey.is_session.is_(True),
                ApiKey.user_id == user.id,
                ApiKey.revoked_at.is_(None),
                (ApiKey.expires_at.is_(None)) | (ApiKey.expires_at > now),
            )
            .order_by(ApiKey.created_at.desc())
            .limit(100)
        )
    ).all()
    return [
        SessionKeyResponse(
            id=k.id,
            workspace_id=k.workspace_id,
            workspace_name=ws_name,
            key_prefix=k.key_prefix,
            name=k.name,
            created_at=k.created_at,
            expires_at=k.expires_at,
            last_used_at=k.last_used_at,
            current=k.id == current_key.id,
        )
        for k, ws_name in rows
    ]


@router.delete("/auth/sessions/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_my_session(
    key_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_user)],
    db: DbDep,
) -> Response:
    _, user = auth
    key = await db.get(ApiKey, key_id)
    if key is None or not key.is_session or key.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    if key.revoked_at is None:
        key.revoked_at = datetime.now(UTC)
        await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Email verification & password reset ──────────────────────────────────────


async def issue_verification_email(db: AsyncSession, user: User) -> None:
    """Create a fresh verification token and email it (caller commits)."""
    from runledger_api.services.email import send_verification_email  # noqa: PLC0415

    raw, digest = new_token()
    user.email_verify_token = digest
    user.email_verify_expires_at = datetime.now(UTC) + timedelta(
        hours=settings.email_verify_ttl_hours
    )
    url = f"{settings.app_base_url.rstrip('/')}/verify-email?token={raw}"
    await send_verification_email(user.email, user.full_name or "", url)


@router.post("/auth/verify-email")
async def verify_email(body: VerifyEmailRequest, db: DbDep) -> dict[str, Any]:
    user = (
        await db.execute(select(User).where(User.email_verify_token == hash_token(body.token)))
    ).scalar_one_or_none()
    now = datetime.now(UTC)
    if user is None or user.email_verify_expires_at is None or user.email_verify_expires_at < now:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired verification link")
    user.email_verified = True
    user.email_verify_token = None
    user.email_verify_expires_at = None
    await db.commit()
    return {"ok": True, "message": "Email verified. You can now sign in."}


@router.post("/auth/resend-verification", status_code=status.HTTP_202_ACCEPTED)
async def resend_verification(
    body: EmailOnlyRequest, request: Request, db: DbDep, redis: RedisDep
) -> dict[str, Any]:
    """Always 202 so the response does not reveal which emails exist."""
    account = f"verify:{body.email.strip().lower()}"
    await assert_login_allowed(redis, account, _client_ip(request))
    user = (
        await db.execute(select(User).where(User.email == body.email.strip()))
    ).scalar_one_or_none()
    if user is not None and user.is_active and not user.email_verified:
        await issue_verification_email(db, user)
        await db.commit()
    await record_login_failure(redis, account, _client_ip(request))
    return {"ok": True, "message": "If the account exists, a verification email was sent."}


@router.post("/auth/password-reset/request", status_code=status.HTTP_202_ACCEPTED)
async def request_password_reset(
    body: EmailOnlyRequest, request: Request, db: DbDep, redis: RedisDep
) -> dict[str, Any]:
    """Email a single-use reset link. Always 202 (no account enumeration)."""
    from runledger_api.services.email import send_password_reset_email  # noqa: PLC0415

    ip = _client_ip(request)
    # Separate counter from sign-in failures so reset spam cannot lock a user out.
    account = f"reset:{body.email.strip().lower()}"
    await assert_login_allowed(redis, account, ip)
    user = (
        await db.execute(select(User).where(User.email == body.email.strip()))
    ).scalar_one_or_none()
    if user is not None and user.is_active and user.password_hash is not None:
        raw, digest = new_token()
        user.password_reset_token_hash = digest
        user.password_reset_expires_at = datetime.now(UTC) + timedelta(
            minutes=settings.password_reset_ttl_minutes
        )
        await db.commit()
        url = f"{settings.app_base_url.rstrip('/')}/reset-password?token={raw}"
        await send_password_reset_email(user.email, user.full_name, url)
    await record_login_failure(redis, account, ip)
    return {"ok": True, "message": "If the account exists, a reset link was sent."}


@router.post("/auth/password-reset/confirm")
async def confirm_password_reset(body: PasswordResetConfirm, db: DbDep) -> dict[str, Any]:
    user = (
        await db.execute(
            select(User).where(User.password_reset_token_hash == hash_token(body.token))
        )
    ).scalar_one_or_none()
    now = datetime.now(UTC)
    if (
        user is None
        or user.password_reset_expires_at is None
        or user.password_reset_expires_at < now
        or not user.is_active
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired reset link")
    validate_password_policy(body.new_password)
    user.password_hash = await hash_password_async(body.new_password)
    user.password_reset_token_hash = None
    user.password_reset_expires_at = None
    user.must_change_password = False
    # Possession of the reset link proves control of the mailbox.
    user.email_verified = True
    await revoke_user_sessions(db, user.id)
    await db.commit()
    log.info("password_reset_completed", user_id=str(user.id))
    return {"ok": True, "message": "Password updated. Sign in with your new password."}


# ── External login providers ─────────────────────────────────────────────────


@router.get("/auth/providers", response_model=AuthProvidersResponse)
async def list_auth_providers(
    db: DbDep,
    tenant_id: str | None = None,
    workspace_id: str | None = None,
) -> AuthProvidersResponse:
    """Public endpoint: lists available external login providers."""
    tid = _parse_uuid(tenant_id)
    wid = _parse_uuid(workspace_id)

    result_providers: list[AuthProviderInfo] = []

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

    oauth2_query = select(OAuth2Provider).where(OAuth2Provider.is_active.is_(True))
    if tid:
        oauth2_query = oauth2_query.where(OAuth2Provider.tenant_id == tid)
    elif wid:
        oauth2_query = oauth2_query.where(OAuth2Provider.workspace_id == wid)
    for p in (await db.execute(oauth2_query)).scalars().all():
        result_providers.append(AuthProviderInfo(id=p.id, name=p.name, type="oauth2"))

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
    db: DbDep,
    redis: RedisDep,
    redirect_uri: str | None = None,  # accepted for compatibility; ignored (pinned)
) -> OIDCAuthorizeResponse:
    """Start the OIDC authorization code flow (PKCE + nonce)."""
    provider = await db.get(OIDCProvider, provider_id)
    if provider is None or not provider.is_active or not provider.client_id:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "OIDC provider not found or not configured for login"
        )
    flow = await create_auth_state(redis, "oidc", provider_id)
    auth_url = await build_oidc_authorize_url(provider, sso_callback_url("oidc"), flow)
    return OIDCAuthorizeResponse(authorization_url=auth_url, state=flow.state)


@router.post("/auth/oidc/callback", response_model=LoginResponse)
async def oidc_callback(body: OIDCCallbackRequest, db: DbDep, redis: RedisDep) -> LoginResponse:
    """Finish OIDC: exchange code (with PKCE verifier), validate id_token + nonce."""
    flow = await consume_auth_state(redis, "oidc", body.state)
    if flow.provider_id != body.provider_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "State/provider mismatch")
    provider = await db.get(OIDCProvider, flow.provider_id)
    if provider is None or not provider.is_active or not provider.client_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "OIDC provider not found")

    token_response = await exchange_oidc_code(
        provider, body.code, sso_callback_url("oidc"), flow.code_verifier
    )
    id_token = token_response.get("id_token")
    if not id_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "OIDC token response missing id_token")
    claims = await validate_oidc_id_token(provider, id_token, flow.nonce)
    user, _ext_id = await find_or_create_user_from_oidc(db, provider, claims)
    log.info("oidc_login", user_id=str(user.id), provider_id=str(provider.id))
    return await _issue_session(db, user, provider.workspace_id, "dashboard-session-oidc")


@router.get("/auth/oauth2/{provider_id}/authorize", response_model=OAuth2AuthorizeResponse)
async def oauth2_authorize(
    provider_id: uuid.UUID,
    db: DbDep,
    redis: RedisDep,
    redirect_uri: str | None = None,  # accepted for compatibility; ignored (pinned)
) -> OAuth2AuthorizeResponse:
    """Start the OAuth2 authorization code flow (PKCE)."""
    provider = await db.get(OAuth2Provider, provider_id)
    if provider is None or not provider.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "OAuth2 provider not found")
    flow = await create_auth_state(redis, "oauth2", provider_id)
    auth_url = build_oauth2_authorize_url(provider, sso_callback_url("oauth2"), flow)
    return OAuth2AuthorizeResponse(authorization_url=auth_url, state=flow.state)


@router.post("/auth/oauth2/callback", response_model=LoginResponse)
async def oauth2_callback(body: OAuth2CallbackRequest, db: DbDep, redis: RedisDep) -> LoginResponse:
    """Finish OAuth2: exchange code (with PKCE verifier) and resolve the user."""
    flow = await consume_auth_state(redis, "oauth2", body.state)
    if flow.provider_id != body.provider_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "State/provider mismatch")
    provider = await db.get(OAuth2Provider, flow.provider_id)
    if provider is None or not provider.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "OAuth2 provider not found")

    token_response = await exchange_oauth2_code(
        provider, body.code, sso_callback_url("oauth2"), flow.code_verifier
    )
    access_token = token_response.get("access_token")
    if not access_token:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "OAuth2 token response missing access_token"
        )
    userinfo = await fetch_oauth2_userinfo(provider, access_token)
    user, _ext_id = await find_or_create_user_from_oauth2(db, provider, userinfo)
    log.info("oauth2_login", user_id=str(user.id), provider_id=str(provider.id))
    return await _issue_session(db, user, provider.workspace_id, "dashboard-session-oauth2")


@router.post("/auth/ldap/login", response_model=LoginResponse)
async def ldap_login(
    body: LDAPLoginRequest, request: Request, db: DbDep, redis: RedisDep
) -> LoginResponse:
    """Authenticate with LDAP username + password (rate limited)."""
    provider = await db.get(LDAPProvider, body.provider_id)
    if provider is None or not provider.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "LDAP provider not found")
    account = f"ldap:{provider.id}:{body.username}"
    ip = _client_ip(request)
    await assert_login_allowed(redis, account, ip)
    try:
        ldap_user = await authenticate_ldap(provider, body.username, body.password)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            await record_login_failure(redis, account, ip)
        raise
    await clear_login_failures(redis, account)
    user, _ext_id = await find_or_create_user_from_ldap(db, provider, ldap_user)
    log.info("ldap_login", user_id=str(user.id), provider_id=str(provider.id))
    return await _issue_session(db, user, provider.workspace_id, "dashboard-session-ldap")


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
