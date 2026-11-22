"""Per-workspace signing keys for billing snapshots and signed exports (review F-03).

Each workspace signs with its own HMAC key derived from ``SECRET_KEY`` and the
workspace's ``billing_signing_version``; the key id recorded with a signature is
``ws-v<version>``. A tenant can fetch its key to verify its own exports, and doing so
reveals nothing about other tenants or the platform secret. Rotating bumps the version:
new signatures use the new key and signatures made with older versions still verify.

Signatures made before per-workspace keys existed carry key id ``v1`` (the platform
secret) and remain verifiable server-side through ``verify``.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

from runledger_api.core.config import settings

LEGACY_KEY_ID = "v1"


def key_id(version: int) -> str:
    return f"ws-v{version}"


def workspace_billing_key(workspace_id: Any, version: int) -> str:
    """The workspace's billing signing key for ``version`` (hex)."""
    base = hashlib.sha256(f"{settings.secret_key}:billing-signing".encode()).digest()
    return hmac.new(base, f"billing:{workspace_id}:{version}".encode(), hashlib.sha256).hexdigest()


def canonical(data: dict[str, Any]) -> bytes:
    """Canonical JSON (sorted keys) — the exact bytes a signature covers."""
    return json.dumps(data, sort_keys=True, default=str).encode()


def sign(data: dict[str, Any], workspace_id: Any, version: int) -> tuple[str, str]:
    """Return ``(signature_hex, key_id)`` for ``data``."""
    key = workspace_billing_key(workspace_id, version)
    return hmac.new(key.encode(), canonical(data), hashlib.sha256).hexdigest(), key_id(version)


def verify(data: dict[str, Any], signature: str, workspace_id: Any, signing_key_id: str) -> bool:
    """Check ``signature`` over ``data`` with the key ``signing_key_id`` names."""
    if signing_key_id == LEGACY_KEY_ID:
        key = settings.secret_key
    elif signing_key_id.startswith("ws-v") and signing_key_id[4:].isdigit():
        key = workspace_billing_key(workspace_id, int(signing_key_id[4:]))
    else:
        return False
    expected = hmac.new(key.encode(), canonical(data), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def webhook_secret(notification_id: Any, version: int) -> str:
    """A budget webhook destination's own signing secret (hex).

    Receivers verify ``X-RunLedger-Signature: sha256=<hmac>`` of the raw body with
    it; one destination's secret can't verify or forge another's deliveries.
    """
    base = hashlib.sha256(f"{settings.secret_key}:budget-webhook".encode()).digest()
    return hmac.new(
        base, f"budget-webhook:{notification_id}:{version}".encode(), hashlib.sha256
    ).hexdigest()
