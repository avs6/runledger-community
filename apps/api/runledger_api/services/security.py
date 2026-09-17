from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.security import (
    ExternalIdentity,
    IpAclRule,
    LDAPProvider,
    OAuth2Provider,
    OIDCProvider,
    WorkspaceSecuritySettings,
)
from runledger_api.models.tenant import Workspace


@dataclass
class OIDCAuthResult:
    workspace: Workspace
    provider: OIDCProvider
    claims: dict[str, Any]


_OIDC_CACHE_TTL_SECONDS = 300
_oidc_doc_cache: dict[str, tuple[datetime, dict[str, Any]]] = {}
_oidc_jwks_cache: dict[str, tuple[datetime, dict[str, Any]]] = {}


async def _cached_json(
    url: str, cache: dict[str, tuple[datetime, dict[str, Any]]]
) -> dict[str, Any]:
    now = datetime.now(UTC)
    cached = cache.get(url)
    if cached and (now - cached[0]).total_seconds() < _OIDC_CACHE_TTL_SECONDS:
        return cached[1]
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        payload = resp.json()
    cache[url] = (now, payload)
    return payload


async def _resolve_oidc_urls(provider: OIDCProvider) -> tuple[str, str]:
    discovery_url = (
        provider.discovery_url
        or f"{provider.issuer_url.rstrip('/')}/.well-known/openid-configuration"
    )
    if provider.jwks_uri:
        return discovery_url, provider.jwks_uri
    discovery = await _cached_json(discovery_url, _oidc_doc_cache)
    jwks_uri = str(discovery.get("jwks_uri") or "").strip()
    if not jwks_uri:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "OIDC provider is missing jwks_uri")
    return discovery_url, jwks_uri


async def authenticate_oidc_token(token: str, db: AsyncSession) -> OIDCAuthResult | None:
    providers = (
        (await db.execute(select(OIDCProvider).where(OIDCProvider.is_active.is_(True))))
        .scalars()
        .all()
    )
    if not providers:
        return None

    last_error: Exception | None = None
    for provider in providers:
        try:
            _, jwks_uri = await _resolve_oidc_urls(provider)
            jwks = await _cached_json(jwks_uri, _oidc_jwks_cache)
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            keys = jwks.get("keys") or []
            jwk = next((item for item in keys if item.get("kid") == kid), None)
            if jwk is None and len(keys) == 1:
                jwk = keys[0]
            if jwk is None:
                continue
            public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
            claims = jwt.decode(
                token,
                key=public_key,
                algorithms=["RS256", "RS384", "RS512"],
                audience=provider.audience if provider.audience else None,
                issuer=provider.issuer_url,
                options={"verify_aud": bool(provider.audience)},
            )
            claim_mappings = provider.claim_mappings or {}
            workspace_claim = claim_mappings.get("workspace_id") or "workspace_id"
            workspace_value = claims.get(workspace_claim)
            if not workspace_value:
                continue
            workspace = await db.get(Workspace, uuid.UUID(str(workspace_value)))
            if workspace is None or workspace.id != provider.workspace_id:
                continue
            return OIDCAuthResult(workspace=workspace, provider=provider, claims=claims)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            continue
    if last_error:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Invalid OIDC bearer token"
        ) from last_error
    return None


def get_client_ip(x_forwarded_for: str | None, fallback_host: str | None) -> str | None:
    from runledger_api.core.config import settings  # noqa: PLC0415

    if x_forwarded_for:
        trusted = {p.strip() for p in settings.trusted_proxies.split(",") if p.strip()}
        parts = [p.strip() for p in x_forwarded_for.split(",")]
        if trusted:
            client_candidates = [p for p in parts if p not in trusted]
            return client_candidates[0] if client_candidates else parts[0]
        return parts[0]
    return fallback_host


