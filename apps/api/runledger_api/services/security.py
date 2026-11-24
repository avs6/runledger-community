from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import ipaddress
import json
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
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


async def _find_jwk(jwks_uri: str, kid: str | None) -> dict[str, Any] | None:
    """Find the signing key; refetch the JWKS once when the kid is unknown (key rotation)."""
    for attempt in range(2):
        if attempt == 1:
            _oidc_jwks_cache.pop(jwks_uri, None)
        jwks = await _cached_json(jwks_uri, _oidc_jwks_cache)
        keys = jwks.get("keys") or []
        jwk = next((item for item in keys if item.get("kid") == kid), None)
        if jwk is None and kid is None and len(keys) == 1:
            jwk = keys[0]
        if jwk is not None:
            return jwk
    return None


def _looks_like_jwt(token: str) -> bool:
    parts = token.split(".")
    return len(parts) == 3 and all(parts)


async def authenticate_oidc_token(token: str, db: AsyncSession) -> OIDCAuthResult | None:
    # API keys and other opaque tokens never reach the IdP-discovery path.
    if not _looks_like_jwt(token):
        return None
    try:
        unverified_iss = jwt.decode(token, options={"verify_signature": False}).get("iss")
    except jwt.PyJWTError:
        return None
    if not unverified_iss:
        return None

    providers = (
        (
            await db.execute(
                select(OIDCProvider).where(
                    OIDCProvider.is_active.is_(True),
                    OIDCProvider.issuer_url == unverified_iss,
                )
            )
        )
        .scalars()
        .all()
    )
    if not providers:
        return None

    last_error: Exception | None = None
    for provider in providers:
        # The token must be addressed to us: audience (or client_id) is mandatory.
        expected_aud = provider.audience or provider.client_id
        if not expected_aud:
            continue
        try:
            _, jwks_uri = await _resolve_oidc_urls(provider)
            header = jwt.get_unverified_header(token)
            jwk = await _find_jwk(jwks_uri, header.get("kid"))
            if jwk is None:
                continue
            public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
            claims = jwt.decode(
                token,
                key=public_key,
                algorithms=["RS256", "RS384", "RS512"],
                audience=expected_aud,
                issuer=provider.issuer_url,
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


def _trusted_networks(value: str) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    networks = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            networks.append(ipaddress.ip_network(part, strict=False))
        except ValueError:
            continue
    return networks


def get_client_ip(x_forwarded_for: str | None, fallback_host: str | None) -> str | None:
    """The client's address: the socket peer (``fallback_host``) unless the peer is a
    trusted proxy (``TRUSTED_PROXIES``, IPs or CIDRs), in which case X-Forwarded-For is
    walked from the right and the first address that isn't a trusted proxy wins. A client
    can't claim an address by sending the header itself (review G-18)."""
    from runledger_api.core.config import settings  # noqa: PLC0415

    trusted = _trusted_networks(settings.trusted_proxies)

    def is_trusted(value: str | None) -> bool:
        try:
            ip = ipaddress.ip_address((value or "").strip())
        except ValueError:
            return False
        return any(ip in net for net in trusted)

    if not x_forwarded_for or not is_trusted(fallback_host):
        return fallback_host
    client = fallback_host
    for hop in reversed([p.strip() for p in x_forwarded_for.split(",")]):
        try:
            ipaddress.ip_address(hop)
        except ValueError:
            break
        client = hop
        if not is_trusted(hop):
            break
    return client


async def evaluate_ip_acl(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    api_key_id: uuid.UUID | None,
    client_ip: str | None,
    principal_user_id: uuid.UUID | None = None,
) -> None:
    """Enforce IP ACL rules for one request; raises 403 when the client IP is refused.

    Rules that apply: global, this workspace's, this API key's, and those of access
    groups the request's principal user belongs to (legacy unmapped team rules never
    apply). The first matching rule by priority decides (allow or deny). With no
    match, the request is refused only if an ``allow`` rule applies (allow-list mode);
    deny-only rule sets block just the listed ranges. ``client_ip`` is the socket peer,
    or the forwarded address when the peer is a trusted proxy (gateway-rs; G-18)."""
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
    group_ids = {rule.access_group_id for rule in rules if rule.access_group_id is not None}
    member_of: set[uuid.UUID] = set()
    if group_ids and principal_user_id is not None:
        from runledger_api.models.access_groups import AccessGroupMember  # noqa: PLC0415

        member_of = set(
            (
                await db.execute(
                    select(AccessGroupMember.group_id).where(
                        AccessGroupMember.group_id.in_(group_ids),
                        AccessGroupMember.user_id == principal_user_id,
                    )
                )
            )
            .scalars()
            .all()
        )
    applicable = [
        rule
        for rule in rules
        if (rule.access_group_id is None and not rule.team_name)
        or (rule.access_group_id is not None and rule.access_group_id in member_of)
    ]
    if not applicable:
        return

    if not client_ip:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Client IP required when ACL is active")
    try:
        ip_obj = ipaddress.ip_address(client_ip.strip())
    except ValueError:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Client IP is not a valid address") from None

    for rule in applicable:
        try:
            network = ipaddress.ip_network(rule.cidr, strict=False)
        except ValueError:
            continue
        if ip_obj in network:
            if rule.action == "allow":
                return
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Client IP is denied by policy")
    if any(rule.action == "allow" for rule in applicable):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Client IP is not on the allow list")


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


@dataclass
class AuthFlowState:
    """Server-side half of an SSO authorization request (never sent to the browser
    except ``state`` itself; the PKCE verifier stays in Redis)."""

    state: str
    nonce: str
    code_verifier: str
    provider_id: uuid.UUID

    @property
    def code_challenge(self) -> str:
        digest = hashlib.sha256(self.code_verifier.encode()).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def _state_key(kind: str, state: str) -> str:
    return f"rl:auth:state:{kind}:{state}"


async def create_auth_state(redis: Any, kind: str, provider_id: uuid.UUID) -> AuthFlowState:
    """Create a single-use SSO state (kind = "oidc" | "oauth2") stored in Redis.

    Redis makes the flow work across API workers/replicas; the entry expires after
    ``auth_state_ttl_seconds`` and is deleted when consumed.
    """
    from runledger_api.core.config import settings  # noqa: PLC0415

    flow = AuthFlowState(
        state=secrets.token_urlsafe(32),
        nonce=secrets.token_urlsafe(24),
        code_verifier=secrets.token_urlsafe(64),
        provider_id=provider_id,
    )
    payload = json.dumps(
        {"provider_id": str(provider_id), "nonce": flow.nonce, "verifier": flow.code_verifier}
    )
    await redis.set(_state_key(kind, flow.state), payload, ex=settings.auth_state_ttl_seconds)
    return flow


async def consume_auth_state(redis: Any, kind: str, state: str) -> AuthFlowState:
    """Atomically fetch-and-delete the SSO state. Raises 400 when missing/expired."""
    key = _state_key(kind, state)
    raw = await redis.getdel(key)
    if not raw:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid or expired {kind} state")
    data = json.loads(raw)
    return AuthFlowState(
        state=state,
        nonce=data["nonce"],
        code_verifier=data["verifier"],
        provider_id=uuid.UUID(data["provider_id"]),
    )


def sso_callback_url(kind: str) -> str:
    """The only redirect URI RunLedger registers with IdPs (pinned to APP_BASE_URL)."""
    from runledger_api.core.config import settings  # noqa: PLC0415

    return f"{settings.app_base_url.rstrip('/')}/auth/{kind}/callback"


def _provider_secret(stored: str | None) -> str:
    """Plaintext of a provider secret column.

    The ``*_encrypted`` columns use ``core.secrets.EncryptedText``: values are
    Fernet/KMS-encrypted at rest and decrypted on load (review S-03), so the ORM
    attribute already holds the plaintext.
    """
    return stored or ""


async def build_oidc_authorize_url(
    provider: OIDCProvider, redirect_uri: str, flow: AuthFlowState
) -> str:
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
        "state": flow.state,
        "nonce": flow.nonce,
        "code_challenge": flow.code_challenge,
        "code_challenge_method": "S256",
    }
    if provider.audience:
        params["audience"] = provider.audience
    return f"{auth_endpoint}?{urlencode(params)}"


