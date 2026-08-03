"""
Analytics query API — cost and usage aggregates.

All endpoints are workspace-scoped via Bearer API key authentication.
Data is read directly from provider_calls (and agent_runs for feature_tag).

Time-range parameters:
  ``from_dt``  ISO-8601 datetime (default: 7 days ago)
  ``to_dt``    ISO-8601 datetime (default: now)

All amounts are in USD.
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from fastapi.responses import StreamingResponse
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_user, get_current_workspace
from runledger_api.core.ratelimit import analytics_rate_limit
from runledger_api.models.annotations import Annotation
from runledger_api.models.events import AgentRun, OutcomeEvent, ProviderCall, Span, ToolCall
from runledger_api.models.metering import UsageDaily
from runledger_api.models.replay import UserAnomaly
from runledger_api.models.scores import ScoreEvent
from runledger_api.models.tenant import TenantUser, Workspace
from runledger_api.schemas.analytics import (
    AnalyticsSummary,
    AnomalyItem,
    AnomalyList,
    CohortList,
    CohortSummary,
    FeatureSpend,
    IntentCount,
    ModelSpend,
    OptimizationOpportunitiesResponse,
    OptimizationOpportunity,
    RequestExplorerResponse,
    RequestRecord,
    SavingsByCategory,
    SavingsResponse,
    SavingsTimeline,
    ScopedSummary,
    SpendByFeature,
    SpendByModel,
    SpendByUser,
    SpendOverTime,
    SpendPoint,
    TrendMetric,
    TrendPoint,
    TrendsResponse,
    UserSpend,
    UserSpendDetail,
    CostByDimension,
    EngineeringMetrics,
    LifecycleStage,
    QualityFunnel,
    ModelScorecard,
    ModelScorecardList,
    SimulationImpact,
    SimulationRequest,
    SimulationResult,
)
from runledger_api.schemas.economics import (
    AnnotationCreate,
    AnnotationList,
    AnnotationResponse,
    ModelCost,
    RegressionItem,
    RegressionList,
    RunEconomics,
    SpanTypeCost,
    SpanTypeDelta,
    VersionCompareResult,
    VersionSummary,
    WorkflowSummary,
    WorkflowTopList,
)
from runledger_api.schemas.evaluators import (
    BestValueModel,
    BestValueResponse,
    CostQualityPoint,
    CostQualityResponse,
)
from runledger_api.schemas.scores import (
    ScoreRegressionItem,
    ScoreSummary,
    ScoreSummaryItem,
)

router = APIRouter(
    prefix="/analytics", tags=["analytics"], dependencies=[Depends(analytics_rate_limit)]
)
log = structlog.get_logger()

# ── Helpers ───────────────────────────────────────────────────────────────────

_DEFAULT_LOOKBACK_DAYS = 7


def _default_from() -> datetime:
    return datetime.now(UTC) - timedelta(days=_DEFAULT_LOOKBACK_DAYS)


def _default_to() -> datetime:
    return datetime.now(UTC)


def _parse_dt(value: str | None, default: datetime) -> datetime:
    if not value:
        return default
    return datetime.fromisoformat(value)


# ── /analytics/summary ────────────────────────────────────────────────────────


@router.get("/summary", response_model=AnalyticsSummary)
async def analytics_summary(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
) -> AnalyticsSummary:
    """Total cost, tokens, run count and call count for the time window."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())

    # Prior period: same duration, shifted back
    duration = t_to - t_from
    prev_from = t_from - duration
    prev_to = t_from

    def _summary_stmt(period_from: datetime, period_to: datetime) -> Any:
        return select(
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("total_cost"),
            func.coalesce(func.sum(ProviderCall.input_tokens), 0).label("total_input"),
            func.coalesce(func.sum(ProviderCall.output_tokens), 0).label("total_output"),
            func.count(ProviderCall.run_id.distinct()).label("run_count"),
            func.count(ProviderCall.id).label("call_count"),
        ).where(
            ProviderCall.workspace_id == workspace.id,
            ProviderCall.created_at >= period_from,
            ProviderCall.created_at < period_to,
            ProviderCall.status == "success",
        )

    result = await db.execute(_summary_stmt(t_from, t_to))
    row = result.one()

    prev_result = await db.execute(_summary_stmt(prev_from, prev_to))
    prev_row = prev_result.one()

    prev_cost: Decimal = prev_row.total_cost
    cost_delta_pct: Decimal | None = None
    if prev_cost and prev_cost > Decimal(0):
        cost_delta_pct = (row.total_cost - prev_cost) / prev_cost * Decimal(100)

    return AnalyticsSummary(
        total_cost_usd=row.total_cost,
        total_input_tokens=row.total_input,
        total_output_tokens=row.total_output,
        run_count=row.run_count,
        call_count=row.call_count,
        prev_cost_usd=prev_cost,
        cost_delta_pct=cost_delta_pct,
    )


# ── /analytics/spend-over-time ────────────────────────────────────────────────