async def evaluate_ip_acl(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    api_key_id: uuid.UUID | None,
    team_name: str | None,
    client_ip: str | None,
) -> None:
    rules = (
        (
            await db.execute(
                select(IpAclRule)
                .where(
                    or_(IpAclRule.workspace_id.is_(None), IpAclRule.workspace_id == workspace_id),
                    or_(IpAclRule.api_key_id.is_(None), IpAclRule.api_key_id == api_key_id),
                )
                .order_by(IpAclRule.priority.asc(), IpAclRule.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    if not rules:
        return

    if not client_ip:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Client IP required when ACL is active")

    ip_obj = ipaddress.ip_address(client_ip)
    matching_rules = []
    for rule in rules:
        if rule.team_name and rule.team_name != team_name:
            continue
        try:
            network = ipaddress.ip_network(rule.cidr, strict=False)
        except ValueError:
            continue
        if ip_obj in network:
            matching_rules.append(rule)

    allow_rules = [rule for rule in matching_rules if rule.action == "allow"]
    if allow_rules:
        return

    raise HTTPException(status.HTTP_403_FORBIDDEN, "Client IP is denied by policy")


async def get_or_create_security_settings(
    db: AsyncSession, workspace_id: uuid.UUID
) -> WorkspaceSecuritySettings:
    existing = (
        await db.execute(
            select(WorkspaceSecuritySettings).where(
                WorkspaceSecuritySettings.workspace_id == workspace_id
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    settings = WorkspaceSecuritySettings(workspace_id=workspace_id)
    db.add(settings)
    await db.commit()
    await db.refresh(settings)
    return settings


# ── OIDC Authorization Code Flow ──────────────────────────────────────────────

_STATE_TTL_SECONDS = 600
_oidc_state_store: dict[str, tuple[datetime, uuid.UUID]] = {}


def _encrypt_client_secret(plain: str) -> str:
    from runledger_api.core.config import settings  # noqa: PLC0415

    pepper = (settings.api_key_pepper or settings.secret_key).encode()
    return hmac.new(pepper, plain.encode(), hashlib.sha256).hexdigest() + ":" + plain


def _decrypt_client_secret(stored: str) -> str:
    if ":" in stored:
        return stored.split(":", 1)[1]
    return stored


def generate_oidc_state(provider_id: uuid.UUID) -> str:
    state = secrets.token_urlsafe(32)
    _oidc_state_store[state] = (datetime.now(UTC), provider_id)
    _gc_expired_states()
    return state


def validate_oidc_state(state: str) -> uuid.UUID:
    entry = _oidc_state_store.pop(state, None)
    if entry is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired OIDC state")
    created, provider_id = entry
    if (datetime.now(UTC) - created).total_seconds() > _STATE_TTL_SECONDS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "OIDC state has expired")
    return provider_id


def _gc_expired_states() -> None:
    now = datetime.now(UTC)
    expired = [
        k
        for k, (t, _) in _oidc_state_store.items()
        if (now - t).total_seconds() > _STATE_TTL_SECONDS * 2
    ]
    for k in expired:
        _oidc_state_store.pop(k, None)


async def build_oidc_authorize_url(provider: OIDCProvider, redirect_uri: str, state: str) -> str:
    discovery_url = (
        provider.discovery_url
        or f"{provider.issuer_url.rstrip('/')}/.well-known/openid-configuration"
    )
    discovery = await _cached_json(discovery_url, _oidc_doc_cache)
    auth_endpoint = discovery.get("authorization_endpoint")
    if not auth_endpoint:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "OIDC provider discovery missing authorization_endpoint",
        )
    params = {
        "response_type": "code",
        "client_id": provider.client_id,
        "redirect_uri": redirect_uri,
        "scope": provider.scopes or "openid email profile",
        "state": state,
    }
    if provider.audience:
        params["audience"] = provider.audience
    return f"{auth_endpoint}?{urlencode(params)}"


async def exchange_oidc_code(
    provider: OIDCProvider, code: str, redirect_uri: str
) -> dict[str, Any]:
    discovery_url = (
        provider.discovery_url
        or f"{provider.issuer_url.rstrip('/')}/.well-known/openid-configuration"
    )
    discovery = await _cached_json(discovery_url, _oidc_doc_cache)
    token_endpoint = discovery.get("token_endpoint")
    if not token_endpoint:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "OIDC provider discovery missing token_endpoint",
        )
    client_secret = _decrypt_client_secret(provider.client_secret_encrypted or "")
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            token_endpoint,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": provider.client_id,
                "client_secret": client_secret,
            },
        )
        if resp.status_code != 200:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                f"OIDC token exchange failed: {resp.text[:200]}",
            )
        return resp.json()


async def validate_oidc_id_token(provider: OIDCProvider, id_token: str) -> dict[str, Any]:
    _, jwks_uri = await _resolve_oidc_urls(provider)
    jwks = await _cached_json(jwks_uri, _oidc_jwks_cache)
    header = jwt.get_unverified_header(id_token)
    kid = header.get("kid")
    keys = jwks.get("keys") or []
    jwk = next((item for item in keys if item.get("kid") == kid), None)
    if jwk is None and len(keys) == 1:
        jwk = keys[0]
    if jwk is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No matching JWKS key for id_token")
    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
    return jwt.decode(
        id_token,
        key=public_key,
        algorithms=["RS256", "RS384", "RS512"],
        audience=provider.client_id,
        issuer=provider.issuer_url,
        options={"verify_aud": bool(provider.client_id)},
    )


async def find_or_create_user_from_oidc(
    db: AsyncSession,
    provider: OIDCProvider,
    claims: dict[str, Any],
) -> tuple[Any, ExternalIdentity]:
    from runledger_api.models.tenant import (  # noqa: PLC0415
        MemberStatusEnum,
        TenantRoleEnum,
        TenantUser,
        User,
        WorkspaceRoleEnum,
        WorkspaceUser,
    )

    sub = claims.get("sub")
    if not sub:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "OIDC token missing 'sub' claim")

    email_claim = (provider.claim_mappings or {}).get("email", "email")
    name_claim = (provider.claim_mappings or {}).get("name", "name")
    email = claims.get(email_claim)
    full_name = claims.get(name_claim)

    result = await db.execute(
        select(ExternalIdentity).where(
            ExternalIdentity.provider_type == "oidc",
            ExternalIdentity.provider_id == provider.id,
            ExternalIdentity.external_subject == str(sub),
        )
    )
    ext_id = result.scalar_one_or_none()

    if ext_id is not None:
        user = await db.get(User, ext_id.user_id)
        if user is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Linked user account not found")
        ext_id.last_login_at = datetime.now(UTC)
        if email:
            ext_id.external_email = email
        return user, ext_id

    if email:
        user_result = await db.execute(select(User).where(User.email == email))
        user = user_result.scalar_one_or_none()
    else:
        user = None

    if user is None:
        if not provider.auto_provision:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "No account linked to this identity. Ask your administrator to enable auto-provisioning or create your account.",
            )
        user = User(
            email=email or f"oidc-{sub}@external",
            full_name=full_name,
            is_active=True,
            email_verified=True,
        )
        db.add(user)
        await db.flush()

        tenant_id = provider.tenant_id
        if tenant_id is None:
            workspace = await db.get(Workspace, provider.workspace_id)
            tenant_id = workspace.tenant_id if workspace else None

        if tenant_id:
            db.add(
                TenantUser(
                    tenant_id=tenant_id,
                    user_id=user.id,
                    role=TenantRoleEnum(provider.default_tenant_role),
                    status=MemberStatusEnum.active,
                )
            )

        ws_role = WorkspaceRoleEnum(provider.default_workspace_role)
        db.add(
            WorkspaceUser(
                workspace_id=provider.workspace_id,
                user_id=user.id,
                role=ws_role,
                status=MemberStatusEnum.active,
            )
        )

    ext_id = ExternalIdentity(
        user_id=user.id,
        provider_type="oidc",
        provider_id=provider.id,
        external_subject=str(sub),
        external_email=email,
        last_login_at=datetime.now(UTC),
    )
    db.add(ext_id)
    return user, ext_id