async def exchange_oidc_code(
    provider: OIDCProvider, code: str, redirect_uri: str, code_verifier: str
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
    client_secret = _provider_secret(provider.client_secret_encrypted)
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            token_endpoint,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": provider.client_id,
                "client_secret": client_secret,
                "code_verifier": code_verifier,
            },
        )
        if resp.status_code != 200:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                f"OIDC token exchange failed: {resp.text[:200]}",
            )
        return resp.json()


async def validate_oidc_id_token(
    provider: OIDCProvider, id_token: str, expected_nonce: str
) -> dict[str, Any]:
    if not provider.client_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "OIDC provider has no client_id")
    _, jwks_uri = await _resolve_oidc_urls(provider)
    header = jwt.get_unverified_header(id_token)
    jwk = await _find_jwk(jwks_uri, header.get("kid"))
    if jwk is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No matching JWKS key for id_token")
    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
    try:
        claims = jwt.decode(
            id_token,
            key=public_key,
            algorithms=["RS256", "RS384", "RS512"],
            audience=provider.client_id,
            issuer=provider.issuer_url,
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid OIDC id_token") from exc
    if not hmac.compare_digest(str(claims.get("nonce") or ""), expected_nonce):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "OIDC id_token nonce mismatch")
    return claims


async def _provider_tenant_id(db: AsyncSession, provider: Any) -> uuid.UUID | None:
    if getattr(provider, "tenant_id", None):
        return provider.tenant_id
    workspace = await db.get(Workspace, provider.workspace_id)
    return workspace.tenant_id if workspace else None


