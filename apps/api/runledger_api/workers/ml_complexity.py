"""Celery worker: weekly complexity scorer retraining.

For each workspace with sufficient data (>100 runs), retrains
the GradientBoosting complexity model.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from runledger_api.core.celery_app import celery_app
from runledger_api.core.config import settings
from runledger_api.models.events import ProviderCall

log = structlog.get_logger()


def _make_session_factory() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@celery_app.task(name="ml.complexity_retraining", max_retries=1)
def ml_complexity_retraining_worker() -> dict[str, int]:
    """Retrain complexity scorer for all eligible workspaces."""
    return asyncio.run(_run())


async def _run() -> dict[str, int]:
    factory = _make_session_factory()
    models_trained = 0

    async with factory() as db:
        cutoff = datetime.now(UTC) - timedelta(days=30)
        result = await db.execute(
            select(ProviderCall.workspace_id, func.count().label("cnt"))
            .where(ProviderCall.created_at >= cutoff, ProviderCall.cost_usd.isnot(None))
            .group_by(ProviderCall.workspace_id)
            .having(func.count() >= 100)
        )
        eligible = [row[0] for row in result.all()]

    for ws_id in eligible:
        async with factory() as db:
            try:
                from runledger_api.services.ml.complexity import train_complexity_model
                model = await train_complexity_model(db, ws_id)
                if model:
                    models_trained += 1
                await db.commit()
            except Exception:
                log.exception("ml_complexity_error", workspace_id=str(ws_id))
                await db.rollback()

    log.info("ml_complexity_complete", models_trained=models_trained)
    return {"models_trained": models_trained}
