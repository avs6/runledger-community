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


# ── Dashboard session cleanup ────────────────────────────────────────────────

# Revoked/expired session keys are kept this long for audit/investigation, then purged.
_SESSION_KEY_GRACE_DAYS = 7


@celery_app.task(name="auth.purge_session_keys")  # type: ignore[untyped-decorator]
def purge_session_keys() -> int:
    """Delete dashboard session keys that expired or were revoked over a week ago."""
    return asyncio.run(_purge_session_keys())


async def _purge_session_keys() -> int:
    from datetime import timedelta  # noqa: PLC0415

    from sqlalchemy import delete, or_  # noqa: PLC0415

    from runledger_api.models.tenant import ApiKey  # noqa: PLC0415

    cutoff = datetime.now(UTC) - timedelta(days=_SESSION_KEY_GRACE_DAYS)
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with session_factory() as session:
            result = await session.execute(
                delete(ApiKey).where(
                    ApiKey.is_session.is_(True),
                    or_(ApiKey.revoked_at < cutoff, ApiKey.expires_at < cutoff),
                )
            )
            await session.commit()
            purged = int(result.rowcount or 0)
            log.info("session_keys_purged", count=purged)
            return purged
    finally:
        await engine.dispose()