async def resolve_external_user(
    db: AsyncSession,
    *,
    provider_type: str,
    provider: Any,
    subject: str,
    email: str | None,
    full_name: str | None,
    email_trusted: bool,
) -> tuple[Any, ExternalIdentity]:
    """Map an external identity (OIDC/OAuth2/LDAP) to a RunLedger user.

    Rules (closes cross-tenant account takeover through admin-configured IdPs):

    1. A previously linked identity (provider + subject) signs in as its user.
    2. Otherwise, an existing account with the same email is linked **only** when the
       IdP asserts the email as verified (``email_trusted``) and the account is
       managed solely by the provider's organization (not a platform admin, active
       membership there, no memberships elsewhere).
    3. Otherwise, a new account is provisioned in the provider's org when
       ``auto_provision`` is on. An email that already belongs to an account outside
       the org is refused rather than provisioned.
    """
    from runledger_api.models.tenant import (  # noqa: PLC0415
        MemberStatusEnum,
        TenantRoleEnum,
        TenantUser,
        User,
        WorkspaceRoleEnum,
        WorkspaceUser,
    )
    from runledger_api.services.sessions import is_tenant_managed_user  # noqa: PLC0415

    result = await db.execute(
        select(ExternalIdentity).where(
            ExternalIdentity.provider_type == provider_type,
            ExternalIdentity.provider_id == provider.id,
            ExternalIdentity.external_subject == subject,
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

    tenant_id = await _provider_tenant_id(db, provider)
    if tenant_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Identity provider has no organization")

    user = None
    if email:
        user = (
            await db.execute(select(User).where(func.lower(User.email) == email.lower()))
        ).scalar_one_or_none()

    if user is not None:
        if not email_trusted or not await is_tenant_managed_user(db, user, tenant_id):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "An account with this email already exists and cannot be linked to this "
                "sign-in provider. Sign in with your password, or ask a platform "
                "administrator to link the account.",
            )
    else:
        if not provider.auto_provision:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "No account linked to this identity. Ask your administrator to enable "
                "auto-provisioning or create your account.",
            )
        user = User(
            email=email or f"{provider_type}-{subject}@external",
            full_name=full_name,
            is_active=True,
            email_verified=bool(email and email_trusted),
        )
        db.add(user)
        await db.flush()
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
        provider_type=provider_type,
        provider_id=provider.id,
        external_subject=subject,
        external_email=email,
        last_login_at=datetime.now(UTC),
    )
    db.add(ext_id)
    return user, ext_id


