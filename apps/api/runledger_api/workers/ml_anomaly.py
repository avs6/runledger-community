"""Celery worker: hourly ML anomaly detection + weekly Isolation Forest training.

For each workspace with recent activity, materialises daily features
then runs Z-score + EWMA + Isolation Forest anomaly detection across cost,
latency, error rate, token usage, and cache hit rate dimensions.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from runledger_api.core.celery_app import celery_app
from runledger_api.core.config import settings
from runledger_api.models.events import ProviderCall
from runledger_api.services.ml.anomaly import run_anomaly_detection, train_isolation_forest
from runledger_api.services.ml.features import materialize_daily_features

log = structlog.get_logger()


def _make_session_factory() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _get_active_workspaces(factory: async_sessionmaker[AsyncSession]) -> list[Any]:
    async with factory() as db:
        cutoff = datetime.now(UTC) - timedelta(days=1)
        result = await db.execute(
            select(ProviderCall.workspace_id)
            .where(ProviderCall.created_at >= cutoff)
            .group_by(ProviderCall.workspace_id)
        )
        return [row[0] for row in result.all()]


@celery_app.task(name="ml.anomaly_detection", max_retries=1)  # type: ignore[untyped-decorator]
def ml_anomaly_detection_worker() -> dict[str, int]:
    """Detect anomalies across all active workspaces."""
    return asyncio.run(_run())


async def _run() -> dict[str, int]:
    factory = _make_session_factory()
    yesterday = (datetime.now(UTC) - timedelta(days=1)).date()
    workspaces_checked = 0
    anomalies_found = 0

    workspace_ids = await _get_active_workspaces(factory)

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


@celery_app.task(name="ml.isolation_forest_training", max_retries=1)  # type: ignore[untyped-decorator]
def ml_isolation_forest_training_worker() -> dict[str, int]:
    """Train Isolation Forest models for all active workspaces."""
    return asyncio.run(_run_training())


async def _run_training() -> dict[str, int]:
    factory = _make_session_factory()
    workspace_ids = await _get_active_workspaces(factory)
    trained = 0

    for ws_id in workspace_ids:
        async with factory() as db:
            try:
                result = await train_isolation_forest(db, ws_id)
                if result.get("status") == "trained":
                    trained += 1
                await db.commit()
            except Exception:
                log.exception("isolation_forest_training_error", workspace_id=str(ws_id))
                await db.rollback()

    log.info("isolation_forest_training_complete", workspaces=len(workspace_ids), trained=trained)
    return {"workspaces_checked": len(workspace_ids), "models_trained": trained}
