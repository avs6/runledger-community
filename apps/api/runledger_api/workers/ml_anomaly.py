"""Celery worker: hourly ML anomaly detection.

For each workspace with recent activity, materialises daily features
then runs Z-score + EWMA anomaly detection across cost, latency,
error rate, token usage, and cache hit rate dimensions.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from runledger_api.core.celery_app import celery_app
from runledger_api.core.config import settings
from runledger_api.models.events import ProviderCall
from runledger_api.services.ml.anomaly import run_anomaly_detection
from runledger_api.services.ml.features import materialize_daily_features

log = structlog.get_logger()


def _make_session_factory() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@celery_app.task(name="ml.anomaly_detection", max_retries=1)
def ml_anomaly_detection_worker() -> dict[str, int]:
    """Detect anomalies across all active workspaces."""
    return asyncio.run(_run())


async def _run() -> dict[str, int]:
    factory = _make_session_factory()
    yesterday = (datetime.now(UTC) - timedelta(days=1)).date()
    workspaces_checked = 0
    anomalies_found = 0

    async with factory() as db:
        cutoff = datetime.now(UTC) - timedelta(days=1)
        result = await db.execute(
            select(ProviderCall.workspace_id)
            .where(ProviderCall.created_at >= cutoff)
            .group_by(ProviderCall.workspace_id)
        )
        workspace_ids = [row[0] for row in result.all()]

    for ws_id in workspace_ids:
        async with factory() as db:
            try:
                await materialize_daily_features(db, ws_id, yesterday)
                anomalies = await run_anomaly_detection(db, ws_id, yesterday)
                anomalies_found += len(anomalies)
                await db.commit()
            except Exception:
                log.exception("ml_anomaly_error", workspace_id=str(ws_id))
                await db.rollback()
        workspaces_checked += 1

    log.info("ml_anomaly_complete", workspaces=workspaces_checked, anomalies=anomalies_found)
    return {"workspaces_checked": workspaces_checked, "anomalies_found": anomalies_found}