def _truthy_claim(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


async def find_or_create_user_from_oidc(
    db: AsyncSession,
    provider: OIDCProvider,
    claims: dict[str, Any],
) -> tuple[Any, ExternalIdentity]:
    sub = claims.get("sub")
    if not sub:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "OIDC token missing 'sub' claim")
    mappings = provider.claim_mappings or {}
    email = claims.get(mappings.get("email", "email"))
    full_name = claims.get(mappings.get("name", "name"))
    return await resolve_external_user(
        db,
        provider_type="oidc",
        provider=provider,
        subject=str(sub),
        email=str(email) if email else None,
        full_name=full_name,
        email_trusted=_truthy_claim(claims.get("email_verified", False)),
    )


# ── OAuth2 Authorization Code Flow ────────────────────────────────────────────


def build_oauth2_authorize_url(
    provider: OAuth2Provider, redirect_uri: str, flow: AuthFlowState
) -> str:
    params = {
        "response_type": "code",
        "client_id": provider.client_id,
        "redirect_uri": redirect_uri,
        "scope": provider.scopes or "openid email profile",
        "state": flow.state,
        "code_challenge": flow.code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{provider.authorization_endpoint}?{urlencode(params)}"


async def exchange_oauth2_code(
    provider: OAuth2Provider, code: str, redirect_uri: str, code_verifier: str
) -> dict[str, Any]:
    client_secret = _provider_secret(provider.client_secret_encrypted)
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            provider.token_endpoint,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": provider.client_id,
                "client_secret": client_secret,
                "code_verifier": code_verifier,
            },
        )
        if resp.status_code != 200:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                f"OAuth2 token exchange failed: {resp.text[:200]}",
            )
        return resp.json()


async def fetch_oauth2_userinfo(provider: OAuth2Provider, access_token: str) -> dict[str, Any]:
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
    subject = userinfo.get(provider.userinfo_id_field)
    if not subject:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            f"OAuth2 userinfo missing '{provider.userinfo_id_field}' field",
        )
    email = userinfo.get(provider.userinfo_email_field)
    return await resolve_external_user(
        db,
        provider_type="oauth2",
        provider=provider,
        subject=str(subject),
        email=str(email) if email else None,
        full_name=userinfo.get(provider.userinfo_name_field),
        # Plain OAuth2 has no standard verified-email claim; trust it only when the
        # provider explicitly asserts email_verified.
        email_trusted=_truthy_claim(userinfo.get("email_verified", False)),
    )


# ── LDAP Authentication ──────────────────────────────────────────────────────


def _authenticate_ldap_sync(
    provider: Any,
    username: str,
    password: str,
) -> dict[str, str]:
    import ldap3  # noqa: PLC0415

    use_ssl = provider.use_ssl
    server = ldap3.Server(provider.server_url, use_ssl=use_ssl, get_info=ldap3.NONE)

    bind_dn = provider.bind_dn
    bind_pw = _provider_secret(provider.bind_password_encrypted) if bind_dn else None
    if bind_dn and not bind_pw:
        # Never fall back to an unauthenticated service bind (S-25).
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "LDAP service bind password missing")

    conn = ldap3.Connection(server, user=bind_dn, password=bind_pw, auto_bind=False)

    try:
        conn.open()
        if provider.start_tls and not use_ssl:
            conn.start_tls()

        if bind_dn and not conn.bind():
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "LDAP service bind failed")

        search_filter = provider.user_search_filter.replace(
            "{username}", ldap3.utils.conv.escape_filter_chars(username)
        )
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
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 — directory/network errors
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "LDAP directory unavailable") from exc
    finally:
        conn.unbind()


