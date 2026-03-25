"""
SSO / OIDC + SCIM token management router.

Public OIDC flow:
  GET  /auth/sso/authorize/{config_id}   — initiate OIDC authorization
  GET  /auth/sso/callback/{config_id}    — receive code from IdP, JIT provision, redirect
  POST /auth/sso/exchange                — frontend exchanges short-lived Redis token

Org-admin CRUD:
  GET/POST   /sso/configs                — list / create SSO configs
  GET/PUT/DELETE /sso/configs/{id}       — get / update / delete config
  GET/POST   /sso/tokens                 — list / create SCIM tokens
  DELETE     /sso/tokens/{id}            — revoke SCIM token
"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.config import settings
from runledger_api.core.db import get_db
from runledger_api.core.deps import require_org_admin
from runledger_api.core.feature_gate import require_feature
from runledger_api.models.sso import ScimToken, SsoConfig, SsoIdentity
from runledger_api.models.tenant import (
    ApiKey,
    EnvironmentEnum,
    Tenant,
    TenantRoleEnum,
    TenantUser,
    User,
    Workspace,
    WorkspaceRoleEnum,
    WorkspaceUser,
)
from runledger_api.schemas.runs import LoginResponse
from runledger_api.schemas.sso import (
    ScimTokenCreate,
    ScimTokenCreated,
    ScimTokenList,
    ScimTokenResponse,
    SsoAuthorizeResponse,
    SsoConfigCreate,
    SsoConfigList,
    SsoConfigResponse,
    SsoConfigUpdate,
    SsoExchangeRequest,
)
from runledger_api.services.auth import generate_api_key
from runledger_api.services.oidc import (
    build_authorization_url,
    decrypt_secret,
    discover_oidc,
    encrypt_secret,
    exchange_code,
    fetch_userinfo,
    generate_scim_token,
    make_state,
    now_utc,
    sso_redirect_uri,
    verify_state,
)

log = structlog.get_logger()
router = APIRouter(tags=["sso"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
OrgAdminDep = Annotated[tuple[Any, ...], Depends(require_org_admin)]

_SESSION_EXPIRY = timedelta(days=30)
_SSO_TOKEN_TTL = 300  # 5 minutes in Redis


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _get_redis() -> Any:
    from runledger_api.core.redis import redis_client  # noqa: PLC0415

    return redis_client


async def _store_sso_token(login_resp: LoginResponse) -> str:
    """Store LoginResponse in Redis for 5 minutes; return the exchange token."""
    import json  # noqa: PLC0415

    redis = await _get_redis()
    token = "sso_" + secrets.token_urlsafe(24)
    key = f"rl:sso_exchange:{token}"
    await redis.setex(key, _SSO_TOKEN_TTL, json.dumps(login_resp.model_dump()))
    return token


async def _pop_sso_token(token: str) -> LoginResponse | None:
    """Retrieve + delete the exchange token from Redis."""
    import json  # noqa: PLC0415

    redis = await _get_redis()
    key = f"rl:sso_exchange:{token}"
    raw = await redis.get(key)
    if raw is None:
        return None
    await redis.delete(key)
    return LoginResponse(**json.loads(raw))


async def _build_login_response(
    db: AsyncSession, user: User, workspace: Workspace
) -> LoginResponse:
    """Issue a session API key and build a LoginResponse."""
    tu_result = await db.execute(
        select(TenantUser).where(
            TenantUser.user_id == user.id,
            TenantUser.tenant_id == workspace.tenant_id,
        )
    )
    tenant_user = tu_result.scalar_one_or_none()
    tenant_role = tenant_user.role.value if tenant_user else None

    wu_result = await db.execute(
        select(WorkspaceUser)
        .where(WorkspaceUser.user_id == user.id)
        .order_by(WorkspaceUser.created_at)
    )
    workspace_users = list(wu_result.scalars().all())
    workspace_ids = [str(wu.workspace_id) for wu in workspace_users]

    # Find workspace_role
    workspace_role: str | None = None
    for wu in workspace_users:
        if wu.workspace_id == workspace.id:
            workspace_role = wu.role.value
            break

    raw_key, key_hash, key_prefix = generate_api_key(EnvironmentEnum.dev)
    db.add(
        ApiKey(
            workspace_id=workspace.id,
            key_hash=key_hash,
            key_prefix=key_prefix,
            name="sso-session",
            scopes=[],
            expires_at=datetime.now(UTC) + _SESSION_EXPIRY,
            is_session=True,
            created_by=user.email,
        )
    )
    await db.commit()

    return LoginResponse(
        email=user.email,
        full_name=user.full_name,
        user_id=str(user.id),
        workspace_id=str(workspace.id),
        workspace_name=workspace.name,
        tenant_id=str(workspace.tenant_id),
        api_key=raw_key,
        is_platform_admin=user.is_platform_admin,
        tenant_role=tenant_role,
        workspace_role=workspace_role,
        workspace_ids=workspace_ids,
    )


async def _jit_provision(
    db: AsyncSession,
    *,
    sso_config: SsoConfig,
    sub: str,
    email: str,
    full_name: str,
) -> tuple[User, Workspace]:
    """
    JIT-provision a new user or link an existing one.
    Returns (user, primary_workspace).
    """
    # 1. Look up by existing SSO identity
    ident_result = await db.execute(
        select(SsoIdentity).where(
            SsoIdentity.sso_config_id == sso_config.id,
            SsoIdentity.external_sub == sub,
        )
    )
    identity = ident_result.scalar_one_or_none()

    if identity is not None:
        user_result = await db.execute(select(User).where(User.id == identity.user_id))
        user = user_result.scalar_one_or_none()
        if user is None:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Linked user not found")
        identity.last_login_at = now_utc()
        user.last_login_at = now_utc()
    else:
        # 2. Look up by email (link existing account)
        user_result = await db.execute(select(User).where(User.email == email))
        user = user_result.scalar_one_or_none()

        if user is None:
            # 3. Create new user
            user = User(
                email=email,
                password_hash=None,
                full_name=full_name,
                is_active=True,
                is_platform_admin=False,
                email_verified=True,
            )
            db.add(user)
            await db.flush()

            # Fetch tenant and create memberships
            tenant_result = await db.execute(
                select(Tenant).where(Tenant.id == sso_config.tenant_id)
            )
            tenant = tenant_result.scalar_one_or_none()
            if tenant is None:
                raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Tenant not found")

            # Map default_role to TenantRoleEnum / WorkspaceRoleEnum
            t_role = TenantRoleEnum.org_member
            w_role = WorkspaceRoleEnum.member
            if sso_config.default_role == "admin":
                t_role = TenantRoleEnum.org_admin
                w_role = WorkspaceRoleEnum.workspace_admin
            elif sso_config.default_role == "editor":
                w_role = WorkspaceRoleEnum.workspace_editor

            db.add(TenantUser(tenant_id=tenant.id, user_id=user.id, role=t_role))

            # Find the tenant's first workspace
            ws_result = await db.execute(
                select(Workspace)
                .where(Workspace.tenant_id == tenant.id)
                .order_by(Workspace.created_at)
                .limit(1)
            )
            workspace = ws_result.scalar_one_or_none()
            if workspace is None:
                raise HTTPException(
                    status.HTTP_500_INTERNAL_SERVER_ERROR, "No workspace found for tenant"
                )

            db.add(WorkspaceUser(workspace_id=workspace.id, user_id=user.id, role=w_role))
            await db.flush()

        # Create SSO identity link
        db.add(
            SsoIdentity(
                user_id=user.id,
                sso_config_id=sso_config.id,
                external_sub=sub,
                external_email=email,
                last_login_at=now_utc(),
            )
        )
        user.last_login_at = now_utc()

    # Load primary workspace for response
    wu_result = await db.execute(
        select(WorkspaceUser)
        .where(WorkspaceUser.user_id == user.id)
        .order_by(WorkspaceUser.created_at)
        .limit(1)
    )
    wu = wu_result.scalar_one_or_none()
    if wu is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User has no workspace access")

    workspace_result = await db.execute(select(Workspace).where(Workspace.id == wu.workspace_id))
    workspace = workspace_result.scalar_one_or_none()
    if workspace is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Workspace not found")

    return user, workspace


# ── OIDC flow ─────────────────────────────────────────────────────────────────


@router.get(
    "/auth/sso/authorize/{config_id}",
    response_model=SsoAuthorizeResponse,
    summary="Initiate OIDC authorization",
)
async def sso_authorize(config_id: uuid.UUID, db: DbDep) -> SsoAuthorizeResponse:
    """Return the IdP authorization URL. The frontend redirects the user there."""
    require_feature("sso", "SSO / OIDC")
    config_result = await db.execute(
        select(SsoConfig).where(SsoConfig.id == config_id, SsoConfig.enabled == True)  # noqa: E712
    )
    sso_config = config_result.scalar_one_or_none()
    if sso_config is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "SSO config not found or disabled")

    discovery = await discover_oidc(sso_config.issuer_url)
    authorization_endpoint = discovery["authorization_endpoint"]

    nonce = secrets.token_urlsafe(16)
    state = make_state(config_id, nonce)
    redirect_uri = sso_redirect_uri(config_id)

    url = build_authorization_url(
        authorization_endpoint=authorization_endpoint,
        client_id=sso_config.client_id,
        redirect_uri=redirect_uri,
        scopes=sso_config.scopes,
        state=state,
        nonce=nonce,
    )
    return SsoAuthorizeResponse(authorization_url=url)


@router.get("/auth/sso/callback/{config_id}", summary="OIDC callback — internal")
async def sso_callback(
    config_id: uuid.UUID,
    db: DbDep,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
) -> RedirectResponse:
    """
    Receive the authorization code from the IdP.
    Exchange it, JIT-provision the user, store LoginResponse in Redis,
    redirect the browser to {frontend}/sso?token=<exchange_token>.
    """
    frontend_url = settings.app_base_url.rstrip("/")

    if error:
        log.warning("sso_callback_error", error=error)
        return RedirectResponse(f"{frontend_url}/sso?error={error}")

    if not code or not state:
        return RedirectResponse(f"{frontend_url}/sso?error=missing_params")

    # Verify state
    try:
        state_data = verify_state(state)
        if state_data.get("config_id") != str(config_id):
            raise ValueError("config_id mismatch")
    except ValueError as exc:
        log.warning("sso_state_invalid", error=str(exc))
        return RedirectResponse(f"{frontend_url}/sso?error=invalid_state")

    config_result = await db.execute(
        select(SsoConfig).where(SsoConfig.id == config_id, SsoConfig.enabled == True)  # noqa: E712
    )
    sso_config = config_result.scalar_one_or_none()
    if sso_config is None:
        return RedirectResponse(f"{frontend_url}/sso?error=config_not_found")

    try:
        discovery = await discover_oidc(sso_config.issuer_url)
        token_endpoint = discovery["token_endpoint"]
        client_secret = decrypt_secret(sso_config.client_secret_enc)
        redirect_uri = sso_redirect_uri(config_id)

        tokens = await exchange_code(
            token_endpoint=token_endpoint,
            client_id=sso_config.client_id,
            client_secret=client_secret,
            code=code,
            redirect_uri=redirect_uri,
        )

        # Get user claims — prefer userinfo endpoint over id_token
        email: str = ""
        full_name: str = ""
        sub: str = ""

        if "userinfo_endpoint" in discovery and "access_token" in tokens:
            try:
                info = await fetch_userinfo(discovery["userinfo_endpoint"], tokens["access_token"])
                sub = info.get("sub", "")
                email = info.get("email", "")
                full_name = info.get("name", "") or info.get("given_name", "") or ""
            except Exception:
                pass  # fall through to id_token

        if not email and "id_token" in tokens:
            from runledger_api.services.oidc import decode_id_token_claims  # noqa: PLC0415

            claims = decode_id_token_claims(tokens["id_token"])
            sub = sub or claims.get("sub", "")
            email = email or claims.get("email", "")
            full_name = full_name or claims.get("name", "")

        if not email or not sub:
            return RedirectResponse(f"{frontend_url}/sso?error=missing_claims")

        if not full_name:
            full_name = email.split("@")[0]

        user, workspace = await _jit_provision(
            db,
            sso_config=sso_config,
            sub=sub,
            email=email,
            full_name=full_name,
        )

        login_resp = await _build_login_response(db, user, workspace)
        exchange_token = await _store_sso_token(login_resp)

        log.info("sso_login_success", email=email, config_id=str(config_id))
        return RedirectResponse(f"{frontend_url}/sso?token={exchange_token}")

    except HTTPException:
        raise
    except Exception as exc:
        log.exception("sso_callback_failed", error=str(exc))
        return RedirectResponse(f"{frontend_url}/sso?error=server_error")


@router.post("/auth/sso/exchange", response_model=LoginResponse, summary="Exchange SSO token")
async def sso_exchange(body: SsoExchangeRequest) -> LoginResponse:
    """
    Frontend exchanges the short-lived SSO token for a full LoginResponse.
    Call this from the /sso page, then pass the result to NextAuth signIn.
    """
    login_resp = await _pop_sso_token(body.token)
    if login_resp is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "SSO token invalid or expired")
    return login_resp


# ── SSO Config CRUD (org-admin) ───────────────────────────────────────────────


@router.get("/sso/configs", response_model=SsoConfigList, summary="List SSO configs")
async def list_sso_configs(auth: OrgAdminDep, db: DbDep) -> SsoConfigList:
    require_feature("sso_config", "SSO configuration")
    workspace, user, _ = auth
    result = await db.execute(
        select(SsoConfig)
        .where(SsoConfig.tenant_id == workspace.tenant_id)
        .order_by(SsoConfig.created_at)
    )
    items = list(result.scalars().all())
    return SsoConfigList(
        items=[SsoConfigResponse.model_validate(i) for i in items], total=len(items)
    )


@router.post("/sso/configs", response_model=SsoConfigResponse, status_code=201)
async def create_sso_config(
    body: SsoConfigCreate, auth: OrgAdminDep, db: DbDep
) -> SsoConfigResponse:
    workspace, user, _ = auth
    # Verify no duplicate provider for this tenant
    existing = await db.execute(
        select(SsoConfig).where(
            SsoConfig.tenant_id == workspace.tenant_id,
            SsoConfig.provider == body.provider,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"SSO config for provider '{body.provider}' already exists"
        )

    config = SsoConfig(
        tenant_id=workspace.tenant_id,
        provider=body.provider,
        issuer_url=body.issuer_url,
        client_id=body.client_id,
        client_secret_enc=encrypt_secret(body.client_secret),
        scopes=body.scopes,
        default_role=body.default_role,
        enabled=body.enabled,
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    log.info("sso_config_created", provider=body.provider, tenant_id=str(workspace.tenant_id))
    return SsoConfigResponse.model_validate(config)


@router.get("/sso/configs/{config_id}", response_model=SsoConfigResponse)
async def get_sso_config(config_id: uuid.UUID, auth: OrgAdminDep, db: DbDep) -> SsoConfigResponse:
    workspace, _, __ = auth
    result = await db.execute(
        select(SsoConfig).where(
            SsoConfig.id == config_id, SsoConfig.tenant_id == workspace.tenant_id
        )
    )
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "SSO config not found")
    return SsoConfigResponse.model_validate(config)


@router.put("/sso/configs/{config_id}", response_model=SsoConfigResponse)
async def update_sso_config(
    config_id: uuid.UUID, body: SsoConfigUpdate, auth: OrgAdminDep, db: DbDep
) -> SsoConfigResponse:
    workspace, _, __ = auth
    result = await db.execute(
        select(SsoConfig).where(
            SsoConfig.id == config_id, SsoConfig.tenant_id == workspace.tenant_id
        )
    )
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "SSO config not found")

    if body.issuer_url is not None:
        config.issuer_url = body.issuer_url
    if body.client_id is not None:
        config.client_id = body.client_id
    if body.client_secret is not None:
        config.client_secret_enc = encrypt_secret(body.client_secret)
    if body.scopes is not None:
        config.scopes = body.scopes
    if body.default_role is not None:
        config.default_role = body.default_role
    if body.enabled is not None:
        config.enabled = body.enabled
    config.updated_at = now_utc()

    await db.commit()
    await db.refresh(config)
    return SsoConfigResponse.model_validate(config)


@router.delete("/sso/configs/{config_id}", status_code=204)
async def delete_sso_config(config_id: uuid.UUID, auth: OrgAdminDep, db: DbDep) -> None:
    workspace, _, __ = auth
    result = await db.execute(
        select(SsoConfig).where(
            SsoConfig.id == config_id, SsoConfig.tenant_id == workspace.tenant_id
        )
    )
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "SSO config not found")
    await db.delete(config)
    await db.commit()


# ── SCIM Token management (org-admin) ────────────────────────────────────────


@router.get("/sso/tokens", response_model=ScimTokenList, summary="List SCIM tokens")
async def list_scim_tokens(auth: OrgAdminDep, db: DbDep) -> ScimTokenList:
    workspace, _, __ = auth
    result = await db.execute(
        select(ScimToken)
        .where(ScimToken.tenant_id == workspace.tenant_id)
        .order_by(ScimToken.created_at.desc())
    )
    items = list(result.scalars().all())
    return ScimTokenList(
        items=[ScimTokenResponse.model_validate(t) for t in items], total=len(items)
    )


@router.post("/sso/tokens", response_model=ScimTokenCreated, status_code=201)
async def create_scim_token(
    body: ScimTokenCreate, auth: OrgAdminDep, db: DbDep
) -> ScimTokenCreated:
    workspace, _, __ = auth
    raw, token_hash, prefix = generate_scim_token()
    token = ScimToken(
        tenant_id=workspace.tenant_id,
        token_hash=token_hash,
        token_prefix=prefix,
        label=body.label,
    )
    db.add(token)
    await db.commit()
    await db.refresh(token)
    resp = ScimTokenResponse.model_validate(token)
    return ScimTokenCreated(**resp.model_dump(), raw_token=raw)


@router.delete("/sso/tokens/{token_id}", status_code=204)
async def delete_scim_token(token_id: uuid.UUID, auth: OrgAdminDep, db: DbDep) -> None:
    workspace, _, __ = auth
    result = await db.execute(
        select(ScimToken).where(
            ScimToken.id == token_id, ScimToken.tenant_id == workspace.tenant_id
        )
    )
    token = result.scalar_one_or_none()
    if token is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "SCIM token not found")
    await db.delete(token)
    await db.commit()
