"""Per-workspace signing for ``POST /ingest/v1/signed`` (review I-15).

Each workspace has its own HMAC secret, derived from a base secret and the
workspace's ``ingest_signing_version``. Rotating bumps the version, so the old
secret stops working immediately. The base secret is ``INGEST_SIGNING_SECRET`` or,
if unset, derived from ``SECRET_KEY``; it never falls back to ``ADMIN_SECRET``.

Signature (hex HMAC-SHA256 with the workspace secret) over::

    "<workspace_id>.<timestamp>.<nonce>." + raw_body

Headers: ``X-RunLedger-Signature``, ``X-RunLedger-Timestamp`` (ISO-8601, within
INGEST_SIGNATURE_TOLERANCE_SECONDS) and ``X-RunLedger-Nonce`` (unique per request;
a nonce is accepted once, so captured requests cannot be replayed).
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status

from runledger_api.core.config import settings


def _base_secret() -> bytes:
    if settings.ingest_signing_secret:
        return settings.ingest_signing_secret.encode()
    return hashlib.sha256(f"{settings.secret_key}:ingest-webhook".encode()).digest()


def workspace_signing_secret(workspace_id: Any, version: int) -> str:
    """The workspace's current signing secret (hex)."""
    return hmac.new(
        _base_secret(), f"ingest:{workspace_id}:{version}".encode(), hashlib.sha256
    ).hexdigest()


def sign(secret: str, workspace_id: Any, timestamp: str, nonce: str, body: bytes) -> str:
    message = f"{workspace_id}.{timestamp}.{nonce}.".encode() + body
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


async def verify_signed_ingest(
    redis: Any,
    *,
    workspace_id: Any,
    version: int,
    timestamp: str,
    nonce: str,
    body: bytes,
    signature: str,
) -> None:
    """Raise 400/401/409 unless the request is fresh, correctly signed and unseen."""
    try:
        ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid ingest timestamp") from exc
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    tolerance = settings.ingest_signature_tolerance_seconds
    if abs(datetime.now(UTC) - ts) > timedelta(seconds=tolerance):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Signed ingest timestamp expired")
    if not nonce or len(nonce) > 128:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "X-RunLedger-Nonce is required")

    expected = sign(
        workspace_signing_secret(workspace_id, version), workspace_id, timestamp, nonce, body
    )
    if not hmac.compare_digest(expected, signature.strip().lower()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid ingest signature")

    # Each nonce once per workspace, remembered for twice the timestamp window.
    first_use = await redis.set(
        f"rl:ingest:nonce:{workspace_id}:{nonce}", "1", nx=True, ex=tolerance * 2
    )
    if not first_use:
        raise HTTPException(status.HTTP_409_CONFLICT, "Replayed request (nonce already used)")
