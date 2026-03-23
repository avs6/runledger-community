"""
Nightly data retention worker.

Iterates all active RetentionPolicy rows across all workspaces and applies
each one.  One bad policy never aborts the rest — errors are logged and
the loop continues.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from runledger_api.core.celery_app import celery_app
from runledger_api.core.config import settings

log = structlog.get_logger()


@celery_app.task(name="retention.apply_policies")  # type: ignore[untyped-decorator]
def apply_retention_policies() -> None:
    """Apply all active retention policies across all workspaces."""
    asyncio.run(_apply())


async def _apply() -> None:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with session_factory() as session:
            total = await _run_active_policies(session)
            await session.commit()
            log.info("retention_worker_complete", total_purged=total)
    finally:
        await engine.dispose()


async def _run_active_policies(session: AsyncSession) -> int:
    from runledger_api.models.retention import RetentionPolicy
    from runledger_api.services.retention import purge_resource

    result = await session.execute(
        select(RetentionPolicy).where(RetentionPolicy.is_active.is_(True))
    )
    policies = list(result.scalars().all())

    total = 0
    for policy in policies:
        try:
            count, _ = await purge_resource(
                session,
                workspace_id=policy.workspace_id,
                resource_type=policy.resource_type,
                action=policy.action,
                scope=policy.scope,
                scope_value=policy.scope_value,
                max_age_days=policy.max_age_days,
                dry_run=False,
            )
            policy.last_run_at = datetime.now(UTC)
            policy.last_purged_count = count
            total += count
            log.info(
                "retention_policy_applied",
                policy_id=str(policy.id),
                workspace_id=str(policy.workspace_id),
                resource_type=policy.resource_type,
                count=count,
            )
        except Exception:
            log.exception("retention_policy_failed", policy_id=str(policy.id))

    return total
