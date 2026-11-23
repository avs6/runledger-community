"""Celery tasks for the Build area: agent memory expiry purge (review B-16)."""

from __future__ import annotations

import asyncio

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from runledger_api.core.celery_app import celery_app
from runledger_api.core.config import settings

log = structlog.get_logger()


async def _purge() -> int:
    from runledger_api.services.agent_memory import purge_expired  # noqa: PLC0415

    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with factory() as db:
            return await purge_expired(db)
    finally:
        await engine.dispose()


@celery_app.task(name="build.purge_expired_memories")  # type: ignore[untyped-decorator]
def purge_expired_memories() -> int:
    """Delete agent memory entries whose ``expires_at`` has passed."""
    removed = asyncio.run(_purge())
    log.info("agent_memory.purged", removed=removed)
    return removed