# ── OAuth2 Authorization Code Flow ────────────────────────────────────────────

_oauth2_state_store: dict[str, tuple[datetime, uuid.UUID]] = {}


def generate_oauth2_state(provider_id: uuid.UUID) -> str:
    state = secrets.token_urlsafe(32)
    _oauth2_state_store[state] = (datetime.now(UTC), provider_id)
    _gc_oauth2_expired_states()
    return state


def validate_oauth2_state(state: str) -> uuid.UUID:
    entry = _oauth2_state_store.pop(state, None)
    if entry is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired OAuth2 state")
    created, provider_id = entry
    if (datetime.now(UTC) - created).total_seconds() > _STATE_TTL_SECONDS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "OAuth2 state has expired")
    return provider_id


def _gc_oauth2_expired_states() -> None:
    now = datetime.now(UTC)
    expired = [
        k
        for k, (t, _) in _oauth2_state_store.items()
        if (now - t).total_seconds() > _STATE_TTL_SECONDS * 2
    ]
    for k in expired:
        _oauth2_state_store.pop(k, None)


def build_oauth2_authorize_url(provider: OAuth2Provider, redirect_uri: str, state: str) -> str:
    params = {
        "response_type": "code",
        "client_id": provider.client_id,
        "redirect_uri": redirect_uri,
        "scope": provider.scopes or "openid email profile",
        "state": state,
    }
    return f"{provider.authorization_endpoint}?{urlencode(params)}"


