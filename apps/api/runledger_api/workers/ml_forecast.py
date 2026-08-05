"""Celery worker: daily forecast retraining and pattern detection.

For each workspace with sufficient feature data, retrains cost and token
forecasts and runs pattern classification.
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
from runledger_api.models.ml import MLFeatureDaily

log = structlog.get_logger()


def _make_session_factory() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@celery_app.task(name="ml.forecast_retraining", max_retries=1)
def ml_forecast_retraining_worker() -> dict[str, int]:
    """Retrain forecasts and detect patterns for all workspaces."""
    return asyncio.run(_run())


async def _run() -> dict[str, int]:
    factory = _make_session_factory()
    forecasts_created = 0
    patterns_detected = 0

    async with factory() as db:
        cutoff = date.today() - timedelta(days=7)
        result = await db.execute(
            select(MLFeatureDaily.workspace_id)
            .where(MLFeatureDaily.feature_date >= cutoff)
            .group_by(MLFeatureDaily.workspace_id)
        )
        workspace_ids = [row[0] for row in result.all()]

    for ws_id in workspace_ids:
        async with factory() as db:
            try:
                from runledger_api.services.ml.forecast import run_forecast
                for ftype in ("cost_daily", "tokens_daily"):
                    forecast = await run_forecast(db, ws_id, ftype, horizon_days=14)
                    if forecast:
                        forecasts_created += 1

                from runledger_api.services.ml.patterns import detect_patterns
                patterns = await detect_patterns(db, ws_id)
                patterns_detected += len(patterns)

                await db.commit()
            except Exception:
                log.exception("ml_forecast_error", workspace_id=str(ws_id))
                await db.rollback()

    log.info("ml_forecast_complete", forecasts=forecasts_created, patterns=patterns_detected)
    return {"forecasts_created": forecasts_created, "patterns_detected": patterns_detected}
