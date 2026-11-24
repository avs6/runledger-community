"""
Agent memory hygiene (review B-16): encryption at rest for PII, expiry purge.

* Values flagged as PII are stored encrypted (``enc::`` Fernet, the same seam as
  the other build-area secrets until W1-A's ``core/secrets.py`` lands) and
  decrypted on read. Encrypted values are not substring-searchable: memory search
  matches their key only.
* Entries past ``expires_at`` are hidden from reads and deleted by the hourly
  ``build.purge_expired_memories`` task.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.agents import AgentMemory
from runledger_api.services.kafka_export import encrypt_secret_value, resolve_secret_value

ENC_PREFIX = "enc::"


def seal_value(value: str, has_pii: bool) -> str:
    """Value as stored: encrypted when it carries PII."""
    return encrypt_secret_value(value) if has_pii else value


def open_value(stored: str) -> str:
    """Value as returned to an authorised caller."""
    if stored.startswith(ENC_PREFIX):
        try:
            return resolve_secret_value(stored) or ""
        except ValueError:
            return "[encrypted value could not be decrypted]"
    return stored


def not_expired():  # type: ignore[no-untyped-def]
    """SQL filter: entries with no expiry or an expiry in the future."""
    return (AgentMemory.expires_at.is_(None)) | (AgentMemory.expires_at > func.now())


async def purge_expired(db: AsyncSession, now: datetime | None = None) -> int:
    """Delete expired memory entries; returns how many were removed."""
    cutoff = now or datetime.now(UTC)
    count = (
        await db.execute(
            select(func.count(AgentMemory.id)).where(
                AgentMemory.expires_at.isnot(None), AgentMemory.expires_at <= cutoff
            )
        )
    ).scalar() or 0
    if count:
        await db.execute(
            delete(AgentMemory).where(
                AgentMemory.expires_at.isnot(None), AgentMemory.expires_at <= cutoff
            )
        )
        await db.commit()
    return int(count)