async def exchange_oauth2_code(
    provider: OAuth2Provider, code: str, redirect_uri: str
) -> dict[str, Any]:
    client_secret = _decrypt_client_secret(provider.client_secret_encrypted or "")
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            provider.token_endpoint,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": provider.client_id,
                "client_secret": client_secret,
            },
        )
        if resp.status_code != 200:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                f"OAuth2 token exchange failed: {resp.text[:200]}",
            )
        return resp.json()


async def fetch_oauth2_userinfo(
    provider: OAuth2Provider, access_token: str
) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            provider.userinfo_endpoint,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if resp.status_code != 200:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                f"OAuth2 userinfo request failed: {resp.text[:200]}",
            )
        return resp.json()


async def find_or_create_user_from_oauth2(
    db: AsyncSession,
    provider: OAuth2Provider,
    userinfo: dict[str, Any],
) -> tuple[Any, ExternalIdentity]:
    from runledger_api.models.tenant import (  # noqa: PLC0415
        MemberStatusEnum,
        TenantRoleEnum,
        TenantUser,
        User,
        WorkspaceRoleEnum,
        WorkspaceUser,
    )

    subject = userinfo.get(provider.userinfo_id_field)
    if not subject:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            f"OAuth2 userinfo missing '{provider.userinfo_id_field}' field",
        )

    email = userinfo.get(provider.userinfo_email_field)
    full_name = userinfo.get(provider.userinfo_name_field)

    result = await db.execute(
        select(ExternalIdentity).where(
            ExternalIdentity.provider_type == "oauth2",
            ExternalIdentity.provider_id == provider.id,
            ExternalIdentity.external_subject == str(subject),
        )
    )
    ext_id = result.scalar_one_or_none()

    if ext_id is not None:
        user = await db.get(User, ext_id.user_id)
        if user is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Linked user account not found")
        ext_id.last_login_at = datetime.now(UTC)
        if email:
            ext_id.external_email = email
        return user, ext_id

    if email:
        user_result = await db.execute(select(User).where(User.email == email))
        user = user_result.scalar_one_or_none()
    else:
        user = None

    if user is None:
        if not provider.auto_provision:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "No account linked to this identity. Ask your administrator to enable auto-provisioning or create your account.",
            )
        user = User(
            email=email or f"oauth2-{subject}@external",
            full_name=full_name,
            is_active=True,
            email_verified=True,
        )
        db.add(user)
        await db.flush()

        tenant_id = provider.tenant_id
        if tenant_id is None:
            workspace = await db.get(Workspace, provider.workspace_id)
            tenant_id = workspace.tenant_id if workspace else None

        if tenant_id:
            db.add(
                TenantUser(
                    tenant_id=tenant_id,
                    user_id=user.id,
                    role=TenantRoleEnum(provider.default_tenant_role),
                    status=MemberStatusEnum.active,
                )
            )

        db.add(
            WorkspaceUser(
                workspace_id=provider.workspace_id,
                user_id=user.id,
                role=WorkspaceRoleEnum(provider.default_workspace_role),
                status=MemberStatusEnum.active,
            )
        )

    ext_id = ExternalIdentity(
        user_id=user.id,
        provider_type="oauth2",
        provider_id=provider.id,
        external_subject=str(subject),
        external_email=email,
        last_login_at=datetime.now(UTC),
    )
    db.add(ext_id)
    return user, ext_id


# ── LDAP Authentication ──────────────────────────────────────────────────────


