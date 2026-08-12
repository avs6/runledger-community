from __future__ import annotations

import ipaddress
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

import httpx
import jwt
from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.security import IpAclRule, OIDCProvider, WorkspaceSecuritySettings
from runledger_api.models.tenant import Workspace


@dataclass
class OIDCAuthResult:
    workspace: Workspace
    provider: OIDCProvider
    claims: dict[str, Any]


_OIDC_CACHE_TTL_SECONDS = 300
_oidc_doc_cache: dict[str, tuple[datetime, dict[str, Any]]] = {}
_oidc_jwks_cache: dict[str, tuple[datetime, dict[str, Any]]] = {}


async def _cached_json(url: str, cache: dict[str, tuple[datetime, dict[str, Any]]]) -> dict[str, Any]:
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
    discovery_url = provider.discovery_url or f"{provider.issuer_url.rstrip('/')}/.well-known/openid-configuration"
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
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid OIDC bearer token") from last_error
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
            select(WorkspaceSecuritySettings).where(WorkspaceSecuritySettings.workspace_id == workspace_id)
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    settings = WorkspaceSecuritySettings(workspace_id=workspace_id)
    db.add(settings)
    await db.commit()
    await db.refresh(settings)
    return settings


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

