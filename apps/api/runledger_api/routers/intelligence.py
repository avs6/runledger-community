"""ML Intelligence API — anomaly detection, forecasting, top-K, patterns, complexity, and ML observability.

All endpoints are workspace-scoped via Bearer API key authentication.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace
from runledger_api.core.ratelimit import analytics_rate_limit
from runledger_api.models.ml import (
    ForecastAccuracy,
    MLAnomaly,
    MLForecast,
    MLModel,
    MLPattern,
)
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.ml import (
    AdaptiveThresholdList,
    AnomalyAcknowledge,
    AnomalyList,
    AnomalyResponse,
    AnomalySummary,
    CostOutcomeResponse,
    ComplexityScoreList,
    FeatureImportanceList,
    ForecastGenerateRequest,
    ForecastList,
    ForecastResponse,
    MLDashboard,
    ModelHealth,
    PatternList,
    PatternResponse,
    TopKResponse,
)

log = structlog.get_logger()

router = APIRouter(prefix="/intelligence", tags=["intelligence"])

WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]
DbDep = Annotated[AsyncSession, Depends(get_db)]


def _parse_dt(raw: str | None, default: datetime) -> datetime:
    if not raw:
        return default
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return default


# ── Anomaly endpoints ───────────────────────────────────────────────────


@router.get("/anomalies", response_model=AnomalyList, dependencies=[Depends(analytics_rate_limit)])
async def list_anomalies(
    workspace: WorkspaceDep,
    db: DbDep,
    anomaly_type: str | None = None,
    severity: str | None = None,
    suppressed: bool | None = None,
    from_dt: str | None = Query(None, alias="from"),
    to_dt: str | None = Query(None, alias="to"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
) -> AnomalyList:
    now = datetime.now(UTC)
    start = _parse_dt(from_dt, now - timedelta(days=7))
    end = _parse_dt(to_dt, now)

    where = [
        MLAnomaly.workspace_id == workspace.id,
        MLAnomaly.detected_at >= start,
        MLAnomaly.detected_at <= end,
    ]
    if anomaly_type:
        where.append(MLAnomaly.anomaly_type == anomaly_type)
    if severity:
        where.append(MLAnomaly.severity == severity)
    if suppressed is not None:
        where.append(MLAnomaly.is_suppressed == suppressed)

    total = await db.scalar(select(func.count()).where(and_(*where)))

    result = await db.execute(
        select(MLAnomaly)
        .where(and_(*where))
        .order_by(MLAnomaly.detected_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = result.scalars().all()

    return AnomalyList(
        items=[_anomaly_to_response(a) for a in rows],
        total=total or 0,
    )


@router.get("/anomalies/summary", response_model=AnomalySummary, dependencies=[Depends(analytics_rate_limit)])
async def anomaly_summary(
    workspace: WorkspaceDep,
    db: DbDep,
    hours: int = Query(24, ge=1, le=720),
) -> AnomalySummary:
    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    base = [MLAnomaly.workspace_id == workspace.id, MLAnomaly.detected_at >= cutoff]

    total = await db.scalar(select(func.count()).where(and_(*base))) or 0

    sev_result = await db.execute(
        select(MLAnomaly.severity, func.count())
        .where(and_(*base))
        .group_by(MLAnomaly.severity)
    )
    by_severity = {row[0]: row[1] for row in sev_result.all()}

    type_result = await db.execute(
        select(MLAnomaly.anomaly_type, func.count())
        .where(and_(*base))
        .group_by(MLAnomaly.anomaly_type)
    )
    by_type = {row[0]: row[1] for row in type_result.all()}

    suppressed = await db.scalar(
        select(func.count()).where(and_(*base, MLAnomaly.is_suppressed.is_(True)))
    ) or 0

    acknowledged = await db.scalar(
        select(func.count()).where(and_(*base, MLAnomaly.acknowledged_at.isnot(None)))
    ) or 0

    return AnomalySummary(
        total=total,
        by_severity=by_severity,
        by_type=by_type,
        suppressed=suppressed,
        acknowledged=acknowledged,
    )


@router.post("/anomalies/{anomaly_id}/acknowledge", response_model=AnomalyResponse)
async def acknowledge_anomaly(
    anomaly_id: uuid.UUID,
    workspace: WorkspaceDep,
    db: DbDep,
) -> AnomalyResponse:
    result = await db.execute(
        select(MLAnomaly).where(
            MLAnomaly.id == anomaly_id,
            MLAnomaly.workspace_id == workspace.id,
        )
    )
    anomaly = result.scalar_one_or_none()
    if not anomaly:
        raise HTTPException(status_code=404, detail="Anomaly not found")

    anomaly.acknowledged_at = datetime.now(UTC)
    await db.commit()
    return _anomaly_to_response(anomaly)


@router.post("/anomalies/train-isolation-forest")
async def train_isolation_forest_endpoint(
    workspace: WorkspaceDep,
    db: DbDep,
    days: int = Query(60, ge=14, le=365),
) -> dict[str, Any]:
    """Train (or retrain) the Isolation Forest model for multivariate anomaly detection."""
    from runledger_api.services.ml.anomaly import train_isolation_forest

    result = await train_isolation_forest(db, workspace.id, days=days)
    await db.commit()
    return result


# ── Forecast endpoints ──────────────────────────────────────────────────


@router.get("/forecasts/cost", response_model=ForecastResponse | None, dependencies=[Depends(analytics_rate_limit)])
async def get_cost_forecast(
    workspace: WorkspaceDep,
    db: DbDep,
) -> ForecastResponse | None:
    return await _get_latest_forecast(db, workspace.id, "cost_daily")


@router.get("/forecasts/tokens", response_model=ForecastResponse | None, dependencies=[Depends(analytics_rate_limit)])
async def get_token_forecast(
    workspace: WorkspaceDep,
    db: DbDep,
) -> ForecastResponse | None:
    return await _get_latest_forecast(db, workspace.id, "tokens_daily")


@router.post("/forecasts/generate", response_model=dict, dependencies=[Depends(analytics_rate_limit)])
async def generate_forecast(
    workspace: WorkspaceDep,
    db: DbDep,
    body: ForecastGenerateRequest,
) -> dict:
    from runledger_api.services.ml.forecast import run_forecast
    forecast = await run_forecast(
        db, workspace.id, body.forecast_type, body.horizon_days, body.dimension_key
    )
    if forecast:
        await db.commit()
        return {"status": "ok", "forecast_id": str(forecast.id)}
    return {"status": "insufficient_data"}


@router.get("/forecasts/{forecast_id}", response_model=ForecastResponse, dependencies=[Depends(analytics_rate_limit)])
async def get_forecast(
    forecast_id: uuid.UUID,
    workspace: WorkspaceDep,
    db: DbDep,
) -> ForecastResponse:
    result = await db.execute(
        select(MLForecast).where(
            MLForecast.id == forecast_id,
            MLForecast.workspace_id == workspace.id,
        )
    )
    forecast = result.scalar_one_or_none()
    if not forecast:
        raise HTTPException(status_code=404, detail="Forecast not found")
    return _forecast_to_response(forecast)


# ── Top-K endpoints ─────────────────────────────────────────────────────


@router.get("/top-k", response_model=TopKResponse, dependencies=[Depends(analytics_rate_limit)])
async def top_k_analysis(
    workspace: WorkspaceDep,
    db: DbDep,
    dimension: str = Query(..., description="model, user, intent, feature_tag, provider"),
    metric: str = Query("cost", description="cost, tokens, call_count, latency_p95, error_rate"),
    k: int = Query(10, ge=1, le=100),
    from_dt: str | None = Query(None, alias="from"),
    to_dt: str | None = Query(None, alias="to"),
) -> TopKResponse:
    from runledger_api.services.ml.topk import compute_top_k
    now = datetime.now(UTC)
    start = _parse_dt(from_dt, now - timedelta(days=7))
    end = _parse_dt(to_dt, now)
    return await compute_top_k(db, workspace.id, dimension, metric, k, start, end)


# ── Pattern endpoints ───────────────────────────────────────────────────


@router.get("/patterns", response_model=PatternList, dependencies=[Depends(analytics_rate_limit)])
async def list_patterns(
    workspace: WorkspaceDep,
    db: DbDep,
    dimension: str | None = None,
) -> PatternList:
    where = [MLPattern.workspace_id == workspace.id]
    if dimension:
        where.append(MLPattern.dimension == dimension)

    result = await db.execute(
        select(MLPattern)
        .where(and_(*where))
        .order_by(MLPattern.detected_at.desc())
        .limit(50)
    )
    rows = result.scalars().all()
    return PatternList(items=[_pattern_to_response(p) for p in rows])


@router.get("/patterns/{dimension}", response_model=PatternList, dependencies=[Depends(analytics_rate_limit)])
async def patterns_by_dimension(
    dimension: str,
    workspace: WorkspaceDep,
    db: DbDep,
) -> PatternList:
    result = await db.execute(
        select(MLPattern)
        .where(MLPattern.workspace_id == workspace.id, MLPattern.dimension == dimension)
        .order_by(MLPattern.detected_at.desc())
        .limit(50)
    )
    rows = result.scalars().all()
    return PatternList(items=[_pattern_to_response(p) for p in rows])


# ── Complexity endpoints ────────────────────────────────────────────────


@router.get("/complexity/scores", response_model=ComplexityScoreList, dependencies=[Depends(analytics_rate_limit)])
async def complexity_scores(
    workspace: WorkspaceDep,
    db: DbDep,
    hours: int = Query(24, ge=1, le=720),
) -> ComplexityScoreList:
    from runledger_api.services.ml.complexity import get_recent_scores
    return await get_recent_scores(db, workspace.id, hours)


@router.get("/complexity/importances", response_model=FeatureImportanceList, dependencies=[Depends(analytics_rate_limit)])
async def feature_importances(
    workspace: WorkspaceDep,
    db: DbDep,
) -> FeatureImportanceList:
    from runledger_api.services.ml.complexity import get_feature_importances
    return await get_feature_importances(db, workspace.id)


@router.post("/complexity/retrain", response_model=dict)
async def retrain_complexity(
    workspace: WorkspaceDep,
    db: DbDep,
) -> dict:
    from runledger_api.services.ml.complexity import train_complexity_model
    result = await train_complexity_model(db, workspace.id)
    if result:
        await db.commit()
        return {"status": "ok", "model_id": str(result.id)}
    return {"status": "insufficient_data"}


# ── Cost-per-outcome endpoints ──────────────────────────────────────────


@router.get("/cost-per-outcome", response_model=CostOutcomeResponse, dependencies=[Depends(analytics_rate_limit)])
async def cost_per_outcome(
    workspace: WorkspaceDep,
    db: DbDep,
    from_dt: str | None = Query(None, alias="from"),
    to_dt: str | None = Query(None, alias="to"),
) -> CostOutcomeResponse:
    from runledger_api.services.ml.cost_outcome import compute_cost_per_outcome
    now = datetime.now(UTC)
    start = _parse_dt(from_dt, now - timedelta(days=30))
    end = _parse_dt(to_dt, now)
    return await compute_cost_per_outcome(db, workspace.id, start, end)


# ── Adaptive alert endpoints ───────────────────────────────────────────


@router.get("/alerts/adaptive-suggestions", response_model=AdaptiveThresholdList, dependencies=[Depends(analytics_rate_limit)])
async def adaptive_suggestions(
    workspace: WorkspaceDep,
    db: DbDep,
) -> AdaptiveThresholdList:
    from runledger_api.services.ml.adaptive_alerts import suggest_thresholds
    return await suggest_thresholds(db, workspace.id)


@router.post("/alerts/{rule_id}/enable-adaptive", response_model=dict)
async def enable_adaptive(
    rule_id: uuid.UUID,
    workspace: WorkspaceDep,
    db: DbDep,
) -> dict:
    from runledger_api.models.alerts import AlertRule
    result = await db.execute(
        select(AlertRule).where(AlertRule.id == rule_id, AlertRule.workspace_id == workspace.id)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    rule.use_adaptive = True
    await db.commit()
    return {"status": "ok", "rule_id": str(rule_id)}


# ── ML dashboard / observability endpoints ──────────────────────────────


@router.get("/dashboard", response_model=MLDashboard, dependencies=[Depends(analytics_rate_limit)])
async def ml_dashboard(
    workspace: WorkspaceDep,
    db: DbDep,
) -> MLDashboard:
    from runledger_api.services.ml.observability import get_dashboard
    return await get_dashboard(db, workspace.id)


@router.get("/models", response_model=list[ModelHealth], dependencies=[Depends(analytics_rate_limit)])
async def list_ml_models(
    workspace: WorkspaceDep,
    db: DbDep,
) -> list[ModelHealth]:
    from runledger_api.services.ml.observability import get_model_health_list
    return await get_model_health_list(db, workspace.id)


# ── Helpers ─────────────────────────────────────────────────────────────


def _anomaly_to_response(a: MLAnomaly) -> AnomalyResponse:
    return AnomalyResponse(
        id=str(a.id),
        workspace_id=str(a.workspace_id),
        anomaly_type=a.anomaly_type,
        dimension=a.dimension,
        dimension_key=a.dimension_key,
        detected_at=a.detected_at,
        severity=a.severity,
        detection_method=a.detection_method,
        current_value=str(a.current_value),
        expected_value=str(a.expected_value),
        deviation_score=str(a.deviation_score),
        context=a.context,
        is_suppressed=a.is_suppressed,
        suppressed_reason=a.suppressed_reason,
        acknowledged_at=a.acknowledged_at,
        created_at=a.created_at,
    )


def _forecast_to_response(f: MLForecast, budget_overlay: Any = None) -> ForecastResponse:
    from runledger_api.schemas.ml import ForecastPoint
    return ForecastResponse(
        id=str(f.id),
        workspace_id=str(f.workspace_id),
        forecast_type=f.forecast_type,
        dimension_key=f.dimension_key,
        method=f.method,
        horizon_days=f.horizon_days,
        forecast_from=str(f.forecast_from),
        points=[ForecastPoint(**p) for p in (f.points or [])],
        accuracy_metrics=f.accuracy_metrics or {},
        budget_overlay=budget_overlay,
        created_at=f.created_at,
    )


def _pattern_to_response(p: MLPattern) -> PatternResponse:
    return PatternResponse(
        id=str(p.id),
        workspace_id=str(p.workspace_id),
        dimension=p.dimension,
        dimension_key=p.dimension_key,
        pattern=p.pattern,
        confidence=str(p.confidence),
        evidence=p.evidence,
        detected_at=p.detected_at,
    )


async def _get_latest_forecast(
    db: AsyncSession, workspace_id: uuid.UUID, forecast_type: str
) -> ForecastResponse | None:
    result = await db.execute(
        select(MLForecast)
        .where(MLForecast.workspace_id == workspace_id, MLForecast.forecast_type == forecast_type)
        .order_by(MLForecast.created_at.desc())
        .limit(1)
    )
    forecast = result.scalar_one_or_none()
    if not forecast:
        return None
    return _forecast_to_response(forecast)
