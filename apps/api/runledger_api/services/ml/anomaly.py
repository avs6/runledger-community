"""Anomaly detection using Z-score and EWMA methods.

Both detectors operate on a time-series of scalar values (e.g. daily cost)
and return anomaly results for the most recent observation.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import numpy as np
import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.ml import MLAnomaly
from runledger_api.services.ml.features import load_feature_series, materialize_daily_features

log = structlog.get_logger()

_DIMENSIONS = ["cost", "latency", "error_rate", "tokens", "cache_hit_rate"]
_FLOOD_LIMIT = 5
_FLOOD_WINDOW_HOURS = 24


@dataclass
class AnomalyResult:
    anomaly_type: str
    dimension: str
    dimension_key: str | None
    current_value: float
    expected_value: float
    deviation_score: float
    severity: str
    detection_method: str
    context: dict


def classify_severity(deviation_score: float) -> str:
    score = abs(deviation_score)
    if score >= 5.0:
        return "critical"
    if score >= 4.0:
        return "high"
    if score >= 3.0:
        return "medium"
    return "low"


def detect_zscore(
    values: list[float],
    threshold: float = 3.0,
) -> AnomalyResult | None:
    """Z-score anomaly detection on the last value in the series."""
    if len(values) < 7:
        return None

    arr = np.array(values[:-1], dtype=np.float64)
    current = values[-1]
    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1))
    if std < 1e-10:
        return None

    z = (current - mean) / std
    if abs(z) < threshold:
        return None

    return AnomalyResult(
        anomaly_type="",
        dimension="",
        dimension_key=None,
        current_value=current,
        expected_value=mean,
        deviation_score=z,
        severity=classify_severity(z),
        detection_method="zscore",
        context={"mean": mean, "std": std, "z_score": z, "window_size": len(arr)},
    )


def detect_ewma(
    values: list[float],
    span: int = 7,
    threshold_sigma: float = 2.5,
) -> AnomalyResult | None:
    """EWMA-based anomaly detection — more responsive to recent shifts."""
    if len(values) < 7:
        return None

    arr = np.array(values, dtype=np.float64)
    alpha = 2.0 / (span + 1)

    ewma = np.zeros_like(arr)
    ewma[0] = arr[0]
    for i in range(1, len(arr)):
        ewma[i] = alpha * arr[i] + (1 - alpha) * ewma[i - 1]

    residuals = arr[:-1] - ewma[:-1]
    ewma_std = float(np.std(residuals, ddof=1))
    if ewma_std < 1e-10:
        return None

    current = values[-1]
    expected = float(ewma[-2])
    deviation = (current - expected) / ewma_std

    if abs(deviation) < threshold_sigma:
        return None

    return AnomalyResult(
        anomaly_type="",
        dimension="",
        dimension_key=None,
        current_value=current,
        expected_value=expected,
        deviation_score=deviation,
        severity=classify_severity(deviation),
        detection_method="ewma",
        context={
            "ewma_expected": expected,
            "ewma_std": ewma_std,
            "deviation": deviation,
            "span": span,
        },
    )


def _anomaly_type_for_dimension(dimension: str) -> str:
    mapping = {
        "cost": "cost_spike",
        "latency": "latency_regression",
        "error_rate": "error_rate_spike",
        "tokens": "token_spike",
        "cache_hit_rate": "cache_hit_drop",
    }
    return mapping.get(dimension, f"{dimension}_anomaly")


async def _is_flood_suppressed(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    dimension: str,
) -> bool:
    cutoff = datetime.now(UTC) - timedelta(hours=_FLOOD_WINDOW_HOURS)
    count = await db.scalar(
        select(func.count()).where(
            MLAnomaly.workspace_id == workspace_id,
            MLAnomaly.dimension == dimension,
            MLAnomaly.detected_at >= cutoff,
            MLAnomaly.is_suppressed.is_(False),
        )
    )
    return (count or 0) >= _FLOOD_LIMIT


async def run_anomaly_detection(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    target_date: date,
    dimensions: list[str] | None = None,
) -> list[MLAnomaly]:
    """Run anomaly detection across all dimensions for a workspace.

    Returns the list of newly created anomaly records.
    """
    dims = dimensions or _DIMENSIONS
    anomalies: list[MLAnomaly] = []

    for dimension in dims:
        series = await load_feature_series(db, workspace_id, dimension, days=30)
        if len(series) < 7:
            continue

        values = [row["features"].get("value", 0) for row in series]

        zscore_result = detect_zscore(values)
        ewma_result = detect_ewma(values)

        result: AnomalyResult | None = None
        if zscore_result and ewma_result:
            z_sev = _severity_rank(zscore_result.severity)
            e_sev = _severity_rank(ewma_result.severity)
            result = zscore_result if z_sev >= e_sev else ewma_result
        elif zscore_result:
            result = zscore_result
        elif ewma_result:
            result = ewma_result

        if result is None:
            continue

        result.anomaly_type = _anomaly_type_for_dimension(dimension)
        result.dimension = dimension

        is_suppressed = await _is_flood_suppressed(db, workspace_id, dimension)

        anomaly = MLAnomaly(
            workspace_id=workspace_id,
            anomaly_type=result.anomaly_type,
            dimension=result.dimension,
            dimension_key=result.dimension_key,
            severity=result.severity,
            detection_method=result.detection_method,
            current_value=Decimal(str(result.current_value)),
            expected_value=Decimal(str(result.expected_value)),
            deviation_score=Decimal(str(round(result.deviation_score, 4))),
            context=result.context,
            is_suppressed=is_suppressed,
            suppressed_reason="flood_suppression" if is_suppressed else None,
        )
        db.add(anomaly)
        anomalies.append(anomaly)

    if anomalies:
        await db.flush()
        log.info("anomalies_detected", workspace_id=str(workspace_id), count=len(anomalies))

    return anomalies


def _severity_rank(severity: str) -> int:
    return {"low": 0, "medium": 1, "high": 2, "critical": 3}.get(severity, 0)
