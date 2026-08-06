"""Request complexity scoring using Gradient Boosting.

Trains a sklearn GradientBoostingRegressor on historical run features
(token counts, tool usage, latency) to predict expected cost. The ratio
of actual to predicted cost serves as a complexity score.
"""

from __future__ import annotations

import pickle
import uuid
from datetime import UTC, datetime, timedelta

import numpy as np
import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.events import ProviderCall, ToolCall
from runledger_api.models.ml import MLModel
from runledger_api.schemas.ml import (
    ComplexityScore,
    ComplexityScoreList,
    FeatureImportance,
    FeatureImportanceList,
)
from runledger_api.services.ml.registry import load_model, save_model

log = structlog.get_logger()

_FEATURE_NAMES = [
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "tool_call_count",
    "latency_ms",
]

_MIN_SAMPLES = 100


async def train_complexity_model(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    lookback_days: int = 30,
) -> MLModel | None:
    """Train a complexity scorer on recent run data."""
    cutoff = datetime.now(UTC) - timedelta(days=lookback_days)

    result = await db.execute(
        select(
            ProviderCall.run_id,
            func.coalesce(func.sum(ProviderCall.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(ProviderCall.output_tokens), 0).label("output_tokens"),
            func.avg(ProviderCall.latency_ms).label("avg_latency"),
            func.coalesce(func.sum(ProviderCall.cost_usd), 0).label("total_cost"),
        )
        .where(
            ProviderCall.workspace_id == workspace_id,
            ProviderCall.created_at >= cutoff,
            ProviderCall.cost_usd.isnot(None),
            ProviderCall.cost_usd > 0,
        )
        .group_by(ProviderCall.run_id)
    )
    rows = result.all()

    if len(rows) < _MIN_SAMPLES:
        log.info("complexity_insufficient_data", workspace_id=str(workspace_id), count=len(rows))
        return None

    tool_counts_result = await db.execute(
        select(ToolCall.run_id, func.count().label("tool_count"))
        .where(
            ToolCall.run_id.in_([r.run_id for r in rows]),
        )
        .group_by(ToolCall.run_id)
    )
    tool_map = {r.run_id: r.tool_count for r in tool_counts_result.all()}

    X = []
    y = []
    run_ids = []
    for row in rows:
        input_t = int(row.input_tokens)
        output_t = int(row.output_tokens)
        total_t = input_t + output_t
        tools = tool_map.get(row.run_id, 0)
        latency = float(row.avg_latency or 0)
        cost = float(row.total_cost)

        X.append([input_t, output_t, total_t, tools, latency])
        y.append(cost)
        run_ids.append(row.run_id)

    X_arr = np.array(X, dtype=np.float64)
    y_arr = np.array(y, dtype=np.float64)

    from sklearn.ensemble import GradientBoostingRegressor

    model = GradientBoostingRegressor(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        random_state=42,
    )
    model.fit(X_arr, y_arr)

    predictions = model.predict(X_arr)
    residuals = y_arr - predictions
    mae = float(np.mean(np.abs(residuals)))
    with np.errstate(divide="ignore", invalid="ignore"):
        mape = float(np.mean(np.where(y_arr != 0, np.abs(residuals / y_arr), 0)))
    r2 = float(model.score(X_arr, y_arr))

    importances = {
        name: round(float(imp), 4)
        for name, imp in zip(_FEATURE_NAMES, model.feature_importances_, strict=False)
    }

    artifact_bytes = pickle.dumps(model)

    return await save_model(
        db,
        workspace_id,
        model_type="complexity_scorer",
        dimension="cost",
        artifact_bytes=artifact_bytes,
        hyperparams={"n_estimators": 100, "max_depth": 4, "learning_rate": 0.1},
        metrics={
            "mae": round(mae, 4),
            "mape": round(mape, 4),
            "r_squared": round(r2, 4),
            "feature_importances": importances,
        },
        sample_count=len(y),
    )


async def get_recent_scores(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    hours: int = 24,
) -> ComplexityScoreList:
    """Score recent runs using the trained complexity model."""
    ml_model = await load_model(db, workspace_id, "complexity_scorer", "cost")
    if not ml_model or not ml_model.artifact:
        return ComplexityScoreList(items=[], distribution={})

    model = pickle.loads(ml_model.artifact)
    cutoff = datetime.now(UTC) - timedelta(hours=hours)

    result = await db.execute(
        select(
            ProviderCall.run_id,
            func.coalesce(func.sum(ProviderCall.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(ProviderCall.output_tokens), 0).label("output_tokens"),
            func.avg(ProviderCall.latency_ms).label("avg_latency"),
            func.coalesce(func.sum(ProviderCall.cost_usd), 0).label("total_cost"),
        )
        .where(
            ProviderCall.workspace_id == workspace_id,
            ProviderCall.created_at >= cutoff,
            ProviderCall.cost_usd.isnot(None),
            ProviderCall.cost_usd > 0,
        )
        .group_by(ProviderCall.run_id)
        .limit(200)
    )
    rows = result.all()

    tool_counts_result = await db.execute(
        select(ToolCall.run_id, func.count().label("tool_count"))
        .where(ToolCall.run_id.in_([r.run_id for r in rows]))
        .group_by(ToolCall.run_id)
    )
    tool_map = {r.run_id: r.tool_count for r in tool_counts_result.all()}

    items = []
    distribution = {"simple": 0, "medium": 0, "complex": 0, "reasoning": 0}
    for row in rows:
        input_t = int(row.input_tokens)
        output_t = int(row.output_tokens)
        total_t = input_t + output_t
        tools = tool_map.get(row.run_id, 0)
        latency = float(row.avg_latency or 0)
        actual = float(row.total_cost)

        features = np.array([[input_t, output_t, total_t, tools, latency]], dtype=np.float64)
        predicted = float(model.predict(features)[0])
        score = actual / predicted if predicted > 0 else 1.0
        score = min(max(score, 0), 5.0)

        if score < 0.5:
            tier = "simple"
        elif score < 1.5:
            tier = "medium"
        elif score < 3.0:
            tier = "complex"
        else:
            tier = "reasoning"

        distribution[tier] += 1
        items.append(
            ComplexityScore(
                run_id=str(row.run_id),
                score=round(score, 3),
                predicted_cost=round(predicted, 6),
                actual_cost=round(actual, 6),
                complexity_tier=tier,
            )
        )

    return ComplexityScoreList(items=items, distribution=distribution)


async def get_feature_importances(
    db: AsyncSession,
    workspace_id: uuid.UUID,
) -> FeatureImportanceList:
    """Return feature importances from the trained model."""
    ml_model = await load_model(db, workspace_id, "complexity_scorer", "cost")
    if not ml_model:
        return FeatureImportanceList(items=[], model_version=0, trained_at=None, sample_count=0)

    importances = ml_model.metrics.get("feature_importances", {})
    items = [
        FeatureImportance(feature=name, importance=imp)
        for name, imp in sorted(importances.items(), key=lambda x: x[1], reverse=True)
    ]
    return FeatureImportanceList(
        items=items,
        model_version=ml_model.version,
        trained_at=ml_model.trained_at,
        sample_count=ml_model.sample_count,
    )
