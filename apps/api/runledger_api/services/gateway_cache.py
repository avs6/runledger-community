"""
The workspace's response-cache profile and its counters (review G-09).

A workspace has at most one profile (``response_cache_configs``, unique per workspace).
The gateway enforces every field it can act on:

* ``is_enabled``          — off means no exact-cache lookup or store
* ``scope_models``        — when set, only these aliases / models are cached
* ``ttl_seconds``         — expiry of each stored entry
* ``max_entries``         — after a store, the oldest (``lru``/``fifo``) or least-hit
                            (``lfu``) live entries beyond the limit are removed
* ``similarity_threshold``— passed to the semantic-cache service on lookup
* ``total_hits`` / ``total_misses`` / ``total_savings_usd`` — real counters, updated by
  the gateway on every cacheable request (no profile row yet → one named ``default``
  is created on first use, so counters are never dropped)

``embedding_model`` is informational: the semantic-cache service owns its embedder.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.cache_config import ResponseCacheConfig
from runledger_api.models.gateway import PromptCache
from runledger_api.services.gateway_hotpath import is_missing, ttl_cache

log = structlog.get_logger()

DEFAULT_TTL_SECONDS = 24 * 3600
DEFAULT_MAX_ENTRIES = 10_000


@dataclass(frozen=True)
class CacheProfile:
    """Plain-data view of the workspace's cache profile (safe to cache per process)."""

    id: uuid.UUID | None = None
    is_enabled: bool = True
    ttl_seconds: int = DEFAULT_TTL_SECONDS
    max_entries: int | None = DEFAULT_MAX_ENTRIES
    eviction_policy: str = "lru"
    similarity_threshold: float | None = None
    scope_models: frozenset[str] = field(default_factory=frozenset)

    def allows(self, model: str | None) -> bool:
        if not self.is_enabled:
            return False
        if self.scope_models and model is not None:
            return model in self.scope_models
        return True


def _profile_key(workspace_id: Any) -> tuple[str, str]:
    return ("cache_profile", str(workspace_id))


def invalidate_cache_profile(workspace_id: Any) -> None:
    """Drop this process's copy after the profile is edited."""
    ttl_cache.pop(_profile_key(workspace_id))


async def get_cache_profile(db: AsyncSession, workspace_id: Any) -> CacheProfile:
    cached = ttl_cache.get(_profile_key(workspace_id))
    if not is_missing(cached):
        return cached  # type: ignore[no-any-return]
    row = (
        await db.execute(
            select(ResponseCacheConfig)
            .where(ResponseCacheConfig.workspace_id == workspace_id)
            .order_by(ResponseCacheConfig.created_at.asc())
            .limit(1)
        )
    ).scalar_one_or_none()
    profile = CacheProfile() if row is None else _to_profile(row)
    ttl_cache.put(_profile_key(workspace_id), profile)
    return profile


def _to_profile(row: ResponseCacheConfig) -> CacheProfile:
    scope = row.scope_models if isinstance(row.scope_models, list) else []
    threshold = row.similarity_threshold
    return CacheProfile(
        id=row.id,
        is_enabled=bool(row.is_enabled) if row.is_enabled is not None else True,
        ttl_seconds=int(row.ttl_seconds or DEFAULT_TTL_SECONDS),
        max_entries=int(row.max_entries) if row.max_entries else None,
        eviction_policy=str(row.eviction_policy or "lru").strip("'").lower(),
        similarity_threshold=float(threshold) if threshold is not None else None,
        scope_models=frozenset(str(m) for m in scope if m),
    )


async def record_cache_outcome(
    db: AsyncSession,
    workspace_id: Any,
    *,
    hit: bool,
    savings_usd: Decimal | None = None,
) -> None:
    """Count one cacheable request against the profile (atomic upsert; never raises)."""
    try:
        await db.execute(
            text(
                """
                INSERT INTO response_cache_configs
                    (id, workspace_id, name, total_hits, total_misses, total_savings_usd)
                VALUES (:id, :ws, 'default', :hits, :misses, :savings)
                ON CONFLICT (workspace_id) DO UPDATE SET
                    total_hits = response_cache_configs.total_hits + EXCLUDED.total_hits,
                    total_misses = response_cache_configs.total_misses + EXCLUDED.total_misses,
                    total_savings_usd =
                        response_cache_configs.total_savings_usd + EXCLUDED.total_savings_usd
                """
            ),
            {
                "id": uuid.uuid4(),
                "ws": workspace_id,
                "hits": 1 if hit else 0,
                "misses": 0 if hit else 1,
                "savings": savings_usd or Decimal("0"),
            },
        )
        await db.commit()
    except Exception:  # noqa: BLE001 — counters must never fail a request
        await db.rollback()
        log.warning("gateway_cache_counter_failed", workspace_id=str(workspace_id))


async def enforce_max_entries(db: AsyncSession, workspace_id: Any, profile: CacheProfile) -> int:
    """Remove expired entries and the overflow beyond ``max_entries``; returns rows removed."""
    if not profile.max_entries:
        return 0
    try:
        count = int(
            (
                await db.execute(
                    select(func.count(PromptCache.id)).where(
                        PromptCache.workspace_id == workspace_id
                    )
                )
            ).scalar_one()
            or 0
        )
        overflow = count - profile.max_entries
        if overflow <= 0:
            return 0
        order = (
            [PromptCache.hit_count.asc(), PromptCache.created_at.asc()]
            if profile.eviction_policy == "lfu"
            else [PromptCache.expires_at.asc().nulls_last(), PromptCache.created_at.asc()]
        )
        victims = select(PromptCache.id).where(PromptCache.workspace_id == workspace_id)
        victim_ids = list(
            (await db.execute(victims.order_by(*order).limit(overflow))).scalars().all()
        )
        if victim_ids:
            await db.execute(delete(PromptCache).where(PromptCache.id.in_(victim_ids)))
            await db.commit()
        return len(victim_ids)
    except Exception:  # noqa: BLE001
        await db.rollback()
        log.warning("gateway_cache_eviction_failed", workspace_id=str(workspace_id))
        return 0


async def live_entry_count(db: AsyncSession, workspace_id: Any) -> int:
    """Number of unexpired cache entries (the real value behind the stats card)."""
    from datetime import UTC, datetime  # noqa: PLC0415

    now = datetime.now(UTC)
    return int(
        (
            await db.execute(
                select(func.count(PromptCache.id)).where(
                    PromptCache.workspace_id == workspace_id,
                    (PromptCache.expires_at.is_(None)) | (PromptCache.expires_at > now),
                )
            )
        ).scalar_one()
        or 0
    )
