"""
Celery worker that expires budget overrides past their expires_at.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from runledger_api.core.celery_app import celery_app
from runledger_api.core.config import settings
from runledger_api.models.budget_overrides import BudgetOverride

log = structlog.get_logger()


def _make_session_factory() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@celery_app.task(name="budgets.expire_overrides")  # type: ignore[untyped-decorator]
def expire_budget_overrides_worker() -> dict[str, int]:
    return asyncio.run(_expire_overrides())


async def _expire_overrides() -> dict[str, int]:
    factory = _make_session_factory()
    now = datetime.now(UTC)

    async with factory() as session:
        result = await session.execute(
            select(BudgetOverride.id).where(
                BudgetOverride.status == "active",
                BudgetOverride.expires_at <= now,
            )
        )
        expired_ids = list(result.scalars().all())

        if expired_ids:
            await session.execute(
                update(BudgetOverride)
                .where(BudgetOverride.id.in_(expired_ids))
                .values(status="expired")
            )
            await session.commit()
            log.info("budget_overrides_expired", count=len(expired_ids))

    return {"expired": len(expired_ids)}
