"""ML observability — model health dashboard and summaries."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.ml import MLAnomaly, MLForecast, MLModel, MLPattern
from runledger_api.schemas.ml import AnomalySummary, MLDashboard, ModelHealth

log = structlog.get_logger()


async def get_model_health_list(
    db: AsyncSession,
    workspace_id: uuid.UUID,
) -> list[ModelHealth]:
    result = await db.execute(
        select(MLModel).where(
            MLModel.workspace_id == workspace_id,
            MLModel.is_active.is_(True),
        ).order_by(MLModel.model_type, MLModel.dimension)
    )
    models = result.scalars().all()
    now = datetime.now(UTC)

    items = []
    for m in models:
        staleness_hours = 0.0
        if m.trained_at:
            staleness_hours = (now - m.trained_at).total_seconds() / 3600

        if staleness_hours > 168:
            status = "stale"
        elif m.metrics.get("mape", 0) > 0.5:
            status = "degraded"
        else:
            status = "healthy"

        items.append(ModelHealth(
            id=str(m.id),
            model_type=m.model_type,
            dimension=m.dimension,
            dimension_key=m.dimension_key,
            version=m.version,
            trained_at=m.trained_at,
            sample_count=m.sample_count,
            staleness_hours=round(staleness_hours, 1),
            metrics=m.metrics,
            status=status,
        ))
    return items


async def get_dashboard(
    db: AsyncSession,
    workspace_id: uuid.UUID,
) -> MLDashboard:
    models = await get_model_health_list(db, workspace_id)

    cutoff_24h = datetime.now(UTC) - timedelta(hours=24)
    base = [MLAnomaly.workspace_id == workspace_id, MLAnomaly.detected_at >= cutoff_24h]

    total = await db.scalar(select(func.count()).where(and_(*base))) or 0

    sev_result = await db.execute(
        select(MLAnomaly.severity, func.count()).where(and_(*base)).group_by(MLAnomaly.severity)
    )
    by_severity = {row[0]: row[1] for row in sev_result.all()}

    type_result = await db.execute(
        select(MLAnomaly.anomaly_type, func.count()).where(and_(*base)).group_by(MLAnomaly.anomaly_type)
    )
    by_type = {row[0]: row[1] for row in type_result.all()}

    suppressed = await db.scalar(
        select(func.count()).where(and_(*base, MLAnomaly.is_suppressed.is_(True)))
    ) or 0
    acknowledged = await db.scalar(
        select(func.count()).where(and_(*base, MLAnomaly.acknowledged_at.isnot(None)))
    ) or 0

    total_forecasts = await db.scalar(
        select(func.count()).where(MLForecast.workspace_id == workspace_id)
    ) or 0

    total_patterns = await db.scalar(
        select(func.count()).where(MLPattern.workspace_id == workspace_id)
    ) or 0

    last_anomaly = await db.scalar(
        select(func.max(MLAnomaly.detected_at)).where(MLAnomaly.workspace_id == workspace_id)
    )
    last_forecast = await db.scalar(
        select(func.max(MLForecast.created_at)).where(MLForecast.workspace_id == workspace_id)
    )

    return MLDashboard(
        models=models,
        anomaly_summary=AnomalySummary(
            total=total,
            by_severity=by_severity,
            by_type=by_type,
            suppressed=suppressed,
            acknowledged=acknowledged,
        ),
        total_forecasts=total_forecasts,
        total_patterns=total_patterns,
        last_anomaly_run=last_anomaly,
        last_forecast_run=last_forecast,
    )
