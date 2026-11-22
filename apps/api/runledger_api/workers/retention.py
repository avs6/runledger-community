"""
Nightly data retention worker.

Iterates all active RetentionPolicy rows across all workspaces and applies
each one.  One bad policy never aborts the rest — errors are logged and
the loop continues.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

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
        # Each policy in its own savepoint and commit (review S-20): one failing
        # workspace's policy no longer rolls back everyone else's purges.
        policy_id = policy.id
        try:
            async with session.begin_nested():
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
            await session.commit()
            total += count
            log.info(
                "retention_policy_applied",
                policy_id=str(policy.id),
                workspace_id=str(policy.workspace_id),
                resource_type=policy.resource_type,
                count=count,
            )
        except Exception:
            await session.rollback()
            log.exception("retention_policy_failed", policy_id=str(policy_id))

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


# ── Raw ingest telemetry cleanup (review I-12 / I-26) ─────────────────────────

_PURGE_CHUNK = 5000


@celery_app.task(name="ingest.purge_raw_telemetry")  # type: ignore[untyped-decorator]
def purge_raw_telemetry() -> dict[str, int]:
    """Delete raw OTLP batches/spans, finished Kafka deliveries and resolved dead
    letters older than OTLP_RAW_RETENTION_DAYS, and OTLP metric rollups older than
    OTLP_METRIC_RETENTION_DAYS (0 disables either)."""
    return asyncio.run(_purge_raw_telemetry())


async def _purge_chunked(session: AsyncSession, model: Any, *where: Any) -> int:
    from sqlalchemy import delete  # noqa: PLC0415

    total = 0
    while True:
        ids = list(
            (await session.execute(select(model.id).where(*where).limit(_PURGE_CHUNK))).scalars()
        )
        if not ids:
            return total
        await session.execute(delete(model).where(model.id.in_(ids)))
        await session.commit()
        total += len(ids)


async def _purge_raw_telemetry() -> dict[str, int]:
    from datetime import timedelta  # noqa: PLC0415

    from runledger_api.models.ingest_dead_letters import IngestDeadLetter  # noqa: PLC0415
    from runledger_api.models.kafka import KafkaExportDelivery  # noqa: PLC0415
    from runledger_api.models.otlp import OtlpIngestBatch, OtlpMetricRollup  # noqa: PLC0415

    days = settings.otlp_raw_retention_days
    metric_days = settings.otlp_metric_retention_days
    if days <= 0 and metric_days <= 0:
        return {}
    cutoff = datetime.now(UTC) - timedelta(days=days)
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with session_factory() as session:
            counts: dict[str, int] = {}
            if metric_days > 0:
                metric_cutoff = (datetime.now(UTC) - timedelta(days=metric_days)).date()
                counts["metric_rollups"] = await _purge_chunked(
                    session, OtlpMetricRollup, OtlpMetricRollup.day < metric_cutoff
                )
            if days <= 0:
                log.info("raw_telemetry_purged", metric_retention_days=metric_days, **counts)
                return counts
            counts |= {
                # otlp_spans_raw rows cascade with their batch.
                "otlp_batches": await _purge_chunked(
                    session, OtlpIngestBatch, OtlpIngestBatch.received_at < cutoff
                ),
                "kafka_deliveries": await _purge_chunked(
                    session,
                    KafkaExportDelivery,
                    KafkaExportDelivery.created_at < cutoff,
                    KafkaExportDelivery.status.in_(["success", "failed"]),
                ),
                "dead_letters": await _purge_chunked(
                    session,
                    IngestDeadLetter,
                    IngestDeadLetter.created_at < cutoff,
                    IngestDeadLetter.status.in_(["replayed", "discarded"]),
                ),
            }
            log.info(
                "raw_telemetry_purged",
                retention_days=days,
                metric_retention_days=metric_days,
                **counts,
            )
            return counts
    finally:
        await engine.dispose()