@router.get("/spend-over-time", response_model=SpendOverTime)
async def spend_over_time(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    granularity: Annotated[str, Query(pattern="^(minute|5min|hourly|daily)$")] = "daily",
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
) -> SpendOverTime:
    """Time-series of cost and token usage, bucketed by minute, 5 minutes, hour, or day."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())

    if granularity == "minute":
        period_col = func.date_trunc("minute", ProviderCall.created_at).label("period")
    elif granularity == "5min":
        period_col = func.to_timestamp(func.floor(func.extract("epoch", ProviderCall.created_at) / 300) * 300).label("period")
    else:
        trunc_unit = "hour" if granularity == "hourly" else "day"
        period_col = func.date_trunc(trunc_unit, ProviderCall.created_at).label("period")

    stmt = (
        select(
            period_col,
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost_usd"),
            func.coalesce(func.sum(ProviderCall.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(ProviderCall.output_tokens), 0).label("output_tokens"),
            func.count(ProviderCall.id).label("call_count"),
        )
        .where(
            ProviderCall.workspace_id == workspace.id,
            ProviderCall.created_at >= t_from,
            ProviderCall.created_at < t_to,
            ProviderCall.status == "success",
        )
        .group_by(period_col)
        .order_by(period_col)
    )

    result = await db.execute(stmt)
    rows = result.all()

    return SpendOverTime(
        granularity=granularity,
        points=[
            SpendPoint(
                period=row.period.isoformat(),
                cost_usd=row.cost_usd,
                input_tokens=row.input_tokens,
                output_tokens=row.output_tokens,
                call_count=row.call_count,
            )
            for row in rows
        ],
    )


# ── /analytics/spend-by-model ─────────────────────────────────────────────────


@router.get("/spend-by-model", response_model=SpendByModel)
async def spend_by_model(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
) -> SpendByModel:
    """Cost and token usage broken down by provider + model."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())

    stmt = (
        select(
            ProviderCall.provider,
            ProviderCall.model,
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost_usd"),
            func.coalesce(func.sum(ProviderCall.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(ProviderCall.output_tokens), 0).label("output_tokens"),
            func.count(ProviderCall.id).label("call_count"),
        )
        .where(
            ProviderCall.workspace_id == workspace.id,
            ProviderCall.created_at >= t_from,
            ProviderCall.created_at < t_to,
            ProviderCall.status == "success",
        )
        .group_by(ProviderCall.provider, ProviderCall.model)
        .order_by(func.sum(ProviderCall.cost_usd).desc().nulls_last())
    )

    result = await db.execute(stmt)
    rows = result.all()

    return SpendByModel(
        items=[
            ModelSpend(
                provider=row.provider,
                model=row.model,
                cost_usd=row.cost_usd,
                input_tokens=row.input_tokens,
                output_tokens=row.output_tokens,
                call_count=row.call_count,
            )
            for row in rows
        ]
    )


# ── /analytics/spend-by-user ──────────────────────────────────────────────────


@router.get("/spend-by-user", response_model=SpendByUser)
async def spend_by_user(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> SpendByUser:
    """Top end-users by spend."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())

    stmt = (
        select(
            ProviderCall.end_user_id,
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost_usd"),
            func.count(ProviderCall.run_id.distinct()).label("run_count"),
            func.count(ProviderCall.id).label("call_count"),
            func.max(ProviderCall.created_at).label("last_active"),
            func.min(ProviderCall.created_at).label("first_seen"),
        )
        .where(
            ProviderCall.workspace_id == workspace.id,
            ProviderCall.created_at >= t_from,
            ProviderCall.created_at < t_to,
            ProviderCall.status == "success",
            ProviderCall.end_user_id.is_not(None),
        )
        .group_by(ProviderCall.end_user_id)
        .order_by(func.sum(ProviderCall.cost_usd).desc().nulls_last())
        .limit(limit)
    )

    result = await db.execute(stmt)
    rows = result.all()

    return SpendByUser(
        items=[
            UserSpend(
                end_user_id=row.end_user_id,
                cost_usd=row.cost_usd,
                run_count=row.run_count,
                call_count=row.call_count,
                avg_cost_per_run=(
                    row.cost_usd / row.run_count if row.run_count > 0 else Decimal(0)
                ),
                last_active=(row.last_active.isoformat() if row.last_active else None),
                first_seen=(row.first_seen.isoformat() if row.first_seen else None),
            )
            for row in rows
        ]
    )


# ── /analytics/spend-by-feature ───────────────────────────────────────────────


@router.get("/spend-by-feature", response_model=SpendByFeature)
async def spend_by_feature(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
) -> SpendByFeature:
    """Cost and run count broken down by feature_tag."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())

    # Join to agent_runs to get feature_tag (stored on the run, not the call)
    stmt = (
        select(
            AgentRun.feature_tag,
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost_usd"),
            func.count(ProviderCall.run_id.distinct()).label("run_count"),
            func.count(ProviderCall.id).label("call_count"),
        )
        .join(AgentRun, AgentRun.id == ProviderCall.run_id)
        .where(
            ProviderCall.workspace_id == workspace.id,
            ProviderCall.created_at >= t_from,
            ProviderCall.created_at < t_to,
            ProviderCall.status == "success",
        )
        .group_by(AgentRun.feature_tag)
        .order_by(func.sum(ProviderCall.cost_usd).desc().nulls_last())
    )

    result = await db.execute(stmt)
    rows = result.all()

    return SpendByFeature(
        items=[
            FeatureSpend(
                feature_tag=row.feature_tag,
                cost_usd=row.cost_usd,
                run_count=row.run_count,
                call_count=row.call_count,
            )
            for row in rows
        ]
    )


# ── /analytics/users/cohorts ─────────────────────────────────────────────────


_DEFAULT_COHORT_DAYS = 30


@router.get("/users/cohorts", response_model=CohortList)
async def user_cohorts(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
) -> CohortList:
    """Classify end-users into P0–P3 spend tiers for the window (default 30d)."""
    t_to = _parse_dt(to_dt, _default_to())
    t_from = _parse_dt(
        from_dt,
        datetime.now(UTC) - timedelta(days=_DEFAULT_COHORT_DAYS),
    )

    # Inner subquery: per-user total spend
    inner = (
        select(
            ProviderCall.end_user_id,
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost"),
        )
        .where(
            ProviderCall.workspace_id == workspace.id,
            ProviderCall.created_at >= t_from,
            ProviderCall.created_at < t_to,
            ProviderCall.status == "success",
            ProviderCall.end_user_id.is_not(None),
        )
        .group_by(ProviderCall.end_user_id)
        .subquery()
    )

    tier_col = case(
        (inner.c.cost < Decimal("1"), "P0"),
        (inner.c.cost < Decimal("10"), "P1"),
        (inner.c.cost < Decimal("100"), "P2"),
        else_="P3",
    ).label("tier")

    stmt = (
        select(
            tier_col,
            func.count().label("user_count"),
            func.avg(inner.c.cost).label("avg_cost_usd"),
            func.sum(inner.c.cost).label("total_cost_usd"),
        )
        .select_from(inner)
        .group_by(tier_col)
        .order_by(tier_col)
    )

    result = await db.execute(stmt)
    rows = result.all()

    window_days = int((t_to - t_from).total_seconds() / 86400)
    return CohortList(
        items=[
            CohortSummary(
                cohort_tier=row.tier,
                user_count=row.user_count,
                avg_cost_usd=Decimal(str(row.avg_cost_usd)),
                total_cost_usd=Decimal(str(row.total_cost_usd)),
            )
            for row in rows
        ],
        window_days=window_days,
    )


# ── /analytics/users/anomalies ────────────────────────────────────────────────


@router.get("/users/anomalies", response_model=AnomalyList)
async def user_anomalies(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AnomalyList:
    """Most-recent 100 anomaly flags for the workspace (populated by nightly worker)."""
    stmt = (
        select(UserAnomaly)
        .where(UserAnomaly.workspace_id == workspace.id)
        .order_by(UserAnomaly.detected_at.desc())
        .limit(100)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()
    return AnomalyList(items=[AnomalyItem.model_validate(r) for r in items])


# ── /analytics/users/{end_user_id} ────────────────────────────────────────────


@router.get("/users/{end_user_id}", response_model=UserSpendDetail)
async def user_spend_detail(
    end_user_id: str,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
) -> UserSpendDetail:
    """Spend profile for a single end-user: summary + trend + models + features."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())

    base_filter = [
        ProviderCall.workspace_id == workspace.id,
        ProviderCall.end_user_id == end_user_id,
        ProviderCall.created_at >= t_from,
        ProviderCall.created_at < t_to,
        ProviderCall.status == "success",
    ]

    # ── Summary ──────────────────────────────────────────────────────────────
    summary_stmt = select(
        func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost_usd"),
        func.count(ProviderCall.run_id.distinct()).label("run_count"),
        func.count(ProviderCall.id).label("call_count"),
        func.max(ProviderCall.created_at).label("last_active"),
    ).where(*base_filter)

    # ── Spend over time (daily) ───────────────────────────────────────────────
    period_col = func.date_trunc("day", ProviderCall.created_at).label("period")
    time_stmt = (
        select(
            period_col,
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost_usd"),
            func.coalesce(func.sum(ProviderCall.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(ProviderCall.output_tokens), 0).label("output_tokens"),
            func.count(ProviderCall.id).label("call_count"),
        )
        .where(*base_filter)
        .group_by(period_col)
        .order_by(period_col)
    )

    # ── Models used ───────────────────────────────────────────────────────────
    model_stmt = (
        select(
            ProviderCall.provider,
            ProviderCall.model,
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost_usd"),
            func.coalesce(func.sum(ProviderCall.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(ProviderCall.output_tokens), 0).label("output_tokens"),
            func.count(ProviderCall.id).label("call_count"),
        )
        .where(*base_filter)
        .group_by(ProviderCall.provider, ProviderCall.model)
        .order_by(func.sum(ProviderCall.cost_usd).desc().nulls_last())
    )

    # ── Features used ─────────────────────────────────────────────────────────
    feature_stmt = (
        select(
            AgentRun.feature_tag,
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost_usd"),
            func.count(ProviderCall.run_id.distinct()).label("run_count"),
            func.count(ProviderCall.id).label("call_count"),
        )
        .join(AgentRun, AgentRun.id == ProviderCall.run_id)
        .where(*base_filter)
        .group_by(AgentRun.feature_tag)
        .order_by(func.sum(ProviderCall.cost_usd).desc().nulls_last())
    )

    summary_result = await db.execute(summary_stmt)
    summary_row = summary_result.one()

    time_result = await db.execute(time_stmt)
    time_rows = time_result.all()

    model_result = await db.execute(model_stmt)
    model_rows = model_result.all()

    feature_result = await db.execute(feature_stmt)
    feature_rows = feature_result.all()

    avg_cost_per_run = (
        summary_row.cost_usd / summary_row.run_count if summary_row.run_count > 0 else Decimal(0)
    )

    return UserSpendDetail(
        end_user_id=end_user_id,
        cost_usd=summary_row.cost_usd,
        run_count=summary_row.run_count,
        call_count=summary_row.call_count,
        avg_cost_per_run=avg_cost_per_run,
        last_active=(summary_row.last_active.isoformat() if summary_row.last_active else None),
        spend_over_time=[
            SpendPoint(
                period=row.period.isoformat(),
                cost_usd=row.cost_usd,
                input_tokens=row.input_tokens,
                output_tokens=row.output_tokens,
                call_count=row.call_count,
            )
            for row in time_rows
        ],
        models_used=[
            ModelSpend(
                provider=row.provider,
                model=row.model,
                cost_usd=row.cost_usd,
                input_tokens=row.input_tokens,
                output_tokens=row.output_tokens,
                call_count=row.call_count,
            )
            for row in model_rows
        ],
        features_used=[
            FeatureSpend(
                feature_tag=row.feature_tag,
                cost_usd=row.cost_usd,
                run_count=row.run_count,
                call_count=row.call_count,
            )
            for row in feature_rows
        ],
    )


# ── /analytics/economics/{run_id} ────────────────────────────────────────────


@router.get("/economics/{run_id}", response_model=RunEconomics)
async def run_economics(
    run_id: str,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RunEconomics:
    """Per-run cost breakdown by span type and by model."""
    # Verify run belongs to this workspace
    run_stmt = select(AgentRun).where(
        AgentRun.id == run_id,
        AgentRun.workspace_id == workspace.id,
    )
    run_result = await db.execute(run_stmt)
    run = run_result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    # Span-type cost breakdown
    span_stmt = (
        select(
            Span.span_type,
            func.coalesce(func.sum(Span.cost_usd), Decimal(0)).label("cost_usd"),
        )
        .where(Span.run_id == run_id)
        .group_by(Span.span_type)
        .order_by(func.sum(Span.cost_usd).desc().nulls_last())
    )
    span_result = await db.execute(span_stmt)
    span_rows = span_result.all()

    # Model cost breakdown (provider_calls = authoritative cost source)
    model_stmt = (
        select(
            ProviderCall.model,
            ProviderCall.provider,
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost_usd"),
            func.count(ProviderCall.id).label("call_count"),
        )
        .where(ProviderCall.run_id == run_id)
        .group_by(ProviderCall.model, ProviderCall.provider)
        .order_by(func.sum(ProviderCall.cost_usd).desc().nulls_last())
    )
    model_result = await db.execute(model_stmt)
    model_rows = model_result.all()

    # Retry cost: child LLM spans (parent_span_id IS NOT NULL, span_type='llm')
    retry_stmt = select(func.coalesce(func.sum(Span.cost_usd), Decimal(0))).where(
        Span.run_id == run_id,
        Span.parent_span_id.is_not(None),
        Span.span_type == "llm",
    )
    retry_result = await db.execute(retry_stmt)
    retry_cost: Decimal = retry_result.scalar() or Decimal(0)

    # Total from provider_calls (authoritative)
    total_cost = sum((row.cost_usd for row in model_rows), Decimal(0))

    return RunEconomics(
        run_id=run_id,
        total_cost_usd=total_cost,
        cost_by_span_type=[
            SpanTypeCost(span_type=str(row.span_type), cost_usd=row.cost_usd) for row in span_rows
        ],
        cost_by_model=[
            ModelCost(
                model=row.model,
                provider=row.provider,
                cost_usd=row.cost_usd,
                call_count=row.call_count,
            )
            for row in model_rows
        ],
        retry_cost=retry_cost,
    )


# ── /analytics/workflows/top ─────────────────────────────────────────────────


@router.get("/workflows/top", response_model=WorkflowTopList)
async def top_workflows(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    metric: Annotated[str, Query(pattern="^(cost|latency)$")] = "cost",
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
) -> WorkflowTopList:
    """Top workflows ranked by average cost or latency."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())

    order_col = (
        func.avg(AgentRun.total_cost_usd).desc().nulls_last()
        if metric == "cost"
        else func.avg(func.extract("epoch", AgentRun.ended_at - AgentRun.started_at) * 1000)
        .desc()
        .nulls_last()
    )

    # Query 1: run-level aggregates from agent_runs (correct avg/p95)
    run_stmt = (
        select(
            AgentRun.feature_tag,
            AgentRun.application_id,
            func.count(AgentRun.id).label("run_count"),
            func.coalesce(func.avg(AgentRun.total_cost_usd), Decimal(0)).label("avg_cost_usd"),
            func.percentile_cont(0.95).within_group(AgentRun.total_cost_usd).label("p95_cost_usd"),
            func.coalesce(func.sum(AgentRun.total_cost_usd), Decimal(0)).label("total_cost_usd"),
        )
        .where(
            AgentRun.workspace_id == workspace.id,
            AgentRun.started_at >= t_from,
            AgentRun.started_at < t_to,
        )
        .group_by(AgentRun.feature_tag, AgentRun.application_id)
        .order_by(order_col)
        .limit(limit)
    )
    run_result = await db.execute(run_stmt)
    run_rows = run_result.all()

    # Query 2: call counts from provider_calls (separate to avoid join-fan-out)
    call_stmt = (
        select(
            AgentRun.feature_tag,
            AgentRun.application_id,
            func.count(ProviderCall.id).label("call_count"),
        )
        .join(AgentRun, AgentRun.id == ProviderCall.run_id)
        .where(
            ProviderCall.workspace_id == workspace.id,
            ProviderCall.created_at >= t_from,
            ProviderCall.created_at < t_to,
        )
        .group_by(AgentRun.feature_tag, AgentRun.application_id)
    )
    call_result = await db.execute(call_stmt)
    call_rows = call_result.all()

    call_map: dict[tuple[str | None, str | None], int] = {
        (row.feature_tag, str(row.application_id) if row.application_id else None): row.call_count
        for row in call_rows
    }

    items = [
        WorkflowSummary(
            feature_tag=row.feature_tag,
            application_id=str(row.application_id) if row.application_id else None,
            run_count=row.run_count,
            avg_cost_usd=row.avg_cost_usd,
            p95_cost_usd=Decimal(row.p95_cost_usd) if row.p95_cost_usd is not None else Decimal(0),
            total_cost_usd=row.total_cost_usd,
            call_count=call_map.get(
                (row.feature_tag, str(row.application_id) if row.application_id else None), 0
            ),
        )
        for row in run_rows
    ]

    return WorkflowTopList(metric=metric, items=items)


# ── /analytics/compare ────────────────────────────────────────────────────────


@router.get("/compare", response_model=VersionCompareResult)
async def version_compare(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    baseline_version: Annotated[str, Query()],
    comparison_version: Annotated[str, Query()],
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
) -> VersionCompareResult:
    """Compare cost, token, and latency metrics between two deployment versions."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())

    def _run_stats_stmt(version: str) -> Any:
        return select(
            func.count(AgentRun.id).label("run_count"),
            func.coalesce(func.avg(AgentRun.total_cost_usd), Decimal(0)).label("avg_cost_usd"),
            func.coalesce(func.avg(AgentRun.total_input_tokens), Decimal(0)).label(
                "avg_input_tokens"
            ),
            func.coalesce(func.avg(AgentRun.total_output_tokens), Decimal(0)).label(
                "avg_output_tokens"
            ),
            func.avg(func.extract("epoch", AgentRun.ended_at - AgentRun.started_at) * 1000).label(
                "avg_latency_ms"
            ),
        ).where(
            AgentRun.workspace_id == workspace.id,
            AgentRun.deployment_version == version,
            AgentRun.started_at >= t_from,
            AgentRun.started_at < t_to,
        )

    def _span_costs_stmt(version: str) -> Any:
        return (
            select(
                Span.span_type,
                func.coalesce(func.sum(Span.cost_usd), Decimal(0)).label("cost_usd"),
            )
            .join(AgentRun, AgentRun.id == Span.run_id)
            .where(
                AgentRun.workspace_id == workspace.id,
                AgentRun.deployment_version == version,
                AgentRun.started_at >= t_from,
                AgentRun.started_at < t_to,
            )
            .group_by(Span.span_type)
        )

    base_result = await db.execute(_run_stats_stmt(baseline_version))
    base_row = base_result.one()

    cmp_result = await db.execute(_run_stats_stmt(comparison_version))
    cmp_row = cmp_result.one()

    base_span_result = await db.execute(_span_costs_stmt(baseline_version))
    base_span_rows = base_span_result.all()

    cmp_span_result = await db.execute(_span_costs_stmt(comparison_version))
    cmp_span_rows = cmp_span_result.all()

    def _delta(cmp_val: Decimal, base_val: Decimal) -> Decimal | None:
        if not base_val or base_val == Decimal(0):
            return None
        return (cmp_val - base_val) / base_val * Decimal(100)

    base_summary = VersionSummary(
        version=baseline_version,
        run_count=base_row.run_count,
        avg_cost_usd=base_row.avg_cost_usd,
        avg_input_tokens=base_row.avg_input_tokens,
        avg_output_tokens=base_row.avg_output_tokens,
        avg_latency_ms=base_row.avg_latency_ms,
    )
    cmp_summary = VersionSummary(
        version=comparison_version,
        run_count=cmp_row.run_count,
        avg_cost_usd=cmp_row.avg_cost_usd,
        avg_input_tokens=cmp_row.avg_input_tokens,
        avg_output_tokens=cmp_row.avg_output_tokens,
        avg_latency_ms=cmp_row.avg_latency_ms,
    )

    # Build span-type delta map
    base_span_map = {str(r.span_type): r.cost_usd for r in base_span_rows}
    cmp_span_map = {str(r.span_type): r.cost_usd for r in cmp_span_rows}
    all_span_types = sorted(set(base_span_map) | set(cmp_span_map))
    by_span_type = [
        SpanTypeDelta(
            span_type=st,
            baseline_cost=base_span_map.get(st, Decimal(0)),
            comparison_cost=cmp_span_map.get(st, Decimal(0)),
            delta_pct=_delta(cmp_span_map.get(st, Decimal(0)), base_span_map.get(st, Decimal(0))),
        )
        for st in all_span_types
    ]

    base_latency = Decimal(str(base_row.avg_latency_ms)) if base_row.avg_latency_ms else None
    cmp_latency = Decimal(str(cmp_row.avg_latency_ms)) if cmp_row.avg_latency_ms else None

    return VersionCompareResult(
        baseline=base_summary,
        comparison=cmp_summary,
        cost_delta_pct=_delta(cmp_row.avg_cost_usd, base_row.avg_cost_usd),
        token_delta_pct=_delta(cmp_row.avg_input_tokens, base_row.avg_input_tokens),
        latency_delta_pct=(
            _delta(cmp_latency, base_latency) if base_latency and cmp_latency else None
        ),
        by_span_type=by_span_type,
    )


# ── /analytics/regressions ────────────────────────────────────────────────────

_REGRESSION_THRESHOLD = Decimal("0.20")
_REGRESSION_MIN_RUNS = 3


@router.get("/regressions", response_model=RegressionList)
async def regressions(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
) -> RegressionList:
    """Detect feature workflows where avg cost jumped >20% vs prior week."""
    t_to = _parse_dt(to_dt, _default_to())
    t_from = _parse_dt(from_dt, _default_from())
    duration = t_to - t_from
    prior_from = t_from - duration
    prior_to = t_from

    def _window_stmt(w_from: object, w_to: object) -> Any:
        return (
            select(
                AgentRun.feature_tag,
                func.avg(AgentRun.total_cost_usd).label("avg_cost"),
                func.count(AgentRun.id).label("run_count"),
            )
            .where(
                AgentRun.workspace_id == workspace.id,
                AgentRun.started_at >= w_from,
                AgentRun.started_at < w_to,
                AgentRun.total_cost_usd.is_not(None),
            )
            .group_by(AgentRun.feature_tag)
        )

    curr_result = await db.execute(_window_stmt(t_from, t_to))
    curr_rows = curr_result.all()

    prior_result = await db.execute(_window_stmt(prior_from, prior_to))
    prior_rows = prior_result.all()

    prior_map: dict[str | None, tuple[Decimal, int]] = {
        row.feature_tag: (row.avg_cost, row.run_count) for row in prior_rows
    }

    items: list[RegressionItem] = []
    for row in curr_rows:
        if row.run_count < _REGRESSION_MIN_RUNS:
            continue
        prior = prior_map.get(row.feature_tag)
        if prior is None:
            continue
        prior_avg, prior_run_count = prior
        if not prior_avg or prior_avg == Decimal(0):
            continue
        curr_avg = Decimal(str(row.avg_cost))
        change = (curr_avg - prior_avg) / prior_avg
        if change > _REGRESSION_THRESHOLD:
            items.append(
                RegressionItem(
                    feature_tag=row.feature_tag,
                    current_avg_cost=curr_avg,
                    prior_avg_cost=prior_avg,
                    change_pct=change * Decimal(100),
                    run_count=row.run_count,
                    prior_run_count=prior_run_count,
                )
            )

    return RegressionList(
        items=items,
        from_dt=t_from.isoformat(),
        to_dt=t_to.isoformat(),
    )


# ── /analytics/annotations ────────────────────────────────────────────────────


@router.post("/annotations", response_model=AnnotationResponse, status_code=201)
async def create_annotation(
    body: AnnotationCreate,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AnnotationResponse:
    """Create a team annotation anchored to a date (and optionally a version)."""
    annotation = Annotation(
        workspace_id=workspace.id,
        note=body.note,
        annotation_date=body.annotation_date,
        version=body.version,
    )
    db.add(annotation)
    await db.commit()
    await db.refresh(annotation)
    return AnnotationResponse(
        id=str(annotation.id),
        note=annotation.note,
        annotation_date=annotation.annotation_date,
        version=annotation.version,
        created_at=annotation.created_at,
    )


@router.get("/annotations", response_model=AnnotationList)
async def list_annotations(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
    version: Annotated[str | None, Query()] = None,
) -> AnnotationList:
    """List annotations for the workspace, optionally filtered by date range or version."""
    stmt = (
        select(Annotation)
        .where(Annotation.workspace_id == workspace.id)
        .order_by(Annotation.annotation_date.desc())
    )
    if from_dt:
        stmt = stmt.where(Annotation.annotation_date >= _parse_dt(from_dt, _default_from()).date())
    if to_dt:
        stmt = stmt.where(Annotation.annotation_date <= _parse_dt(to_dt, _default_to()).date())
    if version:
        stmt = stmt.where(Annotation.version == version)

    result = await db.execute(stmt)
    rows = result.scalars().all()

    return AnnotationList(
        items=[
            AnnotationResponse(
                id=str(row.id),
                note=row.note,
                annotation_date=row.annotation_date,
                version=row.version,
                created_at=row.created_at,
            )
            for row in rows
        ]
    )


# ── /analytics/export ─────────────────────────────────────────────────────────

_EXPORT_COLUMNS = [
    "date",
    "provider",
    "model",
    "cost_usd",
    "input_tokens",
    "output_tokens",
    "call_count",
]


@router.get("/export", response_model=None)
async def analytics_export(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    format: Annotated[str, Query(pattern="^(csv|json)$")] = "json",
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
) -> StreamingResponse | dict[str, Any]:
    """Bulk export of daily spend data from usage_daily, ordered by date desc."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())

    stmt = (
        select(UsageDaily)
        .where(
            UsageDaily.workspace_id == workspace.id,
            UsageDaily.day >= t_from.date(),
            UsageDaily.day <= t_to.date(),
        )
        .order_by(UsageDaily.day.desc())
    )

    result = await db.execute(stmt)
    rows = result.scalars().all()

    items = [
        {
            "date": str(row.day),
            "provider": row.provider,
            "model": row.model,
            "cost_usd": str(row.cost_usd),
            "input_tokens": row.input_tokens,
            "output_tokens": row.output_tokens,
            "call_count": row.call_count,
        }
        for row in rows
    ]

    if format == "csv":
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=_EXPORT_COLUMNS)
        writer.writeheader()
        writer.writerows(items)
        buf.seek(0)

        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=analytics_export.csv"},
        )

    return {"items": items}


# ── /analytics/email-report ───────────────────────────────────────────────────


@router.post("/email-report", response_model=None, dependencies=[Depends(analytics_rate_limit)])
async def email_analytics_report(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    window_days: Annotated[int, Query(ge=1, le=365)] = 7,
) -> dict[str, Any]:
    """Email a usage analytics report to all workspace admins."""
    from runledger_api.services.email import send_analytics_report_email  # noqa: PLC0415
    from runledger_api.services.email_utils import get_workspace_admin_users  # noqa: PLC0415

    t_to = _default_to()
    t_from = t_to - timedelta(days=window_days)

    stmt = (
        select(UsageDaily)
        .where(
            UsageDaily.workspace_id == workspace.id,
            UsageDaily.day >= t_from.date(),
            UsageDaily.day <= t_to.date(),
        )
        .order_by(UsageDaily.day.desc())
    )
    result = await db.execute(stmt)
    rows_orm = result.scalars().all()

    items = [
        {
            "date": str(row.day),
            "provider": row.provider,
            "model": row.model,
            "cost_usd": str(row.cost_usd),
            "input_tokens": row.input_tokens,
            "output_tokens": row.output_tokens,
            "call_count": row.call_count,
        }
        for row in rows_orm
    ]

    total_cost = str(round(sum((float(str(r["cost_usd"])) for r in items), 0.0), 6))
    period_label = f"Last {window_days} days"
    ws_name = getattr(workspace, "name", str(workspace.id))

    admins = await get_workspace_admin_users(db, workspace.id)
    for u in admins:
        await send_analytics_report_email(
            to_email=u.email,
            full_name=u.full_name,
            period_label=period_label,
            rows=items,
            total_cost=total_cost,
            workspace_name=ws_name,
        )

    return {"queued": True, "recipients": len(admins)}


# ── /analytics/scores/summary ─────────────────────────────────────────────────

_SCORE_REGRESSION_THRESHOLD = Decimal("0.20")
_SCORE_REGRESSION_MIN_SAMPLES = 3


@router.get("/scores/summary", response_model=ScoreSummary)
async def score_summary(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
) -> ScoreSummary:
    """Average score values per score name for the current window vs prior window."""
    t_to = _parse_dt(to_dt, _default_to())
    t_from = _parse_dt(from_dt, _default_from())
    duration = t_to - t_from
    prior_from = t_from - duration
    prior_to = t_from

    def _score_window_stmt(w_from: object, w_to: object) -> Any:
        return (
            select(
                ScoreEvent.name,
                func.avg(ScoreEvent.value).label("avg_value"),
                func.count(ScoreEvent.id).label("sample_count"),
            )
            .where(
                ScoreEvent.workspace_id == workspace.id,
                ScoreEvent.created_at >= w_from,
                ScoreEvent.created_at < w_to,
            )
            .group_by(ScoreEvent.name)
        )

    curr_result = await db.execute(_score_window_stmt(t_from, t_to))
    curr_rows = curr_result.all()

    prior_result = await db.execute(_score_window_stmt(prior_from, prior_to))
    prior_rows = prior_result.all()

    prior_map: dict[str, tuple[Decimal, int]] = {
        row.name: (Decimal(str(row.avg_value)), row.sample_count) for row in prior_rows
    }

    items: list[ScoreSummaryItem] = []
    for row in curr_rows:
        curr_avg = Decimal(str(row.avg_value))
        prior = prior_map.get(row.name)
        prev_avg: Decimal | None = None
        change_pct: Decimal | None = None
        if prior is not None:
            prev_avg, prior_count = prior
            if prior_count > 0 and prev_avg and prev_avg != Decimal(0):
                change_pct = (curr_avg - prev_avg) / prev_avg * Decimal(100)

        items.append(
            ScoreSummaryItem(
                name=row.name,
                avg_value=curr_avg,
                p50=None,
                p90=None,
                sample_count=row.sample_count,
                prev_avg_value=prev_avg,
                change_pct=change_pct,
            )
        )

    return ScoreSummary(items=items)


# ── /analytics/scores/regressions ─────────────────────────────────────────────


@router.get("/scores/regressions", response_model=list[ScoreRegressionItem])
async def score_regressions(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
) -> list[ScoreRegressionItem]:
    """Detect score names where avg value dropped >20% vs prior window (sample_count >= 3)."""
    t_to = _parse_dt(to_dt, _default_to())
    t_from = _parse_dt(from_dt, _default_from())
    duration = t_to - t_from
    prior_from = t_from - duration
    prior_to = t_from

    def _score_window_stmt(w_from: object, w_to: object) -> Any:
        return (
            select(
                ScoreEvent.name,
                func.avg(ScoreEvent.value).label("avg_value"),
                func.count(ScoreEvent.id).label("sample_count"),
            )
            .where(
                ScoreEvent.workspace_id == workspace.id,
                ScoreEvent.created_at >= w_from,
                ScoreEvent.created_at < w_to,
            )
            .group_by(ScoreEvent.name)
        )

    curr_result = await db.execute(_score_window_stmt(t_from, t_to))
    curr_rows = curr_result.all()

    prior_result = await db.execute(_score_window_stmt(prior_from, prior_to))
    prior_rows = prior_result.all()

    prior_map: dict[str, Decimal] = {row.name: Decimal(str(row.avg_value)) for row in prior_rows}

    regressions: list[ScoreRegressionItem] = []
    for row in curr_rows:
        if row.sample_count < _SCORE_REGRESSION_MIN_SAMPLES:
            continue
        prior_avg = prior_map.get(row.name)
        if prior_avg is None or prior_avg == Decimal(0):
            continue
        curr_avg = Decimal(str(row.avg_value))
        change = (curr_avg - prior_avg) / prior_avg
        # Negative change means degradation; threshold is >20% drop
        if change < -_SCORE_REGRESSION_THRESHOLD:
            regressions.append(
                ScoreRegressionItem(
                    name=row.name,
                    current_avg=curr_avg,
                    prior_avg=prior_avg,
                    change_pct=change * Decimal(100),
                    sample_count=row.sample_count,
                )
            )

    return regressions


# ── Cost-quality analytics ─────────────────────────────────────────────────────


@router.get("/scores/cost-quality", response_model=CostQualityResponse)
async def cost_quality(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    score_name: Annotated[str | None, Query()] = None,
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
) -> CostQualityResponse:
    """
    Return avg cost vs avg score per model over the selected window.
    Joins agent_runs → provider_calls → score_events on run_id.
    """
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())

    from runledger_api.models.evaluators import Evaluator  # noqa: F401

    # Subquery: avg cost per run (from provider_calls)
    cost_sq = (
        select(
            ProviderCall.run_id.label("run_id"),
            ProviderCall.model.label("model"),
            func.sum(ProviderCall.cost_usd).label("run_cost"),
        )
        .where(
            ProviderCall.workspace_id == workspace.id,
            ProviderCall.created_at >= t_from,
            ProviderCall.created_at < t_to,
        )
        .group_by(ProviderCall.run_id, ProviderCall.model)
        .subquery()
    )

    # Subquery: avg score per run
    score_filter = [
        ScoreEvent.workspace_id == workspace.id,
        ScoreEvent.created_at >= t_from,
        ScoreEvent.created_at < t_to,
    ]
    if score_name:
        score_filter.append(ScoreEvent.name == score_name)

    score_sq = (
        select(
            ScoreEvent.run_id.label("run_id"),
            func.avg(ScoreEvent.value).label("avg_score"),
        )
        .where(*score_filter)
        .group_by(ScoreEvent.run_id)
        .subquery()
    )

    stmt = (
        select(
            cost_sq.c.model,
            func.avg(cost_sq.c.run_cost).label("avg_cost_usd"),
            func.avg(score_sq.c.avg_score).label("avg_score"),
            func.count(cost_sq.c.run_id.distinct()).label("run_count"),
        )
        .outerjoin(score_sq, cost_sq.c.run_id == score_sq.c.run_id)
        .group_by(cost_sq.c.model)
        .order_by(func.avg(cost_sq.c.run_cost).asc())
    )

    result = await db.execute(stmt)
    rows = result.all()

    items = [
        CostQualityPoint(
            model=row.model or "unknown",
            avg_cost_usd=str(round(Decimal(str(row.avg_cost_usd or 0)), 6)),
            avg_score=str(round(Decimal(str(row.avg_score)), 4))
            if row.avg_score is not None
            else None,
            run_count=row.run_count,
        )
        for row in rows
    ]
    return CostQualityResponse(items=items)


@router.get("/scores/best-value", response_model=BestValueResponse)
async def best_value_models(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    score_name: Annotated[str | None, Query()] = None,
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
    min_runs: Annotated[int, Query(ge=1)] = 3,
) -> BestValueResponse:
    """
    Return models ranked by quality/cost ratio (best value = high score, low cost).
    Excludes models with avg_cost_usd == 0 to avoid division by zero.
    """
    cq = await cost_quality(workspace, db, score_name, from_dt, to_dt)

    best: list[BestValueModel] = []
    for pt in cq.items:
        if pt.avg_score is None:
            continue
        avg_cost = float(pt.avg_cost_usd)
        avg_score = float(pt.avg_score)
        if avg_cost <= 0 or pt.run_count < min_runs:
            continue
        value_score = avg_score / avg_cost
        best.append(
            BestValueModel(
                model=pt.model,
                avg_cost_usd=pt.avg_cost_usd,
                avg_score=pt.avg_score,
                value_score=str(round(value_score, 4)),
                run_count=pt.run_count,
            )
        )

    best.sort(key=lambda x: float(x.value_score), reverse=True)
    return BestValueResponse(items=best)


# ── Phase 3: Scoped scope helpers ────────────────────────────────────────────

_ORG_ADMIN_ROLES = {"org_admin", "admin"}


async def _resolve_scoped_workspace_ids(
    scope: str,
    workspace: Workspace,
    user: Any,
    db: AsyncSession,
) -> list[uuid.UUID]:
    if scope == "workspace":
        return [workspace.id]

    if user is None:
        raise HTTPException(
            http_status.HTTP_403_FORBIDDEN,
            "User session required for org/platform scope",
        )

    if scope == "org":
        if not user.is_platform_admin:
            tu = (
                await db.execute(
                    select(TenantUser).where(
                        TenantUser.user_id == user.id,
                        TenantUser.tenant_id == workspace.tenant_id,
                    )
                )
            ).scalar_one_or_none()
            if tu is None or tu.role not in _ORG_ADMIN_ROLES:
                raise HTTPException(
                    http_status.HTTP_403_FORBIDDEN,
                    "Org admin access required for org scope",
                )
        result = await db.execute(
            select(Workspace.id).where(Workspace.tenant_id == workspace.tenant_id)
        )
        return list(result.scalars().all())

    if scope == "platform":
        if not user.is_platform_admin:
            raise HTTPException(
                http_status.HTTP_403_FORBIDDEN,
                "Platform admin access required for platform scope",
            )
        result = await db.execute(select(Workspace.id))
        return list(result.scalars().all())

    raise HTTPException(http_status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid scope")


# ── Phase 3: Scoped summary ─────────────────────────────────────────────────


@router.get("/scoped-summary", response_model=ScopedSummary)
async def scoped_summary(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    user: Annotated[Any, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    scope: Annotated[str, Query(pattern="^(workspace|org|platform)$")] = "workspace",
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
) -> ScopedSummary:
    """Summary with workspace/org/platform scope, including savings, intents, and top models."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())
    ws_ids = await _resolve_scoped_workspace_ids(scope, workspace, user, db)
    duration = t_to - t_from

    base_filter = [
        ProviderCall.workspace_id.in_(ws_ids),
        ProviderCall.created_at >= t_from,
        ProviderCall.created_at < t_to,
        ProviderCall.status == "success",
    ]

    agg = await db.execute(
        select(
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost"),
            func.coalesce(func.sum(ProviderCall.savings_usd), Decimal(0)).label("savings"),
            func.coalesce(func.sum(ProviderCall.input_tokens), 0).label("inp"),
            func.coalesce(func.sum(ProviderCall.output_tokens), 0).label("out"),
            func.count(ProviderCall.run_id.distinct()).label("runs"),
            func.count(ProviderCall.id).label("calls"),
            func.count(ProviderCall.end_user_id.distinct()).label("users"),
        ).where(*base_filter)
    )
    row = agg.one()

    prev_agg = await db.execute(
        select(
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost"),
        ).where(
            ProviderCall.workspace_id.in_(ws_ids),
            ProviderCall.created_at >= t_from - duration,
            ProviderCall.created_at < t_from,
            ProviderCall.status == "success",
        )
    )
    prev_cost = prev_agg.scalar_one()
    cost_delta = None
    if prev_cost and prev_cost > 0:
        cost_delta = (row.cost - prev_cost) / prev_cost * Decimal(100)

    intent_rows = (
        await db.execute(
            select(
                AgentRun.intent,
                func.count(AgentRun.id).label("cnt"),
                func.coalesce(func.sum(AgentRun.total_cost_usd), Decimal(0)).label("cost"),
            )
            .where(
                AgentRun.workspace_id.in_(ws_ids),
                AgentRun.started_at >= t_from,
                AgentRun.started_at < t_to,
                AgentRun.intent.isnot(None),
            )
            .group_by(AgentRun.intent)
            .order_by(func.count(AgentRun.id).desc())
            .limit(10)
        )
    ).all()

    model_rows = (
        await db.execute(
            select(
                ProviderCall.provider,
                ProviderCall.model,
                func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost"),
                func.coalesce(func.sum(ProviderCall.input_tokens), 0).label("inp"),
                func.coalesce(func.sum(ProviderCall.output_tokens), 0).label("out"),
                func.count(ProviderCall.id).label("calls"),
            )
            .where(*base_filter)
            .group_by(ProviderCall.provider, ProviderCall.model)
            .order_by(func.sum(ProviderCall.cost_usd).desc())
            .limit(10)
        )
    ).all()

    return ScopedSummary(
        scope=scope,
        total_cost_usd=row.cost,
        total_savings_usd=row.savings,
        total_input_tokens=row.inp,
        total_output_tokens=row.out,
        run_count=row.runs,
        call_count=row.calls,
        workspace_count=len(ws_ids),
        active_users=row.users,
        avg_cost_per_run=row.cost / row.runs if row.runs > 0 else None,
        top_intents=[
            IntentCount(intent=r.intent, count=r.cnt, cost_usd=r.cost)
            for r in intent_rows
        ],
        top_models=[
            ModelSpend(
                provider=r.provider,
                model=r.model,
                cost_usd=r.cost,
                input_tokens=r.inp,
                output_tokens=r.out,
                call_count=r.calls,
            )
            for r in model_rows
        ],
        cost_delta_pct=cost_delta,
    )


# ── Phase 3: Savings analytics ──────────────────────────────────────────────


@router.get("/savings", response_model=SavingsResponse)
async def savings_analytics(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
) -> SavingsResponse:
    """Savings breakdown by category and over time."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())

    base = [
        ProviderCall.workspace_id == workspace.id,
        ProviderCall.created_at >= t_from,
        ProviderCall.created_at < t_to,
        ProviderCall.status == "success",
    ]

    totals = (
        await db.execute(
            select(
                func.coalesce(func.sum(ProviderCall.savings_usd), Decimal(0)).label("savings"),
                func.coalesce(func.sum(ProviderCall.baseline_cost_usd), Decimal(0)).label("baseline"),
                func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("actual"),
            ).where(*base)
        )
    ).one()

    by_cat = (
        await db.execute(
            select(
                ProviderCall.savings_category,
                func.coalesce(func.sum(ProviderCall.savings_usd), Decimal(0)).label("savings"),
                func.count(ProviderCall.id).label("calls"),
            )
            .where(*base, ProviderCall.savings_category.isnot(None))
            .group_by(ProviderCall.savings_category)
            .order_by(func.sum(ProviderCall.savings_usd).desc())
        )
    ).all()

    timeline = (
        await db.execute(
            select(
                func.date_trunc("day", ProviderCall.created_at).label("day"),
                func.coalesce(func.sum(ProviderCall.savings_usd), Decimal(0)).label("savings"),
                func.coalesce(func.sum(ProviderCall.baseline_cost_usd), Decimal(0)).label("baseline"),
                func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("actual"),
            )
            .where(*base)
            .group_by(func.date_trunc("day", ProviderCall.created_at))
            .order_by(func.date_trunc("day", ProviderCall.created_at))
        )
    ).all()

    savings_rate = None
    if totals.baseline > 0:
        savings_rate = totals.savings / totals.baseline * Decimal(100)

    return SavingsResponse(
        total_savings_usd=totals.savings,
        total_baseline_usd=totals.baseline,
        total_actual_usd=totals.actual,
        savings_rate_pct=savings_rate,
        by_category=[
            SavingsByCategory(category=r.savings_category, savings_usd=r.savings, call_count=r.calls)
            for r in by_cat
        ],
        timeline=[
            SavingsTimeline(
                period=str(r.day),
                savings_usd=r.savings,
                baseline_cost_usd=r.baseline,
                actual_cost_usd=r.actual,
            )
            for r in timeline
        ],
    )


# ── Phase 3: Optimization opportunities ─────────────────────────────────────


@router.get("/optimization-opportunities", response_model=OptimizationOpportunitiesResponse)
async def optimization_opportunities(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
) -> OptimizationOpportunitiesResponse:
    """Identify cost optimization opportunities from request patterns."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())

    base = [
        ProviderCall.workspace_id == workspace.id,
        ProviderCall.created_at >= t_from,
        ProviderCall.created_at < t_to,
        ProviderCall.status == "success",
    ]

    opportunities: list[OptimizationOpportunity] = []

    # 1) Calls without any optimization — estimate 15% potential savings via caching/routing
    unopt_row = (
        await db.execute(
            select(
                func.count(ProviderCall.id).label("calls"),
                func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost"),
            ).where(*base, ProviderCall.optimization_applied.is_(None))
        )
    ).one()
    if unopt_row.calls > 0:
        potential = unopt_row.cost * Decimal("0.15")
        opportunities.append(
            OptimizationOpportunity(
                optimization_type="unoptimized_requests",
                potential_savings_usd=potential,
                affected_calls=unopt_row.calls,
                description=f"{unopt_row.calls} calls have no optimization applied — caching or model routing could save ~15%",
            )
        )

    # 2) High-cost models that could be downgraded for simple intents
    expensive = (
        await db.execute(
            select(
                ProviderCall.model,
                func.count(ProviderCall.id).label("calls"),
                func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost"),
            )
            .where(*base)
            .group_by(ProviderCall.model)
            .having(func.avg(ProviderCall.cost_usd) > Decimal("0.01"))
            .order_by(func.sum(ProviderCall.cost_usd).desc())
            .limit(5)
        )
    ).all()
    for row in expensive:
        potential = row.cost * Decimal("0.30")
        opportunities.append(
            OptimizationOpportunity(
                optimization_type="model_downgrade",
                potential_savings_usd=potential,
                affected_calls=row.calls,
                description=f"Model '{row.model}' averaging >$0.01/call — routing simple tasks to a smaller model could save ~30%",
            )
        )

    # 3) Repeated similar prompts that could benefit from caching
    cache_row = (
        await db.execute(
            select(
                func.count(ProviderCall.id).label("calls"),
                func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost"),
            ).where(
                *base,
                ProviderCall.cached_input_tokens.is_(None),
                ProviderCall.input_tokens > 1000,
            )
        )
    ).one()
    if cache_row.calls > 10:
        potential = cache_row.cost * Decimal("0.20")
        opportunities.append(
            OptimizationOpportunity(
                optimization_type="prompt_caching",
                potential_savings_usd=potential,
                affected_calls=cache_row.calls,
                description=f"{cache_row.calls} calls with >1K input tokens and no cache hits — prompt caching could save ~20%",
            )
        )

    total_potential = sum(o.potential_savings_usd for o in opportunities)
    return OptimizationOpportunitiesResponse(
        items=opportunities, total_potential_savings_usd=total_potential
    )


# ── Phase 3: Trends ─────────────────────────────────────────────────────────


@router.get("/trends", response_model=TrendsResponse)
async def trends(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    granularity: Annotated[str, Query(pattern="^(hourly|daily|weekly)$")] = "daily",
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
) -> TrendsResponse:
    """Cost, usage, and savings trends over time with period-over-period comparison."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())
    duration = t_to - t_from

    trunc = {"hourly": "hour", "daily": "day", "weekly": "week"}[granularity]

    base = [
        ProviderCall.workspace_id == workspace.id,
        ProviderCall.created_at >= t_from,
        ProviderCall.created_at < t_to,
        ProviderCall.status == "success",
    ]

    rows = (
        await db.execute(
            select(
                func.date_trunc(trunc, ProviderCall.created_at).label("period"),
                func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost"),
                func.count(ProviderCall.run_id.distinct()).label("runs"),
                func.count(ProviderCall.id).label("calls"),
                func.coalesce(
                    func.sum(ProviderCall.input_tokens) + func.sum(ProviderCall.output_tokens), 0
                ).label("tokens"),
                func.avg(ProviderCall.latency_ms).label("latency"),
                func.coalesce(func.sum(ProviderCall.savings_usd), Decimal(0)).label("savings"),
            )
            .where(*base)
            .group_by(func.date_trunc(trunc, ProviderCall.created_at))
            .order_by(func.date_trunc(trunc, ProviderCall.created_at))
        )
    ).all()

    # Current and previous period totals for metrics
    cur = await db.execute(
        select(
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost"),
            func.count(ProviderCall.run_id.distinct()).label("runs"),
            func.count(ProviderCall.id).label("calls"),
            func.coalesce(func.sum(ProviderCall.savings_usd), Decimal(0)).label("savings"),
        ).where(*base)
    )
    cur_row = cur.one()

    prev = await db.execute(
        select(
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost"),
            func.count(ProviderCall.run_id.distinct()).label("runs"),
            func.count(ProviderCall.id).label("calls"),
            func.coalesce(func.sum(ProviderCall.savings_usd), Decimal(0)).label("savings"),
        ).where(
            ProviderCall.workspace_id == workspace.id,
            ProviderCall.created_at >= t_from - duration,
            ProviderCall.created_at < t_from,
            ProviderCall.status == "success",
        )
    )
    prev_row = prev.one()

    def _pct(cur_val: Decimal, prev_val: Decimal) -> Decimal | None:
        if prev_val and prev_val > 0:
            return (cur_val - prev_val) / prev_val * Decimal(100)
        return None

    return TrendsResponse(
        points=[
            TrendPoint(
                period=str(r.period),
                cost_usd=r.cost,
                run_count=r.runs,
                call_count=r.calls,
                tokens=r.tokens,
                avg_latency_ms=Decimal(str(round(r.latency, 1))) if r.latency else None,
                savings_usd=r.savings,
            )
            for r in rows
        ],
        metrics=[
            TrendMetric(name="cost_usd", current=cur_row.cost, previous=prev_row.cost, change_pct=_pct(cur_row.cost, prev_row.cost)),
            TrendMetric(name="run_count", current=Decimal(cur_row.runs), previous=Decimal(prev_row.runs), change_pct=_pct(Decimal(cur_row.runs), Decimal(prev_row.runs))),
            TrendMetric(name="call_count", current=Decimal(cur_row.calls), previous=Decimal(prev_row.calls), change_pct=_pct(Decimal(cur_row.calls), Decimal(prev_row.calls))),
            TrendMetric(name="savings_usd", current=cur_row.savings, previous=prev_row.savings, change_pct=_pct(cur_row.savings, prev_row.savings)),
        ],
        granularity=granularity,
    )


# ── Phase 3: Request explorer ───────────────────────────────────────────────


@router.get("/request-explorer", response_model=RequestExplorerResponse)
async def request_explorer(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
    model: Annotated[str | None, Query()] = None,
    provider: Annotated[str | None, Query()] = None,
    intent: Annotated[str | None, Query()] = None,
    optimization: Annotated[str | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> RequestExplorerResponse:
    """Paginated request explorer with filtering by model, provider, intent, and optimization."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())

    filters = [
        ProviderCall.workspace_id == workspace.id,
        ProviderCall.created_at >= t_from,
        ProviderCall.created_at < t_to,
    ]
    if model:
        filters.append(ProviderCall.model == model)
    if provider:
        filters.append(ProviderCall.provider == provider)
    if optimization:
        filters.append(ProviderCall.optimization_applied == optimization)

    # Join with AgentRun for intent filtering
    query = (
        select(
            ProviderCall.id,
            ProviderCall.run_id,
            ProviderCall.provider,
            ProviderCall.model,
            AgentRun.intent,
            ProviderCall.cost_usd,
            ProviderCall.baseline_cost_usd,
            ProviderCall.savings_usd,
            ProviderCall.optimization_applied,
            ProviderCall.input_tokens,
            ProviderCall.output_tokens,
            ProviderCall.latency_ms,
            ProviderCall.status,
            ProviderCall.created_at,
        )
        .join(AgentRun, AgentRun.id == ProviderCall.run_id)
        .where(*filters)
    )
    if intent:
        query = query.where(AgentRun.intent == intent)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    rows = (
        await db.execute(
            query.order_by(ProviderCall.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()

    return RequestExplorerResponse(
        items=[
            RequestRecord(
                id=str(r.id),
                run_id=str(r.run_id),
                provider=r.provider,
                model=r.model,
                intent=r.intent,
                cost_usd=r.cost_usd,
                baseline_cost_usd=r.baseline_cost_usd,
                savings_usd=r.savings_usd,
                optimization_applied=r.optimization_applied,
                input_tokens=r.input_tokens,
                output_tokens=r.output_tokens,
                latency_ms=r.latency_ms,
                status=r.status,
                created_at=str(r.created_at),
            )
            for r in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


# ── Phase 8: Engineering metrics ─────────────────────────────────────────────


@router.get("/engineering", response_model=EngineeringMetrics)
async def engineering_metrics(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
) -> EngineeringMetrics:
    """Engineering dashboard: latency, errors, retries, cache, cost breakdowns, quality funnel."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())

    base = [
        ProviderCall.workspace_id == workspace.id,
        ProviderCall.created_at >= t_from,
        ProviderCall.created_at < t_to,
    ]

    # Core metrics
    agg = (
        await db.execute(
            select(
                func.count(ProviderCall.id).label("total"),
                func.avg(ProviderCall.latency_ms).label("avg_lat"),
                func.percentile_cont(0.95).within_group(ProviderCall.latency_ms).label("p95_lat"),
                func.count(case((ProviderCall.status == "error", 1))).label("errors"),
                func.coalesce(func.sum(ProviderCall.input_tokens), 0).label("inp"),
                func.coalesce(func.sum(ProviderCall.output_tokens), 0).label("out"),
                func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost"),
                func.count(case((ProviderCall.cached_input_tokens > 0, 1))).label("cached"),
            ).where(*base)
        )
    ).one()

    total = agg.total or 1
    total_tokens = agg.inp + agg.out

    # Retry count: spans with parent_span_id that are LLM type (re-attempts)
    retry_count = (
        await db.execute(
            select(func.count(Span.id)).where(
                Span.workspace_id == workspace.id,
                Span.started_at >= t_from,
                Span.started_at < t_to,
                Span.span_type == "llm",
                Span.parent_span_id.isnot(None),
            )
        )
    ).scalar_one()

    # Cost by feature_tag
    feature_rows = (
        await db.execute(
            select(
                AgentRun.feature_tag,
                func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost"),
                func.count(ProviderCall.id).label("calls"),
            )
            .join(AgentRun, AgentRun.id == ProviderCall.run_id)
            .where(*base)
            .group_by(AgentRun.feature_tag)
            .order_by(func.sum(ProviderCall.cost_usd).desc())
            .limit(10)
        )
    ).all()

    # Cost by model
    model_rows = (
        await db.execute(
            select(
                ProviderCall.model,
                func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost"),
                func.count(ProviderCall.id).label("calls"),
            )
            .where(*base)
            .group_by(ProviderCall.model)
            .order_by(func.sum(ProviderCall.cost_usd).desc())
            .limit(10)
        )
    ).all()

    # Cost by tool
    tool_rows = (
        await db.execute(
            select(
                ToolCall.tool_name,
                func.count(ToolCall.id).label("calls"),
            )
            .where(
                ToolCall.workspace_id == workspace.id,
                ToolCall.created_at >= t_from,
                ToolCall.created_at < t_to,
            )
            .group_by(ToolCall.tool_name)
            .order_by(func.count(ToolCall.id).desc())
            .limit(10)
        )
    ).all()

    # Quality funnel
    run_base = [
        AgentRun.workspace_id == workspace.id,
        AgentRun.started_at >= t_from,
        AgentRun.started_at < t_to,
    ]
    total_runs = (await db.execute(select(func.count(AgentRun.id)).where(*run_base))).scalar_one()
    succeeded_runs = (
        await db.execute(
            select(func.count(AgentRun.id)).where(*run_base, AgentRun.status == "succeeded")
        )
    ).scalar_one()

    # Gateway-routed count
    from runledger_api.models.gateway import GatewayRequest

    routed = (
        await db.execute(
            select(func.count(GatewayRequest.id)).where(
                GatewayRequest.workspace_id == workspace.id,
                GatewayRequest.created_at >= t_from,
                GatewayRequest.created_at < t_to,
            )
        )
    ).scalar_one()

    cache_hits = (
        await db.execute(
            select(func.count(GatewayRequest.id)).where(
                GatewayRequest.workspace_id == workspace.id,
                GatewayRequest.created_at >= t_from,
                GatewayRequest.created_at < t_to,
                GatewayRequest.cache_hit.is_(True),
            )
        )
    ).scalar_one()

    with_outcome = (
        await db.execute(
            select(func.count(OutcomeEvent.run_id.distinct())).where(
                OutcomeEvent.created_at >= t_from,
                OutcomeEvent.created_at < t_to,
            )
        )
    ).scalar_one()

    positive_outcome = (
        await db.execute(
            select(func.count(OutcomeEvent.id)).where(
                OutcomeEvent.created_at >= t_from,
                OutcomeEvent.created_at < t_to,
                OutcomeEvent.success.is_(True),
            )
        )
    ).scalar_one()

    # Lifecycle stages
    stages = [
        LifecycleStage(stage="Received", count=total_runs, pct=Decimal(100)),
        LifecycleStage(stage="Routed", count=routed, pct=Decimal(round(routed / total_runs * 100, 1)) if total_runs > 0 else Decimal(0)),
        LifecycleStage(stage="Cached", count=cache_hits, pct=Decimal(round(cache_hits / total_runs * 100, 1)) if total_runs > 0 else Decimal(0)),
        LifecycleStage(stage="Completed", count=succeeded_runs, pct=Decimal(round(succeeded_runs / total_runs * 100, 1)) if total_runs > 0 else Decimal(0)),
        LifecycleStage(stage="With outcome", count=with_outcome, pct=Decimal(round(with_outcome / total_runs * 100, 1)) if total_runs > 0 else Decimal(0)),
        LifecycleStage(stage="Positive", count=positive_outcome, pct=Decimal(round(positive_outcome / total_runs * 100, 1)) if total_runs > 0 else Decimal(0)),
    ]

    return EngineeringMetrics(
        avg_latency_ms=Decimal(str(round(agg.avg_lat, 1))) if agg.avg_lat else None,
        p95_latency_ms=Decimal(str(round(agg.p95_lat, 1))) if agg.p95_lat else None,
        error_pct=Decimal(str(round(agg.errors / total * 100, 2))),
        retry_pct=Decimal(str(round(retry_count / total * 100, 2))),
        cache_pct=Decimal(str(round(agg.cached / total * 100, 2))),
        total_requests=agg.total,
        total_tokens=total_tokens,
        avg_cost_per_request=agg.cost / agg.total if agg.total > 0 else None,
        cost_by_feature=[
            CostByDimension(name=r.feature_tag or "Untagged", cost_usd=r.cost, call_count=r.calls)
            for r in feature_rows
        ],
        cost_by_model=[
            CostByDimension(name=r.model, cost_usd=r.cost, call_count=r.calls)
            for r in model_rows
        ],
        cost_by_tool=[
            CostByDimension(name=r.tool_name, cost_usd=Decimal(0), call_count=r.calls)
            for r in tool_rows
        ],
        quality_funnel=QualityFunnel(
            total_requests=total_runs,
            successful=succeeded_runs,
            routed=routed,
            cached=cache_hits,
            with_outcome=with_outcome,
            positive_outcome=positive_outcome,
        ),
        lifecycle_stages=stages,
    )


# ── Optimization Simulator ────────────────────────────────────────────────────

MODEL_COST_RATIOS: dict[str, float] = {
    "gpt-4o": 1.0,
    "gpt-4o-mini": 0.15,
    "gpt-4.1": 1.0,
    "gpt-4.1-mini": 0.18,
    "gpt-4.1-nano": 0.05,
    "gpt-5": 2.5,
    "o3": 3.0,
    "o4-mini": 0.55,
    "claude-sonnet-4": 0.6,
    "claude-opus-4": 1.5,
    "claude-haiku-3.5": 0.08,
    "claude-3-haiku": 0.05,
    "gemini-2.5-pro": 0.5,
    "gemini-2.5-flash": 0.08,
    "deepseek-v3": 0.07,
    "deepseek-r1": 0.22,
    "llama-3.3-70b": 0.04,
    "llama-4-scout": 0.06,
    "llama-4-maverick": 0.12,
    "qwen-3-235b": 0.08,
    "local/ollama": 0.0,
}

MODEL_LATENCY_MS: dict[str, float] = {
    "gpt-4o": 800,
    "gpt-4o-mini": 400,
    "gpt-4.1": 900,
    "gpt-4.1-mini": 350,
    "gpt-4.1-nano": 180,
    "gpt-5": 1400,
    "o3": 5000,
    "o4-mini": 2000,
    "claude-sonnet-4": 700,
    "claude-opus-4": 1200,
    "claude-haiku-3.5": 250,
    "claude-3-haiku": 200,
    "gemini-2.5-pro": 600,
    "gemini-2.5-flash": 250,
    "deepseek-v3": 500,
    "deepseek-r1": 1800,
    "llama-3.3-70b": 300,
    "llama-4-scout": 280,
    "llama-4-maverick": 450,
    "qwen-3-235b": 600,
    "local/ollama": 600,
}

QUALITY_RISK_MAP: dict[str, str] = {
    "gpt-4o": "low",
    "gpt-4o-mini": "medium",
    "gpt-4.1": "low",
    "gpt-4.1-mini": "medium",
    "gpt-4.1-nano": "high",
    "gpt-5": "low",
    "o3": "low",
    "o4-mini": "low",
    "claude-sonnet-4": "low",
    "claude-opus-4": "low",
    "claude-haiku-3.5": "medium",
    "claude-3-haiku": "high",
    "gemini-2.5-pro": "low",
    "gemini-2.5-flash": "medium",
    "deepseek-v3": "medium",
    "deepseek-r1": "low",
    "llama-3.3-70b": "medium",
    "llama-4-scout": "medium",
    "llama-4-maverick": "low",
    "qwen-3-235b": "medium",
    "local/ollama": "high",
}


def _match_model_key(model_name: str | None) -> str | None:
    if not model_name:
        return None
    normalized = model_name.lower().strip()
    for key in MODEL_COST_RATIOS:
        if key in normalized or normalized in key:
            return key
    return None


@router.post("/simulate-optimization", response_model=SimulationResult)
async def simulate_optimization(
    body: SimulationRequest,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SimulationResult:
    """Simulate savings from a proposed route/model/cache/compression change."""
    t_from = _parse_dt(
        body.from_dt.isoformat() if body.from_dt else None,
        _default_from(),
    )
    t_to = _parse_dt(
        body.to_dt.isoformat() if body.to_dt else None,
        _default_to(),
    )

    filters = [
        ProviderCall.workspace_id == workspace.id,
        ProviderCall.created_at >= t_from,
        ProviderCall.created_at < t_to,
    ]
    if body.intent:
        run_ids_q = select(AgentRun.id).where(
            AgentRun.workspace_id == workspace.id,
            AgentRun.intent == body.intent,
        )
        filters.append(ProviderCall.run_id.in_(run_ids_q))
    if body.current_model:
        filters.append(func.lower(ProviderCall.model).contains(body.current_model.lower()))
    if body.current_provider:
        filters.append(func.lower(ProviderCall.provider).contains(body.current_provider.lower()))

    q = select(
        func.count().label("total"),
        func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost"),
        func.avg(ProviderCall.latency_ms).label("avg_lat"),
        func.sum(ProviderCall.input_tokens).label("in_tok"),
        func.sum(ProviderCall.output_tokens).label("out_tok"),
        func.sum(
            case((ProviderCall.cached_input_tokens > 0, 1), else_=0)
        ).label("cached"),
    ).where(*filters)

    row = (await db.execute(q)).one()

    affected = row.total or 0
    current_cost = Decimal(str(row.cost or 0))
    current_lat = float(row.avg_lat) if row.avg_lat else None
    cached_count = row.cached or 0

    if affected == 0:
        return SimulationResult(
            affected_requests=0,
            current_cost_usd=Decimal(0),
            projected_cost_usd=Decimal(0),
            projected_savings_usd=Decimal(0),
            savings_pct=Decimal(0),
            current_avg_latency_ms=None,
            projected_latency_ms=None,
            latency_delta_pct=None,
            quality_risk="unknown",
            confidence="low",
            impacts=[],
            description="No matching requests found for the given filters.",
        )

    current_key = _match_model_key(body.current_model)
    proposed_key = _match_model_key(body.proposed_model)

    model_cost_ratio = Decimal(1)
    if current_key and proposed_key:
        cur_ratio = MODEL_COST_RATIOS.get(current_key, 1.0)
        new_ratio = MODEL_COST_RATIOS.get(proposed_key, 1.0)
        if cur_ratio > 0:
            model_cost_ratio = Decimal(str(round(new_ratio / cur_ratio, 4)))

    cache_savings_pct = Decimal(0)
    if body.enable_cache:
        current_cache_rate = cached_count / affected if affected > 0 else 0
        target_cache_rate = max(current_cache_rate, 0.40)
        cache_savings_pct = Decimal(str(round((target_cache_rate - current_cache_rate) * 0.50, 4)))

    compression_pct = Decimal("0.15") if body.enable_compression else Decimal(0)

    projected_cost = current_cost * model_cost_ratio * (1 - cache_savings_pct) * (1 - compression_pct)
    projected_savings = current_cost - projected_cost
    savings_pct = (projected_savings / current_cost * 100) if current_cost > 0 else Decimal(0)

    proposed_lat = None
    lat_delta = None
    if current_lat and proposed_key:
        proposed_lat_est = MODEL_LATENCY_MS.get(proposed_key)
        if proposed_lat_est:
            proposed_lat = Decimal(str(round(proposed_lat_est, 1)))
            if current_lat > 0:
                lat_delta = Decimal(str(round((proposed_lat_est - current_lat) / current_lat * 100, 1)))

    quality_risk = "low"
    if proposed_key:
        quality_risk = QUALITY_RISK_MAP.get(proposed_key, "medium")

    confidence = "high" if affected >= 100 else "medium" if affected >= 20 else "directional"

    impacts: list[SimulationImpact] = []
    if body.proposed_model and body.current_model:
        impacts.append(SimulationImpact(
            label="Model change",
            current_value=body.current_model,
            projected_value=body.proposed_model,
            delta_pct=Decimal(str(round((float(model_cost_ratio) - 1) * 100, 1))),
        ))
    if body.enable_cache:
        impacts.append(SimulationImpact(
            label="Cache policy",
            current_value=f"{round(cached_count / affected * 100)}% hit rate" if affected > 0 else "0%",
            projected_value=f"~{round(float(cache_savings_pct) * 100 + cached_count / affected * 100)}% hit rate" if affected > 0 else "40%",
            delta_pct=Decimal(str(round(float(cache_savings_pct) * -100, 1))),
        ))
    if body.enable_compression:
        impacts.append(SimulationImpact(
            label="Prompt compression",
            current_value="Disabled",
            projected_value="Enabled (~15% token reduction)",
            delta_pct=Decimal("-15"),
        ))

    parts: list[str] = []
    if body.proposed_model:
        parts.append(f"route from {body.current_model or 'current'} to {body.proposed_model}")
    if body.enable_cache:
        parts.append("enable caching")
    if body.enable_compression:
        parts.append("enable compression")
    desc = (
        f"Simulating: {', '.join(parts) or 'no changes'}. "
        f"Affects {affected:,} requests with ${float(current_cost):.4f} current spend. "
        f"Projected savings: ${float(projected_savings):.4f} ({float(savings_pct):.1f}%)."
    )

    return SimulationResult(
        affected_requests=affected,
        current_cost_usd=current_cost,
        projected_cost_usd=projected_cost,
        projected_savings_usd=projected_savings,
        savings_pct=savings_pct,
        current_avg_latency_ms=Decimal(str(round(current_lat, 1))) if current_lat else None,
        projected_latency_ms=proposed_lat,
        latency_delta_pct=lat_delta,
        quality_risk=quality_risk,
        confidence=confidence,
        impacts=impacts,
        description=desc,
    )


# ── Model Scorecards ────────────────────────────────────────────────────────


@router.get("/model-scorecards", response_model=ModelScorecardList)
async def model_scorecards(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
) -> ModelScorecardList:
    """Aggregate quality scorecards per model: cost, latency, errors, cache, quality."""
    now = datetime.now(UTC)
    start = datetime.fromisoformat(from_dt) if from_dt else now - timedelta(days=30)
    end = datetime.fromisoformat(to_dt) if to_dt else now

    filters = [
        ProviderCall.workspace_id == workspace.id,
        ProviderCall.created_at >= start,
        ProviderCall.created_at <= end,
    ]

    stmt = (
        select(
            ProviderCall.model,
            ProviderCall.provider,
            func.sum(ProviderCall.cost_usd).label("total_cost"),
            func.count().label("call_count"),
            func.avg(ProviderCall.cost_usd).label("avg_cost"),
            func.avg(ProviderCall.latency_ms).label("avg_latency"),
            func.percentile_cont(0.95).within_group(ProviderCall.latency_ms).label("p95_latency"),
            func.sum(case((ProviderCall.status == "failed", 1), else_=0)).label("error_count"),
            func.sum(ProviderCall.input_tokens).label("input_tokens"),
            func.sum(ProviderCall.output_tokens).label("output_tokens"),
        )
        .where(*filters)
        .group_by(ProviderCall.model, ProviderCall.provider)
        .order_by(func.sum(ProviderCall.cost_usd).desc().nulls_last())
    )

    rows = (await db.execute(stmt)).all()

    from runledger_api.models.gateway import GatewayRequest

    cache_stmt = (
        select(
            GatewayRequest.model_used,
            func.count().label("total"),
            func.sum(case((GatewayRequest.cache_hit.is_(True), 1), else_=0)).label("hits"),
        )
        .where(
            GatewayRequest.workspace_id == workspace.id,
            GatewayRequest.created_at >= start,
            GatewayRequest.created_at <= end,
        )
        .group_by(GatewayRequest.model_used)
    )
    cache_rows = {r.model_used: r for r in (await db.execute(cache_stmt)).all()}

    score_stmt = (
        select(
            ProviderCall.model,
            func.avg(ScoreEvent.value).label("avg_score"),
        )
        .join(ScoreEvent, ScoreEvent.run_id == ProviderCall.run_id)
        .where(
            ProviderCall.workspace_id == workspace.id,
            ProviderCall.created_at >= start,
            ProviderCall.created_at <= end,
        )
        .group_by(ProviderCall.model)
    )
    score_map = {r.model: r.avg_score for r in (await db.execute(score_stmt)).all()}

    items = []
    for r in rows:
        cache_info = cache_rows.get(r.model)
        cache_hit_rate = None
        if cache_info and cache_info.total > 0:
            cache_hit_rate = Decimal(str(round(cache_info.hits / cache_info.total * 100, 1)))

        avg_score = score_map.get(r.model)

        items.append(ModelScorecard(
            model=r.model,
            provider=r.provider,
            total_cost_usd=Decimal(str(r.total_cost or 0)),
            call_count=r.call_count,
            avg_cost_per_call=Decimal(str(round(float(r.avg_cost or 0), 6))),
            avg_latency_ms=Decimal(str(round(float(r.avg_latency or 0), 1))) if r.avg_latency else None,
            p95_latency_ms=Decimal(str(round(float(r.p95_latency or 0), 1))) if r.p95_latency else None,
            error_rate=Decimal(str(round(r.error_count / r.call_count * 100, 2))) if r.call_count > 0 else Decimal("0"),
            cache_hit_rate=cache_hit_rate,
            avg_quality_score=Decimal(str(round(float(avg_score), 2))) if avg_score else None,
            input_tokens=r.input_tokens or 0,
            output_tokens=r.output_tokens or 0,
        ))

    return ModelScorecardList(items=items, from_dt=start, to_dt=end)