async def authenticate_ldap(
    provider: LDAPProvider,
    username: str,
    password: str,
) -> dict[str, str]:
    try:
        import ldap3  # noqa: PLC0415
    except ImportError as exc:
        raise HTTPException(
            status.HTTP_501_NOT_IMPLEMENTED,
            "LDAP support requires the ldap3 package. Install with: pip install ldap3",
        ) from exc

    use_ssl = provider.use_ssl
    server = ldap3.Server(provider.server_url, use_ssl=use_ssl, get_info=ldap3.NONE)

    bind_dn = provider.bind_dn
    bind_pw = _decrypt_client_secret(provider.bind_password_encrypted or "") if bind_dn else None

    conn = ldap3.Connection(server, user=bind_dn, password=bind_pw, auto_bind=False)

    try:
        conn.open()
        if provider.start_tls and not use_ssl:
            conn.start_tls()

        if bind_dn:
            if not conn.bind():
                raise HTTPException(status.HTTP_502_BAD_GATEWAY, "LDAP service bind failed")

        search_filter = provider.user_search_filter.replace("{username}", ldap3.utils.conv.escape_filter_chars(username))
        conn.search(
            provider.user_search_base,
            search_filter,
            search_scope=ldap3.SUBTREE,
            attributes=[provider.email_attribute, provider.name_attribute, provider.uid_attribute],
        )

        if not conn.entries:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid LDAP credentials")

        user_entry = conn.entries[0]
        user_dn = user_entry.entry_dn

        user_conn = ldap3.Connection(server, user=user_dn, password=password, auto_bind=False)
        user_conn.open()
        if provider.start_tls and not use_ssl:
            user_conn.start_tls()
        if not user_conn.bind():
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid LDAP credentials")
        user_conn.unbind()

        def _attr(name: str) -> str:
            val = getattr(user_entry, name, None)
            if val is None:
                return ""
            return str(val.value) if hasattr(val, "value") else str(val)

        return {
            "uid": _attr(provider.uid_attribute) or username,
            "email": _attr(provider.email_attribute),
            "name": _attr(provider.name_attribute),
        }
    finally:
        conn.unbind()


async def find_or_create_user_from_ldap(
    db: AsyncSession,
    provider: LDAPProvider,
    ldap_user: dict[str, str],
) -> tuple[Any, ExternalIdentity]:
    from runledger_api.models.tenant import (  # noqa: PLC0415
        MemberStatusEnum,
        TenantRoleEnum,
        TenantUser,
        User,
        WorkspaceRoleEnum,
        WorkspaceUser,
    )

    uid = ldap_user.get("uid", "")
    email = ldap_user.get("email", "")
    full_name = ldap_user.get("name", "")

    if not uid:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "LDAP user missing uid")

    result = await db.execute(
        select(ExternalIdentity).where(
            ExternalIdentity.provider_type == "ldap",
            ExternalIdentity.provider_id == provider.id,
            ExternalIdentity.external_subject == uid,
        )
    )
    ext_id = result.scalar_one_or_none()

    if ext_id is not None:
        user = await db.get(User, ext_id.user_id)
        if user is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Linked user account not found")
        ext_id.last_login_at = datetime.now(UTC)
        if email:
            ext_id.external_email = email
        return user, ext_id

    if email:
        user_result = await db.execute(select(User).where(User.email == email))
        user = user_result.scalar_one_or_none()
    else:
        user = None

    if user is None:
        if not provider.auto_provision:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "No account linked to this identity. Ask your administrator to enable auto-provisioning or create your account.",
            )
        user = User(
            email=email or f"ldap-{uid}@external",
            full_name=full_name,
            is_active=True,
            email_verified=True,
        )
        db.add(user)
        await db.flush()

        tenant_id = provider.tenant_id
        if tenant_id is None:
            workspace = await db.get(Workspace, provider.workspace_id)
            tenant_id = workspace.tenant_id if workspace else None

        if tenant_id:
            db.add(
                TenantUser(
                    tenant_id=tenant_id,
                    user_id=user.id,
                    role=TenantRoleEnum(provider.default_tenant_role),
                    status=MemberStatusEnum.active,
                )
            )

        db.add(
            WorkspaceUser(
                workspace_id=provider.workspace_id,
                user_id=user.id,
                role=WorkspaceRoleEnum(provider.default_workspace_role),
                status=MemberStatusEnum.active,
            )
        )

    ext_id = ExternalIdentity(
        user_id=user.id,
        provider_type="ldap",
        provider_id=provider.id,
        external_subject=uid,
        external_email=email,
        last_login_at=datetime.now(UTC),
    )
    db.add(ext_id)
    return user, ext_id


async def enforce_required_metadata(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    metadata: dict[str, Any] | None,
) -> list[str]:
    settings = await get_or_create_security_settings(db, workspace_id)
    required = settings.required_metadata_fields or []
    if not required:
        return []
    metadata = metadata or {}
    missing = [field for field in required if metadata.get(field) in (None, "", [])]
    if missing and settings.required_metadata_mode == "reject":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Missing required metadata fields: {', '.join(missing)}",
        )
    return missing
