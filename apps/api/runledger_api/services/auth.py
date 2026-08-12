from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.config import settings
from runledger_api.models.tenant import ApiKey, EnvironmentEnum

_KEY_BYTES = 32  # 256-bit random token


def _pepper() -> bytes:
    return (settings.api_key_pepper or settings.secret_key).encode()


def _hmac_hash(raw_key: str) -> str:
    return hmac.new(_pepper(), raw_key.encode(), hashlib.sha256).hexdigest()


def _legacy_hash(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def generate_api_key(environment: EnvironmentEnum) -> tuple[str, str, str]:
    """
    Returns (raw_key, key_hash, key_prefix).

    raw_key   — shown to the caller once, never stored
    key_hash  — HMAC-SHA256 hex digest stored in DB for verification
    key_prefix — first 24 chars of raw_key, safe to display anytime
    """
    prefix = "rl_live_" if environment == EnvironmentEnum.prod else "rl_test_"
    token = secrets.token_urlsafe(_KEY_BYTES)
    raw_key = f"{prefix}{token}"
    key_hash = _hmac_hash(raw_key)
    key_prefix = raw_key[:24]
    return raw_key, key_hash, key_prefix


async def verify_api_key(raw_key: str, db: AsyncSession) -> ApiKey | None:
    """
    Returns the ApiKey row if valid and not revoked; None otherwise.
    Tries HMAC hash first, falls back to legacy SHA-256 for migration.
    """
    for hash_fn in (_hmac_hash, _legacy_hash):
        key_hash = hash_fn(raw_key)
        result = await db.execute(
            select(ApiKey).where(
                ApiKey.key_hash == key_hash,
                ApiKey.revoked_at.is_(None),
                or_(ApiKey.expires_at.is_(None), ApiKey.expires_at > datetime.now(UTC)),
            )
        )
        api_key = result.scalar_one_or_none()
        if api_key is not None:
            if hash_fn is _legacy_hash:
                api_key.key_hash = _hmac_hash(raw_key)
                await db.commit()
            return api_key
    return None
