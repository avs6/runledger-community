from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.tenant import ApiKey, EnvironmentEnum

_KEY_BYTES = 32  # 256-bit random token


def generate_api_key(environment: EnvironmentEnum) -> tuple[str, str, str]:
    """
    Returns (raw_key, key_hash, key_prefix).

    raw_key   — shown to the caller once, never stored
    key_hash  — SHA-256 hex digest stored in DB for verification
    key_prefix — first 24 chars of raw_key, safe to display anytime
    """
    prefix = "rl_live_" if environment == EnvironmentEnum.prod else "rl_test_"
    token = secrets.token_urlsafe(_KEY_BYTES)
    raw_key = f"{prefix}{token}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_prefix = raw_key[:24]
    return raw_key, key_hash, key_prefix


async def verify_api_key(raw_key: str, db: AsyncSession) -> ApiKey | None:
    """
    Returns the ApiKey row if valid and not revoked; None otherwise.
    """
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.key_hash == key_hash,
            ApiKey.revoked_at.is_(None),
            or_(ApiKey.expires_at.is_(None), ApiKey.expires_at > datetime.now(UTC)),
        )
    )
    return result.scalar_one_or_none()