async def authenticate_ldap(
    provider: LDAPProvider,
    username: str,
    password: str,
) -> dict[str, str]:
    # An empty password would make the user bind an anonymous ("unauthenticated")
    # bind, which many directories accept. Reject it before touching LDAP.
    if not username or not password:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid LDAP credentials")
    try:
        import ldap3  # noqa: F401, PLC0415
    except ImportError as exc:
        raise HTTPException(
            status.HTTP_501_NOT_IMPLEMENTED,
            "LDAP support requires the ldap3 package. Install with: pip install ldap3",
        ) from exc
    # ldap3 is synchronous; keep the event loop free (S-25). Hand the worker thread a
    # plain snapshot so it never touches the ORM session (no lazy loads off-loop).
    snapshot = SimpleNamespace(
        server_url=provider.server_url,
        use_ssl=provider.use_ssl,
        start_tls=provider.start_tls,
        bind_dn=provider.bind_dn,
        bind_password_encrypted=provider.bind_password_encrypted,
        user_search_base=provider.user_search_base,
        user_search_filter=provider.user_search_filter,
        email_attribute=provider.email_attribute,
        name_attribute=provider.name_attribute,
        uid_attribute=provider.uid_attribute,
    )
    return await asyncio.to_thread(_authenticate_ldap_sync, snapshot, username, password)


async def find_or_create_user_from_ldap(
    db: AsyncSession,
    provider: LDAPProvider,
    ldap_user: dict[str, str],
) -> tuple[Any, ExternalIdentity]:
    uid = ldap_user.get("uid", "")
    if not uid:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "LDAP user missing uid")
    email = ldap_user.get("email") or None
    return await resolve_external_user(
        db,
        provider_type="ldap",
        provider=provider,
        subject=uid,
        email=email,
        full_name=ldap_user.get("name") or None,
        # The directory is operated by the org that configured it, so its email
        # attribute is only trusted for accounts that org already manages exclusively
        # (enforced inside resolve_external_user).
        email_trusted=True,
    )


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


# ── Row-level security context (tr-security: defence in depth) ───────────────
#
# Migration ``security_secrets_audit_rls`` puts an RLS policy on tenant tables
# keyed on two per-transaction settings. ``apply_tenant_context`` records them
# for the request's session; an ``after_begin`` hook re-applies them at the start
# of every transaction (they are SET LOCAL, so a pooled connection never carries
# them into another request). Session (dashboard) keys get the whole org, since
# org roles legitimately span workspaces; workload keys are pinned to their
# workspace. With nothing set (workers, internal calls) the policy allows all.

_RLS_TENANT = "rl_rls_tenant_id"
_RLS_WORKSPACE = "rl_rls_workspace_id"
_SET_RLS_SQL = (
    "SELECT set_config('app.tenant_id', :tenant, true),"
    " set_config('app.workspace_id', :workspace, true)"
)


def _rls_params(info: dict[str, Any]) -> dict[str, str]:
    return {"tenant": info.get(_RLS_TENANT, ""), "workspace": info.get(_RLS_WORKSPACE, "")}


async def apply_tenant_context(db: Any, workspace: Any, *, pin_workspace: bool) -> None:
    """Scope this request's DB session to the caller's org (and workspace)."""
    info = getattr(db, "info", None)
    sync_session = getattr(db, "sync_session", None)
    if not isinstance(info, dict) or sync_session is None:
        return  # not a real AsyncSession (unit tests use mocks)
    tenant_id = getattr(workspace, "tenant_id", None)
    info[_RLS_TENANT] = str(tenant_id) if tenant_id else ""
    info[_RLS_WORKSPACE] = str(workspace.id) if pin_workspace else ""
    bind = db.get_bind()
    if bind.dialect.name != "postgresql":
        return
    from sqlalchemy import text  # noqa: PLC0415

    await db.execute(text(_SET_RLS_SQL), _rls_params(info))


def _rls_after_begin(session: Any, transaction: Any, connection: Any) -> None:
    info = session.info
    if not info.get(_RLS_TENANT) or connection.dialect.name != "postgresql":
        return
    from sqlalchemy import text  # noqa: PLC0415

    connection.execute(text(_SET_RLS_SQL), _rls_params(info))


def _install_rls_hook() -> None:
    from sqlalchemy import event as sa_event  # noqa: PLC0415
    from sqlalchemy.orm import Session  # noqa: PLC0415

    if not sa_event.contains(Session, "after_begin", _rls_after_begin):
        sa_event.listen(Session, "after_begin", _rls_after_begin)


_install_rls_hook()
