"""Adaptive alert thresholds computed from historical feature data.

Instead of static thresholds, computes EWMA-based baselines with
confidence intervals per metric, and suggests threshold adjustments.
"""

from __future__ import annotations

import uuid

import numpy as np
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.alerts import AlertRule
from runledger_api.schemas.ml import AdaptiveThresholdList, AdaptiveThresholdSuggestion
from runledger_api.services.ml.features import load_feature_series

log = structlog.get_logger()

_METRIC_TO_DIMENSION = {
    "error_rate": "error_rate",
    "p95_latency": "latency",
    "spend_velocity": "cost",
    "avg_score": "cost",
}


async def suggest_thresholds(
    db: AsyncSession,
    workspace_id: uuid.UUID,
) -> AdaptiveThresholdList:
    """Compute adaptive threshold suggestions for all active alert rules."""
    result = await db.execute(
        select(AlertRule).where(
            AlertRule.workspace_id == workspace_id,
            AlertRule.is_active.is_(True),
        )
    )
    rules = result.scalars().all()

    suggestions = []
    for rule in rules:
        dimension = _METRIC_TO_DIMENSION.get(rule.metric)
        if not dimension:
            continue

        series = await load_feature_series(db, workspace_id, dimension, days=30)
        if len(series) < 7:
            continue

        values = [row["features"].get("value", 0) for row in series]
        arr = np.array(values, dtype=np.float64)

        span = 7
        alpha = 2.0 / (span + 1)
        ewma = np.zeros_like(arr)
        ewma[0] = arr[0]
        for i in range(1, len(arr)):
            ewma[i] = alpha * arr[i] + (1 - alpha) * ewma[i - 1]

        baseline = float(ewma[-1])
        residuals = arr - ewma
        residual_std = float(np.std(residuals, ddof=1))

        sigma = 2.5
        upper = baseline + sigma * residual_std
        lower = max(baseline - sigma * residual_std, 0)

        cv = residual_std / abs(baseline) if abs(baseline) > 1e-10 else 0
        confidence = max(1 - cv, 0.1)

        suggestions.append(AdaptiveThresholdSuggestion(
            rule_id=str(rule.id),
            rule_name=rule.name,
            metric=rule.metric,
            current_threshold=str(rule.threshold),
            suggested_upper=round(upper, 4),
            suggested_lower=round(lower, 4),
            baseline=round(baseline, 4),
            confidence=round(confidence, 3),
        ))

    return AdaptiveThresholdList(items=suggestions)
