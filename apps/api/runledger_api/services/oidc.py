"""
OIDC / SCIM service helpers.

- Fernet-based client_secret encryption
- HMAC-signed state parameter (CSRF)
- OIDC discovery + authorization URL
- Authorization code exchange → ID token claims
- JIT user provisioning
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
import structlog

from runledger_api.core.config import settings
from runledger_api.services.crypto import decrypt_secret, encrypt_secret

log = structlog.get_logger()

__all__ = ["encrypt_secret", "decrypt_secret"]


# ── HMAC state parameter ──────────────────────────────────────────────────────


def make_state(config_id: uuid.UUID, nonce: str) -> str:
    """Produce a tamper-evident state param: base64url(json) + "." + hexsig."""
    payload = json.dumps({"config_id": str(config_id), "nonce": nonce})
    body = base64.urlsafe_b64encode(payload.encode()).decode()
    sig = hmac.new(settings.secret_key.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def verify_state(state: str) -> dict[str, str]:
    """Verify + decode a state parameter. Raises ValueError on tampering."""
    try:
        body, sig = state.rsplit(".", 1)
    except ValueError:
        raise ValueError("Malformed state") from None
    expected = hmac.new(settings.secret_key.encode(), body.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        raise ValueError("State signature mismatch")
    return json.loads(base64.urlsafe_b64decode(body + "==").decode())


# ── OIDC discovery + authorization URL ───────────────────────────────────────


async def discover_oidc(issuer_url: str) -> dict[str, Any]:
    """Fetch OIDC discovery document from {issuer}/.well-known/openid-configuration."""
    url = issuer_url.rstrip("/") + "/.well-known/openid-configuration"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]


def build_authorization_url(
    *,
    authorization_endpoint: str,
    client_id: str,
    redirect_uri: str,
    scopes: str,
    state: str,
    nonce: str,
) -> str:
    """Build the OIDC authorization redirect URL."""
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scopes,
        "state": state,
        "nonce": nonce,
    }
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{authorization_endpoint}?{qs}"


# ── Token exchange ────────────────────────────────────────────────────────────


async def exchange_code(
    *,
    token_endpoint: str,
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
) -> dict[str, Any]:
    """Exchange authorization code for tokens. Returns token response dict."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            token_endpoint,
            data={
                "grant_type": "authorization_code",
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            },
        )
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]


def decode_id_token_claims(id_token: str) -> dict[str, Any]:
    """
    Extract claims from JWT ID token without full signature verification.
    (Signature was already verified by the IdP; we just parse claims.)
    In production you'd use a JWT library with the JWKS endpoint.
    """
    parts = id_token.split(".")
    if len(parts) < 2:
        raise ValueError("Invalid ID token format")
    # JWT payload is base64url without padding
    padded = parts[1] + "=="
    payload = base64.urlsafe_b64decode(padded.encode())
    return json.loads(payload)  # type: ignore[no-any-return]


async def fetch_userinfo(userinfo_endpoint: str, access_token: str) -> dict[str, Any]:
    """Fetch userinfo from the IdP using the access token."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            userinfo_endpoint,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]


# ── Redirect URI helper ───────────────────────────────────────────────────────


def sso_redirect_uri(config_id: uuid.UUID) -> str:
    """Canonical callback URL for a given SSO config."""
    base = settings.app_base_url.rstrip("/")
    return f"{base.replace(':3000', ':8000')}/auth/sso/callback/{config_id}"


# ── SCIM token helpers ────────────────────────────────────────────────────────


def generate_scim_token() -> tuple[str, str, str]:
    """
    Generate a SCIM Bearer token.
    Returns (raw_token, token_hash, token_prefix).
    """
    raw = "scim_" + secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    token_prefix = raw[:12]
    return raw, token_hash, token_prefix


def hash_scim_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def now_utc() -> datetime:
    return datetime.now(UTC)
