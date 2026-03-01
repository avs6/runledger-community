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
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace
from runledger_api.core.ratelimit import analytics_rate_limit
from runledger_api.models.annotations import Annotation
from runledger_api.models.events import AgentRun, ProviderCall, Span
from runledger_api.models.metering import UsageDaily
from runledger_api.models.replay import UserAnomaly
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.analytics import (
    AnalyticsSummary,
    AnomalyItem,
    AnomalyList,
    CohortList,
    CohortSummary,
    FeatureSpend,
    ModelSpend,
    SpendByFeature,
    SpendByModel,
    SpendByUser,
    SpendOverTime,
    SpendPoint,
    UserSpend,
    UserSpendDetail,
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
    granularity: Annotated[str, Query(pattern="^(hourly|daily)$")] = "daily",
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
) -> SpendOverTime:
    """Time-series of cost and token usage, bucketed by hour or day."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())

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
        from fastapi import HTTPException

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
