"""
Celery worker that moves budget overrides through their lifecycle (review F-13).

- ``scheduled`` overrides whose ``starts_at`` has passed become ``active``.
- ``active`` overrides past ``expires_at`` become ``expired``.

Either change invalidates the affected workspaces' budget cache, so the gateway
picks up the new limit on its next request instead of up to five minutes later.
Overrides waiting for approval stay ``pending``; approving one makes it ``active``
(routers/approvals.py) and the cache then applies it once ``starts_at`` is reached.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import cast

import structlog
from redis.asyncio import Redis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from runledger_api.core.celery_app import celery_app
from runledger_api.core.config import settings
from runledger_api.models.budget_overrides import BudgetOverride
from runledger_api.models.budgets import Budget
from runledger_api.services.budgets import invalidate_workspace_budgets_cache

log = structlog.get_logger()


def _make_session_factory() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@celery_app.task(name="budgets.expire_overrides")  # type: ignore[untyped-decorator]
def expire_budget_overrides_worker() -> dict[str, int]:
    return asyncio.run(_run_override_lifecycle())


async def advance_overrides(
    session: AsyncSession, now: datetime
) -> tuple[int, int, set[uuid.UUID]]:
    """Activate due scheduled overrides and expire finished ones.

    Returns ``(activated, expired, workspace_ids)``; the caller commits.
    """
    activated = list(
        (
            await session.execute(
                update(BudgetOverride)
                .where(
                    BudgetOverride.status == "scheduled",
                    BudgetOverride.starts_at <= now,
                    BudgetOverride.expires_at > now,
                )
                .values(status="active")
                .returning(BudgetOverride.budget_id)
            )
        ).scalars()
    )
    expired = list(
        (
            await session.execute(
                update(BudgetOverride)
                .where(
                    BudgetOverride.status.in_(("active", "scheduled")),
                    BudgetOverride.expires_at <= now,
                )
                .values(status="expired")
                .returning(BudgetOverride.budget_id)
            )
        ).scalars()
    )
    budget_ids = set(activated) | set(expired)
    workspace_ids: set[uuid.UUID] = set()
    if budget_ids:
        workspace_ids = set(
            (
                await session.execute(select(Budget.workspace_id).where(Budget.id.in_(budget_ids)))
            ).scalars()
        )
    return len(activated), len(expired), workspace_ids


async def _run_override_lifecycle() -> dict[str, int]:
    factory = _make_session_factory()
    redis = cast(Redis, Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True))
    try:
        async with factory() as session:
            activated, expired, workspace_ids = await advance_overrides(session, datetime.now(UTC))
            await session.commit()
        for workspace_id in workspace_ids:
            await invalidate_workspace_budgets_cache(redis, workspace_id)
    finally:
        await redis.aclose()
    if activated or expired:
        log.info("budget_overrides_advanced", activated=activated, expired=expired)
    return {"activated": activated, "expired": expired}
