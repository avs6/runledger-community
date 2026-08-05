"""Anomaly detection using Z-score, EWMA, STL, and Isolation Forest methods.

Z-score and EWMA are univariate detectors that operate on a time-series of
scalar values per dimension. STL (Seasonal-Trend decomposition using LOESS)
strips out trend and weekly seasonality to detect anomalies in the residual
component. Isolation Forest is a multivariate detector that considers all
dimensions simultaneously to catch correlated anomalies that univariate
methods miss.
"""

from __future__ import annotations

import pickle
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import numpy as np
import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.ml import MLAnomaly
from runledger_api.services.ml.features import load_feature_series
from runledger_api.services.ml.registry import load_model, save_model

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


def detect_stl(
    values: list[float],
    period: int = 7,
    threshold_sigma: float = 3.0,
) -> AnomalyResult | None:
    """STL seasonal decomposition — detects anomalies after removing trend and seasonality.

    Requires at least 2 full seasonal cycles (2 * period observations).
    Uses LOESS-based decomposition with weekly (period=7) seasonality by default.
    """
    min_obs = 2 * period + 1
    if len(values) < min_obs:
        return None

    from statsmodels.tsa.seasonal import STL as _STL

    arr = np.array(values, dtype=np.float64)
    try:
        decomposition = _STL(arr, period=period, robust=True).fit()
    except Exception:
        return None

    residuals = decomposition.resid
    resid_history = residuals[:-1]
    resid_std = float(np.std(resid_history, ddof=1))
    if resid_std < 1e-10:
        return None

    current_resid = float(residuals[-1])
    deviation = current_resid / resid_std

    if abs(deviation) < threshold_sigma:
        return None

    trend_last = float(decomposition.trend[-1])
    seasonal_last = float(decomposition.seasonal[-1])
    expected = trend_last + seasonal_last

    return AnomalyResult(
        anomaly_type="",
        dimension="",
        dimension_key=None,
        current_value=values[-1],
        expected_value=round(expected, 6),
        deviation_score=round(deviation, 4),
        severity=classify_severity(deviation),
        detection_method="stl",
        context={
            "trend": round(trend_last, 6),
            "seasonal": round(seasonal_last, 6),
            "residual": round(current_resid, 6),
            "residual_std": round(resid_std, 6),
            "deviation": round(deviation, 4),
            "period": period,
            "window_size": len(values),
        },
    )


async def _build_multivariate_matrix(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    days: int = 30,
) -> tuple[np.ndarray, list[date]]:
    """Load all dimension features and align into a (days x dims) matrix.

    Returns the feature matrix and the list of dates for each row.
    """
    all_series: dict[str, dict[date, float]] = {}
    for dim in _DIMENSIONS:
        series = await load_feature_series(db, workspace_id, dim, days=days)
        all_series[dim] = {row["date"]: row["features"].get("value", 0.0) for row in series}

    all_dates = sorted(set().union(*(s.keys() for s in all_series.values())))
    if not all_dates:
        return np.empty((0, len(_DIMENSIONS))), []

    matrix = np.zeros((len(all_dates), len(_DIMENSIONS)), dtype=np.float64)
    for j, dim in enumerate(_DIMENSIONS):
        for i, d in enumerate(all_dates):
            matrix[i, j] = all_series[dim].get(d, 0.0)

    return matrix, all_dates


async def train_isolation_forest(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    days: int = 60,
    contamination: float = 0.05,
    n_estimators: int = 100,
) -> dict[str, Any]:
    """Train an Isolation Forest on multivariate daily features and save it."""
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler

    matrix, dates = await _build_multivariate_matrix(db, workspace_id, days=days)
    if matrix.shape[0] < 14:
        return {"status": "skipped", "reason": "insufficient_data", "rows": matrix.shape[0]}

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(matrix)

    model = IsolationForest(
        n_estimators=n_estimators,
        contamination=contamination,
        random_state=42,
    )
    model.fit(X_scaled)

    artifact = pickle.dumps({"model": model, "scaler": scaler, "dimensions": _DIMENSIONS})

    await save_model(
        db,
        workspace_id,
        model_type="isolation_forest",
        dimension="multivariate",
        artifact_bytes=artifact,
        hyperparams={
            "n_estimators": n_estimators,
            "contamination": contamination,
            "days": days,
        },
        metrics={"sample_count": matrix.shape[0], "features": len(_DIMENSIONS)},
        sample_count=matrix.shape[0],
    )
    return {"status": "trained", "sample_count": matrix.shape[0], "features": len(_DIMENSIONS)}


async def detect_isolation_forest(
    db: AsyncSession,
    workspace_id: uuid.UUID,
) -> list[AnomalyResult]:
    """Run Isolation Forest on today's multivariate feature vector.

    Returns anomaly results for each dimension that contributed most to the
    anomaly score, if the overall point is flagged as anomalous.
    """
    stored = await load_model(db, workspace_id, "isolation_forest", "multivariate")
    if stored is None or stored.artifact is None:
        return []

    artifact = pickle.loads(stored.artifact)  # noqa: S301
    model = artifact["model"]
    scaler = artifact["scaler"]
    dims = artifact["dimensions"]

    matrix, dates = await _build_multivariate_matrix(db, workspace_id, days=30)
    if matrix.shape[0] < 7:
        return []

    X_scaled = scaler.transform(matrix)
    last_point = X_scaled[-1:]
    prediction = model.predict(last_point)

    if prediction[0] != -1:
        return []

    score = float(model.decision_function(last_point)[0])
    deviation = abs(score) / max(abs(model.offset_), 1e-10) * 3.0

    results: list[AnomalyResult] = []
    last_raw = matrix[-1]
    history = matrix[:-1]
    means = history.mean(axis=0)
    stds = history.std(axis=0, ddof=1)

    for j, dim in enumerate(dims):
        std_j = stds[j] if stds[j] > 1e-10 else 1.0
        dim_z = abs((last_raw[j] - means[j]) / std_j)
        if dim_z < 1.5:
            continue
        results.append(AnomalyResult(
            anomaly_type=_anomaly_type_for_dimension(dim),
            dimension=dim,
            dimension_key=None,
            current_value=float(last_raw[j]),
            expected_value=float(means[j]),
            deviation_score=round(deviation, 4),
            severity=classify_severity(deviation),
            detection_method="isolation_forest",
            context={
                "if_anomaly_score": round(score, 6),
                "dimension_z_score": round(dim_z, 4),
                "contributing_dimensions": [
                    dims[k] for k in range(len(dims))
                    if stds[k] > 1e-10 and abs((last_raw[k] - means[k]) / stds[k]) >= 1.5
                ],
            },
        ))

    return results


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
        stl_result = detect_stl(values)

        candidates = [r for r in (zscore_result, ewma_result, stl_result) if r is not None]
        result: AnomalyResult | None = None
        if candidates:
            result = max(candidates, key=lambda r: _severity_rank(r.severity))

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

    # ── Isolation Forest (multivariate) ────────────────────────────────
    if_results = await detect_isolation_forest(db, workspace_id)
    for result in if_results:
        already_flagged = any(
            a.dimension == result.dimension and a.detection_method != "isolation_forest"
            for a in anomalies
        )
        if already_flagged:
            continue

        is_suppressed = await _is_flood_suppressed(db, workspace_id, result.dimension)
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
