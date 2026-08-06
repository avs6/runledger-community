"""Daily feature materialization for the ML intelligence layer.

Queries provider_calls and agent_runs to compute daily aggregate features
per workspace per dimension, stored in ml_features_daily for use by
anomaly detection, forecasting, and pattern recognition.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Any

import structlog
from sqlalchemy import Date, and_, cast, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.events import ProviderCall
from runledger_api.models.ml import MLFeatureDaily

log = structlog.get_logger()


async def materialize_daily_features(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    target_date: date,
) -> int:
    """Compute and upsert daily feature rows for a workspace.

    Returns the number of feature rows upserted.
    """
    rows_upserted = 0

    rows_upserted += await _materialize_cost_features(db, workspace_id, target_date)
    rows_upserted += await _materialize_latency_features(db, workspace_id, target_date)
    rows_upserted += await _materialize_error_features(db, workspace_id, target_date)
    rows_upserted += await _materialize_token_features(db, workspace_id, target_date)
    rows_upserted += await _materialize_cache_features(db, workspace_id, target_date)
    rows_upserted += await _materialize_per_model_features(db, workspace_id, target_date)

    return rows_upserted


async def _upsert_feature(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    feature_date: date,
    dimension: str,
    dimension_key: str | None,
    features: dict[str, Any],
) -> int:
    stmt = pg_insert(MLFeatureDaily).values(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        feature_date=feature_date,
        dimension=dimension,
        dimension_key=dimension_key,
        features=features,
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_ml_features_daily",
        set_={"features": features},
    )
    await db.execute(stmt)
    return 1


def _day_filter(col: Any, target_date: date) -> Any:
    return cast(col, Date) == target_date


async def _materialize_cost_features(
    db: AsyncSession, workspace_id: uuid.UUID, target_date: date
) -> int:
    result = await db.execute(
        select(
            func.coalesce(func.sum(ProviderCall.cost_usd), 0).label("total_cost"),
            func.count().label("call_count"),
        ).where(
            ProviderCall.workspace_id == workspace_id,
            _day_filter(ProviderCall.created_at, target_date),
        )
    )
    row = result.one()
    return await _upsert_feature(
        db,
        workspace_id,
        target_date,
        "cost",
        None,
        {
            "value": float(row.total_cost),
            "call_count": row.call_count,
        },
    )


async def _materialize_latency_features(
    db: AsyncSession, workspace_id: uuid.UUID, target_date: date
) -> int:
    result = await db.execute(
        select(
            func.avg(ProviderCall.latency_ms).label("avg_latency"),
            func.percentile_cont(0.95).within_group(ProviderCall.latency_ms).label("p95_latency"),
            func.percentile_cont(0.99).within_group(ProviderCall.latency_ms).label("p99_latency"),
            func.count().label("call_count"),
        ).where(
            ProviderCall.workspace_id == workspace_id,
            ProviderCall.latency_ms.isnot(None),
            _day_filter(ProviderCall.created_at, target_date),
        )
    )
    row = result.one()
    if row.call_count == 0:
        return 0
    return await _upsert_feature(
        db,
        workspace_id,
        target_date,
        "latency",
        None,
        {
            "value": float(row.avg_latency or 0),
            "p95": float(row.p95_latency or 0),
            "p99": float(row.p99_latency or 0),
            "call_count": row.call_count,
        },
    )


async def _materialize_error_features(
    db: AsyncSession, workspace_id: uuid.UUID, target_date: date
) -> int:
    result = await db.execute(
        select(
            func.count().label("total"),
            func.count().filter(ProviderCall.status != "succeeded").label("errors"),
        ).where(
            ProviderCall.workspace_id == workspace_id,
            _day_filter(ProviderCall.created_at, target_date),
        )
    )
    row = result.one()
    if row.total == 0:
        return 0
    error_rate = row.errors / row.total if row.total > 0 else 0
    return await _upsert_feature(
        db,
        workspace_id,
        target_date,
        "error_rate",
        None,
        {
            "value": error_rate,
            "total_calls": row.total,
            "error_count": row.errors,
        },
    )


async def _materialize_token_features(
    db: AsyncSession, workspace_id: uuid.UUID, target_date: date
) -> int:
    result = await db.execute(
        select(
            func.coalesce(func.sum(ProviderCall.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(ProviderCall.output_tokens), 0).label("output_tokens"),
            func.count().label("call_count"),
        ).where(
            ProviderCall.workspace_id == workspace_id,
            _day_filter(ProviderCall.created_at, target_date),
        )
    )
    row = result.one()
    total = row.input_tokens + row.output_tokens
    return await _upsert_feature(
        db,
        workspace_id,
        target_date,
        "tokens",
        None,
        {
            "value": total,
            "input_tokens": row.input_tokens,
            "output_tokens": row.output_tokens,
            "call_count": row.call_count,
        },
    )


async def _materialize_cache_features(
    db: AsyncSession, workspace_id: uuid.UUID, target_date: date
) -> int:
    result = await db.execute(
        select(
            func.count().label("total"),
            func.count().filter(ProviderCall.cached_input_tokens > 0).label("cache_hits"),
        ).where(
            ProviderCall.workspace_id == workspace_id,
            _day_filter(ProviderCall.created_at, target_date),
        )
    )
    row = result.one()
    if row.total == 0:
        return 0
    hit_rate = row.cache_hits / row.total if row.total > 0 else 0
    return await _upsert_feature(
        db,
        workspace_id,
        target_date,
        "cache_hit_rate",
        None,
        {
            "value": hit_rate,
            "total_calls": row.total,
            "cache_hits": row.cache_hits,
        },
    )


async def _materialize_per_model_features(
    db: AsyncSession, workspace_id: uuid.UUID, target_date: date
) -> int:
    result = await db.execute(
        select(
            ProviderCall.model,
            func.coalesce(func.sum(ProviderCall.cost_usd), 0).label("cost"),
            func.avg(ProviderCall.latency_ms).label("avg_latency"),
            func.count().label("call_count"),
            func.count().filter(ProviderCall.status != "succeeded").label("errors"),
        )
        .where(
            ProviderCall.workspace_id == workspace_id,
            _day_filter(ProviderCall.created_at, target_date),
        )
        .group_by(ProviderCall.model)
    )
    count = 0
    for row in result.all():
        error_rate = row.errors / row.call_count if row.call_count > 0 else 0
        count += await _upsert_feature(
            db,
            workspace_id,
            target_date,
            "cost_by_model",
            row.model,
            {
                "value": float(row.cost),
                "avg_latency": float(row.avg_latency or 0),
                "call_count": row.call_count,
                "error_rate": error_rate,
            },
        )
    return count


async def load_feature_series(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    dimension: str,
    dimension_key: str | None = None,
    days: int = 30,
) -> list[dict[str, Any]]:
    """Load the last N days of feature values for a dimension, oldest first."""
    cutoff = date.today() - timedelta(days=days)
    where_clauses = [
        MLFeatureDaily.workspace_id == workspace_id,
        MLFeatureDaily.dimension == dimension,
        MLFeatureDaily.feature_date >= cutoff,
    ]
    if dimension_key is not None:
        where_clauses.append(MLFeatureDaily.dimension_key == dimension_key)
    else:
        where_clauses.append(MLFeatureDaily.dimension_key.is_(None))

    result = await db.execute(
        select(MLFeatureDaily.feature_date, MLFeatureDaily.features)
        .where(and_(*where_clauses))
        .order_by(MLFeatureDaily.feature_date)
    )
    return [{"date": row.feature_date, "features": row.features} for row in result.all()]
