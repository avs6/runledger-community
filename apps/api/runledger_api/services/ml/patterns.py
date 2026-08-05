"""Usage pattern classification — rule-based with numpy/scipy.

Classifies time-series into one of six patterns:
steady, growing, declining, spiky, seasonal, one_shot.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import numpy as np
import structlog
from scipy import stats as sp_stats
from sqlalchemy import and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.ml import MLPattern
from runledger_api.services.ml.features import load_feature_series

log = structlog.get_logger()

_DIMENSIONS = ["cost", "latency", "tokens"]


def classify_pattern(
    values: list[float],
    dates: list[date],
) -> tuple[str, float, dict]:
    """Classify a time-series into a pattern type.

    Returns (pattern, confidence, evidence).
    """
    arr = np.array(values, dtype=np.float64)
    n = len(arr)

    if n < 7:
        return "steady", 0.5, {"reason": "insufficient_data"}

    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1))
    cv = std / abs(mean) if abs(mean) > 1e-10 else 0.0

    x = np.arange(n, dtype=np.float64)
    slope, intercept, r_value, p_value, std_err = sp_stats.linregress(x, arr)
    r_squared = r_value ** 2

    total = float(np.sum(arr))
    if total > 0:
        sorted_vals = np.sort(arr)[::-1]
        top_10_pct = int(max(1, n * 0.1))
        top_share = float(np.sum(sorted_vals[:top_10_pct])) / total
    else:
        top_share = 0.0

    autocorr_7 = _autocorrelation(arr, lag=7) if n >= 14 else 0.0

    evidence = {
        "mean": round(mean, 4),
        "std": round(std, 4),
        "cv": round(cv, 4),
        "slope": round(slope, 6),
        "slope_p_value": round(p_value, 4),
        "r_squared": round(r_squared, 4),
        "autocorr_lag7": round(autocorr_7, 4),
        "top_10pct_share": round(top_share, 4),
        "n": n,
    }

    if top_share > 0.8:
        return "one_shot", round(min(top_share, 0.999), 3), evidence

    if abs(autocorr_7) > 0.5 and n >= 14:
        return "seasonal", round(min(abs(autocorr_7), 0.999), 3), evidence

    if cv > 0.5:
        return "spiky", round(min(cv / 2, 0.999), 3), evidence

    if p_value < 0.05 and slope > 0:
        confidence = min(r_squared * 1.2, 0.999)
        return "growing", round(confidence, 3), evidence

    if p_value < 0.05 and slope < 0:
        confidence = min(r_squared * 1.2, 0.999)
        return "declining", round(confidence, 3), evidence

    return "steady", round(min(1 - cv, 0.999), 3), evidence


def _autocorrelation(arr: np.ndarray, lag: int) -> float:
    n = len(arr)
    if n <= lag:
        return 0.0
    mean = np.mean(arr)
    c0 = np.sum((arr - mean) ** 2)
    if c0 < 1e-10:
        return 0.0
    ck = np.sum((arr[lag:] - mean) * (arr[:-lag] - mean))
    return float(ck / c0)


async def detect_patterns(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    dimensions: list[str] | None = None,
) -> list[MLPattern]:
    """Detect and store usage patterns for each dimension."""
    dims = dimensions or _DIMENSIONS
    patterns: list[MLPattern] = []

    for dimension in dims:
        series = await load_feature_series(db, workspace_id, dimension, days=30)
        if len(series) < 7:
            continue

        values = [row["features"].get("value", 0) for row in series]
        dates = [row["date"] for row in series]

        pattern_type, confidence, evidence = classify_pattern(values, dates)

        await db.execute(
            delete(MLPattern).where(
                MLPattern.workspace_id == workspace_id,
                MLPattern.dimension == dimension,
                MLPattern.dimension_key.is_(None),
            )
        )

        record = MLPattern(
            workspace_id=workspace_id,
            dimension=dimension,
            pattern=pattern_type,
            confidence=Decimal(str(confidence)),
            evidence=evidence,
        )
        db.add(record)
        patterns.append(record)

    if patterns:
        await db.flush()
    return patterns
