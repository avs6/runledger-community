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

import sqlalchemy as sa
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi import status as http_status
from fastapi.responses import StreamingResponse
from sqlalchemy import String, case, cast, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_user, get_current_workspace, require_platform_admin
from runledger_api.core.ratelimit import analytics_rate_limit
from runledger_api.models.access_groups import AccessGroup, AccessGroupMember
from runledger_api.models.agents import Agent, WorkflowDefinition, WorkflowRun
from runledger_api.models.alerts import AlertFiring, AlertRule
from runledger_api.models.annotations import Annotation
from runledger_api.models.approvals import Approval
from runledger_api.models.audit import AuditEvent
from runledger_api.models.billing import BillingPeriod, ChargebackRule
from runledger_api.models.budget_overrides import BudgetOverride
from runledger_api.models.budgets import Budget, BudgetBreach, BudgetNotification
from runledger_api.models.cache_config import ResponseCacheConfig
from runledger_api.models.eval_experiments import EvalDataset, EvalExperiment
from runledger_api.models.events import AgentRun, OutcomeEvent, ProviderCall, Span, ToolCall
from runledger_api.models.gateway import GatewayPassThroughEndpoint, GatewayRoute, RoutingPolicy
from runledger_api.models.guardrails import GuardrailEvent, GuardrailRule
from runledger_api.models.hub import HubModel
from runledger_api.models.ledger import CapturePolicy, LedgerSnapshot, SecurityEvent, ToolRegistry
from runledger_api.models.mcp_registry import McpServer, McpToolCall
from runledger_api.models.metering import ProviderPricing, UsageDaily
from runledger_api.models.model_budgets import ModelBudget
from runledger_api.models.otlp import OtlpIngestBatch
from runledger_api.models.prompts import Prompt
from runledger_api.models.replay import ReplayDataset, ReplayExperiment, UserAnomaly
from runledger_api.models.scores import ScoreEvent
from runledger_api.models.search_tools import SearchTool
from runledger_api.models.tags import Tag
from runledger_api.models.tenant import ApiKey, Tenant, TenantUser, Workspace, WorkspaceUser
from runledger_api.models.tool_policies import ToolPolicy
from runledger_api.schemas.analytics import (
    AnalyticsSummary,
    AnomalyItem,
    AnomalyList,
    CohortList,
    CohortSummary,
    CostByDimension,
    EconomicsFinopsPosture,
    EconomicsGatewayPosture,
    EngineeringMetrics,
    FeatureSpend,
    IntentCount,
    InvestigationFinopsBudgetPosture,
    InvestigationGatewayRuntimePosture,
    InvestigationGovernancePosture,
    InvestigationOrgIdentityPosture,
    LifecycleStage,
    ModelBudgetUtilization,
    ModelScorecard,
    ModelScorecardList,
    ModelSpend,
    ModelUsageGatewayPosture,
    MonitoringFinopsPosture,
    MonitoringOpsPosture,
    OptimizationOpportunitiesResponse,
    OptimizationOpportunity,
    OutcomesFinopsPosture,
    OverviewFinopsBudgetPosture,
    OverviewGatewayPosture,
    OverviewGovernancePosture,
    OverviewOrgPosture,
    OverviewScopePosture,
    QualityFunnel,
    RequestExplorerResponse,
    RequestRecord,
    SavingsByCategory,
    SavingsResponse,
    SavingsTimeline,
    ScopedSummary,
    SimulationImpact,
    SimulationRequest,
    SimulationResult,
    SpendByFeature,
    SpendByModel,
    SpendByUser,
    SpendOverTime,
    SpendPoint,
    TelemetryOpsPosture,
    ApprovalsAlertFinopsPosture,
    DataProtectionGatewayPosture,
    DataProtectionOrgPosture,
    EvidenceAuditCrossPosture,
    GovernanceInternalPosture,
    ExceptionWorkflowsGatewayPosture,
    ExceptionWorkflowsOrgPosture,
    TagsFinopsBudgetPosture,
    ToolGovernanceGatewayPosture,
    ToolGovernanceOrgPosture,
    ToolPoliciesRuntimePosture,
    ToolRegistryFinopsPosture,
    ToolRegistryRuntimePosture,
    ApprovalsRuntimePosture,
    DataCaptureRuntimePosture,
    SecurityRuntimePosture,
    AlertRulesRuntimePosture,
    AuditLogRuntimePosture,
    GovernancePackRuntimePosture,
    BillingOrgScopePosture,
    BudgetControlPlatformPosture,
    BudgetDetailBuildPosture,
    BudgetDetailObservePosture,
    FinOpsInternalPosture,
    BudgetControlObservePosture,
    BudgetControlBuildPosture,
    BillingCrossFeaturePosture,
    ChargebackCrossFeaturePosture,
    LedgerCrossFeaturePosture,
    BudgetScopeGovernancePosture,
    BudgetDetailDrillbackPosture,
    BudgetOverrideExceptionPosture,
    BillingReconciliationPosture,
    BillingDetailEvidencePosture,
    ChargebackAttributionPosture,
    PlaygroundOrgGatewayPosture,
    PlaygroundObservePosture,
    PromptsOrgGatewayPosture,
    PromptDetailObservePosture,
    WorkflowDetailCrossFeaturePosture,
    EvalReplayOrgGatewayPosture,
    EvalReplayObservePosture,
    OptimizationOrgGatewayPosture,
    OptimizationObservePosture,
    OptimizationFinOpsPosture,
    BuildInternalPosture,
    PromptsListObservePosture,
    PromptDetailHubFinOpsPosture,
    AgentsListPosture,
    AgentDetailGovernancePosture,
    WorkflowsListPosture,
    WorkflowDetailLoopPosture,
    WorkflowRunEvidencePosture,
    DatasetsEvalAssetPosture,
    EvalStudioParentPosture,
    ExperimentsComparisonPosture,
    ReplayLabModePosture,
    ReplayResultAnalysisPosture,
    RunbooksRemediationPosture,
    OptOppsRationalePosture,
    OptSimDecisionPosture,
    ModelScorecardsIntelPosture,
    VectorStoreDetailEvidencePosture,
    VectorStoresLifecyclePosture,
    BudgetOrgScopePosture,
    BudgetOverrideGovernancePosture,
    GatewayRuntimeBoundaryPosture,
    SidecarCollapsePosture,
    ConsumerMigrationPosture,
    RuntimeScopeModelPosture,
    ScopeEnforcementEvidencePosture,
    PipelineStudioPosture,
    ApiExplorerPosture,
    DesignSystemPosture,
    PlatformAdminObservePosture,
    PlatformLifecyclePosture,
    PlatformSettingsConvergencePosture,
    TagsRuntimePosture,
    TrendMetric,
    TrendPoint,
    TrendsResponse,
    UserAnalyticsOrgPosture,
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


async def _resolve_access_group_observe_filters(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    access_group_id: uuid.UUID,
) -> dict[str, list[str]]:
    group = (
        await db.execute(
            select(AccessGroup).where(
                AccessGroup.id == access_group_id,
                AccessGroup.workspace_id == workspace_id,
                AccessGroup.is_active.is_(True),
            )
        )
    ).scalar_one_or_none()
    if group is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "Access group not found")

    dashboard_filters = (group.permissions or {}).get("dashboard_filters", {})
    if not isinstance(dashboard_filters, dict):
        dashboard_filters = {}

    def _values(keys: list[str]) -> list[str]:
        collected: list[str] = []
        for key in keys:
            raw = dashboard_filters.get(key)
            if isinstance(raw, str) and raw.strip():
                collected.append(raw.strip())
            elif isinstance(raw, list):
                for item in raw:
                    if isinstance(item, str) and item.strip():
                        collected.append(item.strip())
        return collected

    member_rows = (
        await db.execute(
            select(AccessGroupMember.user_id).where(AccessGroupMember.group_id == access_group_id)
        )
    ).scalars()

    end_user_ids = [str(user_id) for user_id in member_rows]
    end_user_ids.extend(_values(["end_user_id", "end_user_ids", "user_id", "user_ids"]))

    def _unique(values: list[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            ordered.append(value)
        return ordered

    return {
        "end_user_ids": _unique(end_user_ids),
        "feature_tags": _unique(_values(["feature_tag", "feature_tags", "intent", "intents"])),
        "models": _unique(_values(["model", "models"])),
        "providers": _unique(_values(["provider", "providers"])),
        "statuses": _unique(_values(["status", "statuses"])),
    }


# ── /analytics/summary ────────────────────────────────────────────────────────


@router.get("/summary", response_model=AnalyticsSummary)
async def analytics_summary(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
    api_key_id: Annotated[uuid.UUID | None, Query()] = None,
) -> AnalyticsSummary:
    """Total cost, tokens, run count and call count for the time window."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())

    # Prior period: same duration, shifted back
    duration = t_to - t_from
    prev_from = t_from - duration
    prev_to = t_from

    def _summary_stmt(period_from: datetime, period_to: datetime) -> Any:
        stmt = select(
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
        if api_key_id is not None:
            stmt = stmt.where(ProviderCall.api_key_id == api_key_id)
        return stmt

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
    api_key_id: Annotated[uuid.UUID | None, Query()] = None,
) -> SpendOverTime:
    """Time-series of cost and token usage, bucketed by minute, 5 minutes, hour, or day."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())

    if granularity == "minute":
        period_col = func.date_trunc("minute", ProviderCall.created_at).label("period")
    elif granularity == "5min":
        period_col = func.to_timestamp(
            func.floor(func.extract("epoch", ProviderCall.created_at) / 300) * 300
        ).label("period")
    else:
        trunc_unit = "hour" if granularity == "hourly" else "day"
        period_col = func.date_trunc(trunc_unit, ProviderCall.created_at).label("period")

    sot_filters = [
        ProviderCall.workspace_id == workspace.id,
        ProviderCall.created_at >= t_from,
        ProviderCall.created_at < t_to,
        ProviderCall.status == "success",
    ]
    if api_key_id is not None:
        sot_filters.append(ProviderCall.api_key_id == api_key_id)

    stmt = (
        select(
            period_col,
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost_usd"),
            func.coalesce(func.sum(ProviderCall.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(ProviderCall.output_tokens), 0).label("output_tokens"),
            func.count(ProviderCall.id).label("call_count"),
        )
        .where(*sot_filters)
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
    api_key_id: Annotated[uuid.UUID | None, Query()] = None,
) -> SpendByModel:
    """Cost and token usage broken down by provider + model."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())

    sbm_filters = [
        ProviderCall.workspace_id == workspace.id,
        ProviderCall.created_at >= t_from,
        ProviderCall.created_at < t_to,
        ProviderCall.status == "success",
    ]
    if api_key_id is not None:
        sbm_filters.append(ProviderCall.api_key_id == api_key_id)

    stmt = (
        select(
            ProviderCall.provider,
            ProviderCall.model,
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost_usd"),
            func.coalesce(func.sum(ProviderCall.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(ProviderCall.output_tokens), 0).label("output_tokens"),
            func.count(ProviderCall.id).label("call_count"),
        )
        .where(*sbm_filters)
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
    api_key_id: Annotated[uuid.UUID | None, Query()] = None,
) -> SpendByUser:
    """Top end-users by spend."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())

    sbu_filters = [
        ProviderCall.workspace_id == workspace.id,
        ProviderCall.created_at >= t_from,
        ProviderCall.created_at < t_to,
        ProviderCall.status == "success",
        ProviderCall.end_user_id.is_not(None),
    ]
    if api_key_id is not None:
        sbu_filters.append(ProviderCall.api_key_id == api_key_id)

    stmt = (
        select(
            ProviderCall.end_user_id,
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost_usd"),
            func.count(ProviderCall.run_id.distinct()).label("run_count"),
            func.count(ProviderCall.id).label("call_count"),
            func.max(ProviderCall.created_at).label("last_active"),
            func.min(ProviderCall.created_at).label("first_seen"),
        )
        .where(*sbu_filters)
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
    api_key_id: Annotated[uuid.UUID | None, Query()] = None,
) -> SpendByFeature:
    """Cost and run count broken down by feature_tag."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())

    sbf_filters = [
        ProviderCall.workspace_id == workspace.id,
        ProviderCall.created_at >= t_from,
        ProviderCall.created_at < t_to,
        ProviderCall.status == "success",
    ]
    if api_key_id is not None:
        sbf_filters.append(AgentRun.api_key_id == api_key_id)

    stmt = (
        select(
            AgentRun.feature_tag,
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost_usd"),
            func.count(ProviderCall.run_id.distinct()).label("run_count"),
            func.count(ProviderCall.id).label("call_count"),
        )
        .join(AgentRun, AgentRun.id == ProviderCall.run_id)
        .where(*sbf_filters)
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
    from runledger_api.services import kafka_export  # noqa: PLC0415
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
        await kafka_export.publish_event(
            db,
            workspace_id=workspace.id,
            event_type="email.report.sent",
            payload={
                "run_id": str(workspace.id),
                "workspace_name": ws_name,
                "recipient": u.email,
                "cadence": "manual",
                "period_label": period_label,
                "total_cost_usd": total_cost,
                "idempotency_key": f"email-report-manual:{workspace.id}:{u.email}:{window_days}:{t_to.date()}",
                "source": "runledger.email",
                "event_summary": "Manual analytics report sent",
            },
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
    access_group_id: Annotated[uuid.UUID | None, Query()] = None,
) -> ScopedSummary:
    """Summary with workspace/org/platform scope, including savings, intents, and top models."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())
    if access_group_id is not None and scope != "workspace":
        raise HTTPException(
            http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            "access_group_id is only supported for workspace scope",
        )
    ws_ids = await _resolve_scoped_workspace_ids(scope, workspace, user, db)
    duration = t_to - t_from
    access_group_filters = (
        await _resolve_access_group_observe_filters(db, workspace.id, access_group_id)
        if access_group_id is not None
        else None
    )

    base_filter = [
        ProviderCall.workspace_id.in_(ws_ids),
        ProviderCall.created_at >= t_from,
        ProviderCall.created_at < t_to,
        ProviderCall.status == "success",
    ]
    if access_group_filters:
        if access_group_filters["end_user_ids"]:
            base_filter.append(ProviderCall.end_user_id.in_(access_group_filters["end_user_ids"]))
        if access_group_filters["models"]:
            base_filter.append(ProviderCall.model.in_(access_group_filters["models"]))
        if access_group_filters["providers"]:
            base_filter.append(ProviderCall.provider.in_(access_group_filters["providers"]))
        if access_group_filters["statuses"]:
            base_filter.append(ProviderCall.status.in_(access_group_filters["statuses"]))

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
    if access_group_filters:
        # Re-run the intent query with access-group-aware run filters.
        intent_query = select(
            AgentRun.intent,
            func.count(AgentRun.id).label("cnt"),
            func.coalesce(func.sum(AgentRun.total_cost_usd), Decimal(0)).label("cost"),
        ).where(
            AgentRun.workspace_id.in_(ws_ids),
            AgentRun.started_at >= t_from,
            AgentRun.started_at < t_to,
            AgentRun.intent.isnot(None),
        )
        if access_group_filters["end_user_ids"]:
            intent_query = intent_query.where(
                AgentRun.end_user_id.in_(access_group_filters["end_user_ids"])
            )
        if access_group_filters["feature_tags"]:
            intent_query = intent_query.where(
                AgentRun.feature_tag.in_(access_group_filters["feature_tags"])
            )
        if access_group_filters["statuses"]:
            intent_query = intent_query.where(AgentRun.status.in_(access_group_filters["statuses"]))
        if access_group_filters["models"]:
            intent_query = intent_query.where(
                AgentRun.id.in_(
                    select(ProviderCall.run_id)
                    .where(
                        ProviderCall.workspace_id == workspace.id,
                        ProviderCall.model.in_(access_group_filters["models"]),
                    )
                    .distinct()
                )
            )
        if access_group_filters["providers"]:
            intent_query = intent_query.where(
                AgentRun.id.in_(
                    select(ProviderCall.run_id)
                    .where(
                        ProviderCall.workspace_id == workspace.id,
                        ProviderCall.provider.in_(access_group_filters["providers"]),
                    )
                    .distinct()
                )
            )
        intent_rows = (
            await db.execute(
                intent_query.group_by(AgentRun.intent)
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
            IntentCount(intent=r.intent, count=r.cnt, cost_usd=r.cost) for r in intent_rows
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
    api_key_id: Annotated[uuid.UUID | None, Query()] = None,
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
    if api_key_id is not None:
        base.append(ProviderCall.api_key_id == api_key_id)

    totals = (
        await db.execute(
            select(
                func.coalesce(func.sum(ProviderCall.savings_usd), Decimal(0)).label("savings"),
                func.coalesce(func.sum(ProviderCall.baseline_cost_usd), Decimal(0)).label(
                    "baseline"
                ),
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
                func.coalesce(func.sum(ProviderCall.baseline_cost_usd), Decimal(0)).label(
                    "baseline"
                ),
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
            SavingsByCategory(
                category=r.savings_category, savings_usd=r.savings, call_count=r.calls
            )
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

    total_potential = sum((o.potential_savings_usd for o in opportunities), Decimal(0))
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
            TrendMetric(
                name="cost_usd",
                current=cur_row.cost,
                previous=prev_row.cost,
                change_pct=_pct(cur_row.cost, prev_row.cost),
            ),
            TrendMetric(
                name="run_count",
                current=Decimal(cur_row.runs),
                previous=Decimal(prev_row.runs),
                change_pct=_pct(Decimal(cur_row.runs), Decimal(prev_row.runs)),
            ),
            TrendMetric(
                name="call_count",
                current=Decimal(cur_row.calls),
                previous=Decimal(prev_row.calls),
                change_pct=_pct(Decimal(cur_row.calls), Decimal(prev_row.calls)),
            ),
            TrendMetric(
                name="savings_usd",
                current=cur_row.savings,
                previous=prev_row.savings,
                change_pct=_pct(cur_row.savings, prev_row.savings),
            ),
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
    q: Annotated[str | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
    model: Annotated[str | None, Query()] = None,
    provider: Annotated[str | None, Query()] = None,
    intent: Annotated[str | None, Query()] = None,
    end_user_id: Annotated[str | None, Query()] = None,
    optimization: Annotated[str | None, Query()] = None,
    access_group_id: Annotated[uuid.UUID | None, Query()] = None,
    tag: Annotated[str | None, Query()] = None,
    tool_name: Annotated[str | None, Query()] = None,
    security_event_only: Annotated[bool, Query()] = False,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> RequestExplorerResponse:
    """Paginated request explorer with filtering by run, user, status, model, provider, intent, and optimization."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())
    access_group_filters = (
        await _resolve_access_group_observe_filters(db, workspace.id, access_group_id)
        if access_group_id is not None
        else None
    )

    filters = [
        ProviderCall.workspace_id == workspace.id,
        ProviderCall.created_at >= t_from,
        ProviderCall.created_at < t_to,
    ]
    if access_group_filters:
        if access_group_filters["end_user_ids"]:
            filters.append(ProviderCall.end_user_id.in_(access_group_filters["end_user_ids"]))
        if access_group_filters["models"]:
            filters.append(ProviderCall.model.in_(access_group_filters["models"]))
        if access_group_filters["providers"]:
            filters.append(ProviderCall.provider.in_(access_group_filters["providers"]))
        if access_group_filters["statuses"]:
            filters.append(ProviderCall.status.in_(access_group_filters["statuses"]))
    if model:
        filters.append(ProviderCall.model == model)
    if provider:
        filters.append(ProviderCall.provider == provider)
    if status:
        filters.append(ProviderCall.status == status)
    if optimization:
        filters.append(ProviderCall.optimization_applied == optimization)
    if end_user_id:
        filters.append(ProviderCall.end_user_id == end_user_id)
    if tool_name:
        filters.append(
            ProviderCall.run_id.in_(
                select(ToolCall.run_id)
                .where(
                    ToolCall.workspace_id == workspace.id,
                    ToolCall.tool_name == tool_name,
                )
                .distinct()
            )
        )
    if security_event_only:
        filters.append(
            ProviderCall.run_id.in_(
                select(SecurityEvent.run_id)
                .where(
                    SecurityEvent.workspace_id == workspace.id,
                    SecurityEvent.run_id.is_not(None),
                )
                .distinct()
            )
        )

    # Join with AgentRun for intent filtering
    query = (
        select(
            ProviderCall.id,
            ProviderCall.run_id,
            ProviderCall.provider,
            ProviderCall.model,
            AgentRun.intent,
            AgentRun.feature_tag,
            AgentRun.run_metadata,
            ProviderCall.end_user_id,
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
    if access_group_filters and access_group_filters["feature_tags"]:
        query = query.where(AgentRun.feature_tag.in_(access_group_filters["feature_tags"]))
    if tag:
        pattern = f'%"{tag}"%'
        query = query.where(
            or_(
                AgentRun.feature_tag == tag,
                cast(AgentRun.run_metadata, String).ilike(pattern),
            )
        )
    if q:
        q_like = f"%{q.strip()}%"
        if q.strip():
            query = query.where(
                or_(
                    cast(ProviderCall.run_id, String).ilike(q_like),
                    ProviderCall.model.ilike(q_like),
                    ProviderCall.provider.ilike(q_like),
                    ProviderCall.end_user_id.ilike(q_like),
                    AgentRun.intent.ilike(q_like),
                )
            )

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
                end_user_id=r.end_user_id,
                cost_usd=r.cost_usd,
                baseline_cost_usd=r.baseline_cost_usd,
                savings_usd=r.savings_usd,
                optimization_applied=r.optimization_applied,
                input_tokens=r.input_tokens,
                output_tokens=r.output_tokens,
                latency_ms=r.latency_ms,
                status=r.status,
                created_at=str(r.created_at),
                tags=(
                    [
                        item.strip()
                        for item in ((r.run_metadata or {}).get("tags") or [])
                        if isinstance(item, str) and item.strip()
                    ]
                    + ([r.feature_tag] if r.feature_tag else [])
                ),
            )
            for r in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/investigation-governance-posture", response_model=InvestigationGovernancePosture)
async def get_investigation_governance_posture(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
    access_group_id: Annotated[uuid.UUID | None, Query()] = None,
    tag: Annotated[str | None, Query()] = None,
    tool_name: Annotated[str | None, Query()] = None,
    security_event_only: Annotated[bool, Query()] = False,
) -> InvestigationGovernancePosture:
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())
    access_group_filters = (
        await _resolve_access_group_observe_filters(db, workspace.id, access_group_id)
        if access_group_id is not None
        else None
    )
    run_query = select(AgentRun.id).where(
        AgentRun.workspace_id == workspace.id,
        AgentRun.started_at >= t_from,
        AgentRun.started_at < t_to,
    )
    if access_group_filters:
        if access_group_filters["end_user_ids"]:
            run_query = run_query.where(
                AgentRun.end_user_id.in_(access_group_filters["end_user_ids"])
            )
        if access_group_filters["feature_tags"]:
            run_query = run_query.where(
                AgentRun.feature_tag.in_(access_group_filters["feature_tags"])
            )
    if tag:
        pattern = f'%"{tag}"%'
        run_query = run_query.where(
            or_(
                AgentRun.feature_tag == tag,
                cast(AgentRun.run_metadata, String).ilike(pattern),
            )
        )
    if tool_name:
        run_query = run_query.where(
            AgentRun.id.in_(
                select(ToolCall.run_id)
                .where(
                    ToolCall.workspace_id == workspace.id,
                    ToolCall.tool_name == tool_name,
                )
                .distinct()
            )
        )
    if security_event_only:
        run_query = run_query.where(
            AgentRun.id.in_(
                select(SecurityEvent.run_id)
                .where(
                    SecurityEvent.workspace_id == workspace.id,
                    SecurityEvent.run_id.is_not(None),
                )
                .distinct()
            )
        )
    run_ids_subquery = run_query.distinct().subquery()
    filtered_runs = int(
        (await db.execute(select(func.count()).select_from(run_ids_subquery))).scalar() or 0
    )
    tag_rows = (
        (
            await db.execute(
                select(AgentRun.feature_tag)
                .where(AgentRun.id.in_(select(run_ids_subquery.c.id)))
                .where(AgentRun.feature_tag.is_not(None))
                .distinct()
                .limit(12)
            )
        )
        .scalars()
        .all()
    )
    return InvestigationGovernancePosture(
        workspace_id=str(workspace.id),
        period_days=max(1, (t_to - t_from).days or 1),
        filtered_runs=filtered_runs,
        tags=[tag_value for tag_value in tag_rows if isinstance(tag_value, str)],
        tool_governance={
            "registered_tools": int(
                (
                    await db.execute(
                        select(func.count(ToolRegistry.id)).where(
                            ToolRegistry.workspace_id == workspace.id
                        )
                    )
                ).scalar()
                or 0
            ),
            "active_tool_policies": int(
                (
                    await db.execute(
                        select(func.count(ToolPolicy.id)).where(
                            ToolPolicy.workspace_id == workspace.id, ToolPolicy.is_active.is_(True)
                        )
                    )
                ).scalar()
                or 0
            ),
            "filtered_tool_calls": int(
                (
                    await db.execute(
                        select(func.count(ToolCall.id)).where(
                            ToolCall.run_id.in_(select(run_ids_subquery.c.id))
                        )
                    )
                ).scalar()
                or 0
            ),
        },
        security={
            "events": int(
                (
                    await db.execute(
                        select(func.count(SecurityEvent.id)).where(
                            SecurityEvent.workspace_id == workspace.id,
                            SecurityEvent.run_id.in_(select(run_ids_subquery.c.id)),
                        )
                    )
                ).scalar()
                or 0
            ),
            "runs_with_events": int(
                (
                    await db.execute(
                        select(func.count(func.distinct(SecurityEvent.run_id))).where(
                            SecurityEvent.workspace_id == workspace.id,
                            SecurityEvent.run_id.in_(select(run_ids_subquery.c.id)),
                        )
                    )
                ).scalar()
                or 0
            ),
        },
        alert_rules={
            "active": int(
                (
                    await db.execute(
                        select(func.count(AlertRule.id)).where(
                            AlertRule.workspace_id == workspace.id, AlertRule.is_active.is_(True)
                        )
                    )
                ).scalar()
                or 0
            ),
            "recent_firings": int(
                (
                    await db.execute(
                        select(func.count(AlertFiring.id)).where(
                            AlertFiring.workspace_id == workspace.id,
                            AlertFiring.fired_at >= t_from,
                            AlertFiring.fired_at < t_to,
                        )
                    )
                ).scalar()
                or 0
            ),
        },
        audit_log={
            "events_30d": int(
                (
                    await db.execute(
                        select(func.count(AuditEvent.id)).where(
                            AuditEvent.workspace_id == workspace.id,
                            AuditEvent.created_at >= t_from,
                            AuditEvent.created_at < t_to,
                        )
                    )
                ).scalar()
                or 0
            ),
            "governance_events": int(
                (
                    await db.execute(
                        select(func.count(AuditEvent.id)).where(
                            AuditEvent.workspace_id == workspace.id,
                            AuditEvent.created_at >= t_from,
                            AuditEvent.created_at < t_to,
                            AuditEvent.target_type.in_(
                                [
                                    "tool_policy",
                                    "tool_registry",
                                    "security",
                                    "alert_rule",
                                    "tag",
                                    "governance_pack",
                                    "capture_policy",
                                ]
                            ),
                        )
                    )
                ).scalar()
                or 0
            ),
        },
        governance_pack={
            "approvals": int(
                (
                    await db.execute(
                        select(func.count(Approval.id)).where(Approval.workspace_id == workspace.id)
                    )
                ).scalar()
                or 0
            ),
            "capture_policies": int(
                (
                    await db.execute(
                        select(func.count(CapturePolicy.id)).where(
                            CapturePolicy.workspace_id == workspace.id
                        )
                    )
                ).scalar()
                or 0
            ),
            "tags": int(
                (
                    await db.execute(
                        select(func.count(Tag.id)).where(
                            Tag.workspace_id == workspace.id, Tag.is_active.is_(True)
                        )
                    )
                ).scalar()
                or 0
            ),
        },
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
            select(func.count(Span.id))
            .join(AgentRun, AgentRun.id == Span.run_id)
            .where(
                AgentRun.workspace_id == workspace.id,
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
        LifecycleStage(
            stage="Routed",
            count=routed,
            pct=Decimal(round(routed / total_runs * 100, 1)) if total_runs > 0 else Decimal(0),
        ),
        LifecycleStage(
            stage="Cached",
            count=cache_hits,
            pct=Decimal(round(cache_hits / total_runs * 100, 1)) if total_runs > 0 else Decimal(0),
        ),
        LifecycleStage(
            stage="Completed",
            count=succeeded_runs,
            pct=Decimal(round(succeeded_runs / total_runs * 100, 1))
            if total_runs > 0
            else Decimal(0),
        ),
        LifecycleStage(
            stage="With outcome",
            count=with_outcome,
            pct=Decimal(round(with_outcome / total_runs * 100, 1))
            if total_runs > 0
            else Decimal(0),
        ),
        LifecycleStage(
            stage="Positive",
            count=positive_outcome,
            pct=Decimal(round(positive_outcome / total_runs * 100, 1))
            if total_runs > 0
            else Decimal(0),
        ),
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
            CostByDimension(name=r.model, cost_usd=r.cost, call_count=r.calls) for r in model_rows
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
        func.sum(case((ProviderCall.cached_input_tokens > 0, 1), else_=0)).label("cached"),
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

    projected_cost = (
        current_cost * model_cost_ratio * (1 - cache_savings_pct) * (1 - compression_pct)
    )
    projected_savings = current_cost - projected_cost
    savings_pct = (projected_savings / current_cost * 100) if current_cost > 0 else Decimal(0)

    proposed_lat = None
    lat_delta = None
    if current_lat and proposed_key:
        proposed_lat_est = MODEL_LATENCY_MS.get(proposed_key)
        if proposed_lat_est:
            proposed_lat = Decimal(str(round(proposed_lat_est, 1)))
            if current_lat > 0:
                lat_delta = Decimal(
                    str(round((proposed_lat_est - current_lat) / current_lat * 100, 1))
                )

    quality_risk = "low"
    if proposed_key:
        quality_risk = QUALITY_RISK_MAP.get(proposed_key, "medium")

    confidence = "high" if affected >= 100 else "medium" if affected >= 20 else "directional"

    impacts: list[SimulationImpact] = []
    if body.proposed_model and body.current_model:
        impacts.append(
            SimulationImpact(
                label="Model change",
                current_value=body.current_model,
                projected_value=body.proposed_model,
                delta_pct=Decimal(str(round((float(model_cost_ratio) - 1) * 100, 1))),
            )
        )
    if body.enable_cache:
        impacts.append(
            SimulationImpact(
                label="Cache policy",
                current_value=f"{round(cached_count / affected * 100)}% hit rate"
                if affected > 0
                else "0%",
                projected_value=f"~{round(float(cache_savings_pct) * 100 + cached_count / affected * 100)}% hit rate"
                if affected > 0
                else "40%",
                delta_pct=Decimal(str(round(float(cache_savings_pct) * -100, 1))),
            )
        )
    if body.enable_compression:
        impacts.append(
            SimulationImpact(
                label="Prompt compression",
                current_value="Disabled",
                projected_value="Enabled (~15% token reduction)",
                delta_pct=Decimal("-15"),
            )
        )

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
    access_group_id: Annotated[str | None, Query()] = None,
    api_key_id: Annotated[str | None, Query()] = None,
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
    if access_group_id:
        import uuid as _uuid

        from runledger_api.models.access_groups import AccessGroupMember

        member_rows = (
            (
                await db.execute(
                    select(AccessGroupMember.user_id).where(
                        AccessGroupMember.group_id == _uuid.UUID(access_group_id)
                    )
                )
            )
            .scalars()
            .all()
        )
        member_ids = [str(uid) for uid in member_rows]
        filters.append(ProviderCall.end_user_id.in_(member_ids))
    if api_key_id:
        import uuid as _uuid

        filters.append(ProviderCall.api_key_id == _uuid.UUID(api_key_id))

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

        items.append(
            ModelScorecard(
                model=r.model,
                provider=r.provider,
                total_cost_usd=Decimal(str(r.total_cost or 0)),
                call_count=r.call_count,
                avg_cost_per_call=Decimal(str(round(float(r.avg_cost or 0), 6))),
                avg_latency_ms=Decimal(str(round(float(r.avg_latency or 0), 1)))
                if r.avg_latency
                else None,
                p95_latency_ms=Decimal(str(round(float(r.p95_latency or 0), 1)))
                if r.p95_latency
                else None,
                error_rate=Decimal(str(round(r.error_count / r.call_count * 100, 2)))
                if r.call_count > 0
                else Decimal("0"),
                cache_hit_rate=cache_hit_rate,
                avg_quality_score=Decimal(str(round(float(avg_score), 2))) if avg_score else None,
                input_tokens=r.input_tokens or 0,
                output_tokens=r.output_tokens or 0,
            )
        )

    return ModelScorecardList(items=items, from_dt=start, to_dt=end)


@router.get("/api-key-footprint/{api_key_id}")
async def api_key_observe_footprint(
    api_key_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    key = (
        await db.execute(
            select(ApiKey).where(ApiKey.id == api_key_id, ApiKey.workspace_id == workspace.id)
        )
    ).scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found in this workspace")

    since = datetime.now(UTC) - timedelta(days=30)

    run_stmt = select(
        func.count(AgentRun.id).label("run_count"),
        func.coalesce(func.sum(AgentRun.total_cost_usd), 0).label("total_cost"),
        func.coalesce(func.sum(AgentRun.total_tokens), 0).label("total_tokens"),
    ).where(
        AgentRun.workspace_id == workspace.id,
        AgentRun.api_key_id == api_key_id,
        AgentRun.started_at >= since,
    )
    run_row = (await db.execute(run_stmt)).one()

    model_stmt = (
        select(ProviderCall.model)
        .where(
            ProviderCall.workspace_id == workspace.id,
            ProviderCall.api_key_id == api_key_id,
            ProviderCall.created_at >= since,
        )
        .group_by(ProviderCall.model)
    )
    models_used = [r.model for r in (await db.execute(model_stmt)).all()]

    recent_stmt = (
        select(AgentRun.id, AgentRun.status, AgentRun.total_cost_usd, AgentRun.started_at)
        .where(
            AgentRun.workspace_id == workspace.id,
            AgentRun.api_key_id == api_key_id,
        )
        .order_by(AgentRun.started_at.desc())
        .limit(10)
    )
    recent_runs = [
        {
            "id": str(r.id),
            "status": r.status,
            "cost_usd": float(r.total_cost_usd or 0),
            "created_at": r.created_at.isoformat(),
        }
        for r in (await db.execute(recent_stmt)).all()
    ]

    return {
        "api_key_id": str(api_key_id),
        "key_name": key.name,
        "period_days": 30,
        "run_count": run_row.run_count,
        "total_cost_usd": float(run_row.total_cost),
        "total_tokens": int(run_row.total_tokens),
        "models_used": models_used,
        "recent_runs": recent_runs,
    }


@router.get("/workspace-observe-posture")
async def workspace_observe_posture(
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    since = datetime.now(UTC) - timedelta(days=30)

    run_stmt = select(
        func.count(AgentRun.id).label("run_count"),
        func.coalesce(func.sum(AgentRun.total_cost_usd), 0).label("total_cost"),
        func.coalesce(func.sum(AgentRun.total_tokens), 0).label("total_tokens"),
        func.count(func.distinct(AgentRun.end_user_id)).label("active_users"),
    ).where(
        AgentRun.workspace_id == workspace.id,
        AgentRun.started_at >= since,
    )
    run_row = (await db.execute(run_stmt)).one()

    model_stmt = select(func.count(func.distinct(ProviderCall.model))).where(
        ProviderCall.workspace_id == workspace.id,
        ProviderCall.created_at >= since,
    )
    model_count = (await db.execute(model_stmt)).scalar() or 0

    error_stmt = select(func.count(AgentRun.id)).where(
        AgentRun.workspace_id == workspace.id,
        AgentRun.started_at >= since,
        AgentRun.status == "error",
    )
    error_count = (await db.execute(error_stmt)).scalar() or 0

    budget_count = (
        await db.execute(select(func.count(Budget.id)).where(Budget.workspace_id == workspace.id))
    ).scalar() or 0

    billing_count = (
        await db.execute(
            select(func.count(BillingPeriod.id)).where(BillingPeriod.workspace_id == workspace.id)
        )
    ).scalar() or 0

    notification_count = (
        await db.execute(
            select(func.count(BudgetNotification.id))
            .join(Budget)
            .where(Budget.workspace_id == workspace.id)
        )
    ).scalar() or 0

    return {
        "workspace_id": str(workspace.id),
        "period_days": 30,
        "run_count": run_row.run_count,
        "total_cost_usd": float(run_row.total_cost),
        "total_tokens": int(run_row.total_tokens),
        "active_users": run_row.active_users,
        "model_count": model_count,
        "error_count": error_count,
        "budget_count": budget_count,
        "billing_period_count": billing_count,
        "budget_notification_count": notification_count,
    }


@router.get("/workspace-governance-posture")
async def workspace_governance_posture(
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    tool_policy_count = (
        await db.execute(
            select(func.count(ToolPolicy.id)).where(ToolPolicy.workspace_id == workspace.id)
        )
    ).scalar() or 0

    approval_count = (
        await db.execute(
            select(func.count(Approval.id)).where(Approval.workspace_id == workspace.id)
        )
    ).scalar() or 0

    pending_approval_count = (
        await db.execute(
            select(func.count(Approval.id)).where(
                Approval.workspace_id == workspace.id,
                Approval.status == "pending",
            )
        )
    ).scalar() or 0

    audit_event_count = (
        await db.execute(
            select(func.count(AuditEvent.id)).where(AuditEvent.workspace_id == workspace.id)
        )
    ).scalar() or 0

    alert_rule_count = (
        await db.execute(
            select(func.count(AlertRule.id)).where(AlertRule.workspace_id == workspace.id)
        )
    ).scalar() or 0

    active_alert_count = (
        await db.execute(
            select(func.count(AlertRule.id)).where(
                AlertRule.workspace_id == workspace.id,
                AlertRule.is_active.is_(True),
            )
        )
    ).scalar() or 0

    tag_count = (
        await db.execute(select(func.count(Tag.id)).where(Tag.workspace_id == workspace.id))
    ).scalar() or 0

    chargeback_rule_count = (
        await db.execute(
            select(func.count(ChargebackRule.id)).where(ChargebackRule.workspace_id == workspace.id)
        )
    ).scalar() or 0

    return {
        "workspace_id": str(workspace.id),
        "tool_policy_count": tool_policy_count,
        "approval_count": approval_count,
        "pending_approval_count": pending_approval_count,
        "audit_event_count": audit_event_count,
        "alert_rule_count": alert_rule_count,
        "active_alert_count": active_alert_count,
        "tag_count": tag_count,
        "chargeback_rule_count": chargeback_rule_count,
    }


@router.get("/access-group-gateway-posture")
async def access_group_gateway_posture(
    access_group_id: Annotated[uuid.UUID, Query()],
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    group = (
        await db.execute(
            select(AccessGroup).where(
                AccessGroup.id == access_group_id,
                AccessGroup.workspace_id == workspace.id,
            )
        )
    ).scalar_one_or_none()
    if not group:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "Access group not found")

    route_count = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(GatewayRoute.workspace_id == workspace.id)
        )
    ).scalar() or 0
    active_route_count = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id, GatewayRoute.is_active.is_(True)
            )
        )
    ).scalar() or 0
    distinct_providers = (
        await db.execute(
            select(func.count(func.distinct(GatewayRoute.provider))).where(
                GatewayRoute.workspace_id == workspace.id, GatewayRoute.is_active.is_(True)
            )
        )
    ).scalar() or 0
    routing_policy_count = (
        await db.execute(
            select(func.count(RoutingPolicy.id)).where(RoutingPolicy.workspace_id == workspace.id)
        )
    ).scalar() or 0
    guardrail_count = (
        await db.execute(
            select(func.count(GuardrailRule.id)).where(GuardrailRule.workspace_id == workspace.id)
        )
    ).scalar() or 0
    active_guardrail_count = (
        await db.execute(
            select(func.count(GuardrailRule.id)).where(
                GuardrailRule.workspace_id == workspace.id, GuardrailRule.status == "active"
            )
        )
    ).scalar() or 0
    passthrough_count = (
        await db.execute(
            select(func.count(GatewayPassThroughEndpoint.id)).where(
                GatewayPassThroughEndpoint.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    return {
        "access_group_id": str(access_group_id),
        "workspace_id": str(workspace.id),
        "guardrail_profile": group.guardrail_profile,
        "route_count": route_count,
        "active_route_count": active_route_count,
        "distinct_providers": distinct_providers,
        "routing_policy_count": routing_policy_count,
        "guardrail_count": guardrail_count,
        "active_guardrail_count": active_guardrail_count,
        "passthrough_count": passthrough_count,
    }


@router.get("/api-key-gateway-posture")
async def api_key_gateway_posture(
    api_key_id: Annotated[uuid.UUID, Query()],
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    key = (
        await db.execute(
            select(ApiKey).where(
                ApiKey.id == api_key_id,
                ApiKey.workspace_id == workspace.id,
            )
        )
    ).scalar_one_or_none()
    if not key:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "API key not found")

    route_count = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(GatewayRoute.workspace_id == workspace.id)
        )
    ).scalar() or 0
    active_route_count = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id, GatewayRoute.is_active.is_(True)
            )
        )
    ).scalar() or 0
    distinct_providers = (
        await db.execute(
            select(func.count(func.distinct(GatewayRoute.provider))).where(
                GatewayRoute.workspace_id == workspace.id, GatewayRoute.is_active.is_(True)
            )
        )
    ).scalar() or 0
    guardrail_count = (
        await db.execute(
            select(func.count(GuardrailRule.id)).where(GuardrailRule.workspace_id == workspace.id)
        )
    ).scalar() or 0
    active_guardrail_count = (
        await db.execute(
            select(func.count(GuardrailRule.id)).where(
                GuardrailRule.workspace_id == workspace.id, GuardrailRule.status == "active"
            )
        )
    ).scalar() or 0
    rate_limited_route_count = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id, GatewayRoute.per_user_rpm_limit.isnot(None)
            )
        )
    ).scalar() or 0

    return {
        "api_key_id": str(api_key_id),
        "workspace_id": str(workspace.id),
        "route_count": route_count,
        "active_route_count": active_route_count,
        "distinct_providers": distinct_providers,
        "guardrail_count": guardrail_count,
        "active_guardrail_count": active_guardrail_count,
        "rate_limited_route_count": rate_limited_route_count,
    }


@router.get("/telemetry-downstream-posture")
async def telemetry_downstream_posture(
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    now = datetime.now(UTC)
    thirty_days_ago = now - timedelta(days=30)

    batch_count_30d = (
        await db.execute(
            select(func.count(OtlpIngestBatch.id)).where(
                OtlpIngestBatch.workspace_id == workspace.id,
                OtlpIngestBatch.received_at >= thirty_days_ago,
            )
        )
    ).scalar() or 0

    budget_count = (
        await db.execute(select(func.count(Budget.id)).where(Budget.workspace_id == workspace.id))
    ).scalar() or 0
    active_billing_periods = (
        await db.execute(
            select(func.count(BillingPeriod.id)).where(
                BillingPeriod.workspace_id == workspace.id, BillingPeriod.status == "open"
            )
        )
    ).scalar() or 0
    chargeback_rule_count = (
        await db.execute(
            select(func.count(ChargebackRule.id)).where(ChargebackRule.workspace_id == workspace.id)
        )
    ).scalar() or 0
    budget_notification_count = (
        await db.execute(
            select(func.count(BudgetNotification.id)).where(
                BudgetNotification.budget_id.in_(
                    select(Budget.id).where(Budget.workspace_id == workspace.id)
                )
            )
        )
    ).scalar() or 0

    tool_policy_count = (
        await db.execute(
            select(func.count(ToolPolicy.id)).where(ToolPolicy.workspace_id == workspace.id)
        )
    ).scalar() or 0
    approval_count = (
        await db.execute(
            select(func.count(Approval.id)).where(Approval.workspace_id == workspace.id)
        )
    ).scalar() or 0
    audit_event_count = (
        await db.execute(
            select(func.count(AuditEvent.id)).where(AuditEvent.workspace_id == workspace.id)
        )
    ).scalar() or 0
    alert_rule_count = (
        await db.execute(
            select(func.count(AlertRule.id)).where(AlertRule.workspace_id == workspace.id)
        )
    ).scalar() or 0
    active_alert_count = (
        await db.execute(
            select(func.count(AlertRule.id)).where(
                AlertRule.workspace_id == workspace.id, AlertRule.is_active.is_(True)
            )
        )
    ).scalar() or 0
    tag_count = (
        await db.execute(select(func.count(Tag.id)).where(Tag.workspace_id == workspace.id))
    ).scalar() or 0

    return {
        "workspace_id": str(workspace.id),
        "batch_count_30d": batch_count_30d,
        "finops": {
            "budget_count": budget_count,
            "active_billing_periods": active_billing_periods,
            "chargeback_rule_count": chargeback_rule_count,
            "budget_notification_count": budget_notification_count,
        },
        "safety": {
            "tool_policy_count": tool_policy_count,
            "approval_count": approval_count,
            "audit_event_count": audit_event_count,
            "alert_rule_count": alert_rule_count,
            "active_alert_count": active_alert_count,
            "tag_count": tag_count,
        },
    }


@router.get("/mcp-registry-posture")
async def mcp_registry_posture(
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    now = datetime.now(UTC)
    thirty_days_ago = now - timedelta(days=30)

    server_count = (
        await db.execute(
            select(func.count(McpServer.id)).where(McpServer.workspace_id == workspace.id)
        )
    ).scalar() or 0
    active_server_count = (
        await db.execute(
            select(func.count(McpServer.id)).where(
                McpServer.workspace_id == workspace.id, McpServer.is_active.is_(True)
            )
        )
    ).scalar() or 0
    tool_call_count_30d = (
        await db.execute(
            select(func.count(McpToolCall.id)).where(
                McpToolCall.workspace_id == workspace.id, McpToolCall.created_at >= thirty_days_ago
            )
        )
    ).scalar() or 0
    distinct_tools_used = (
        await db.execute(
            select(func.count(func.distinct(McpToolCall.tool_name))).where(
                McpToolCall.workspace_id == workspace.id, McpToolCall.created_at >= thirty_days_ago
            )
        )
    ).scalar() or 0
    error_call_count = (
        await db.execute(
            select(func.count(McpToolCall.id)).where(
                McpToolCall.workspace_id == workspace.id,
                McpToolCall.created_at >= thirty_days_ago,
                McpToolCall.status == "error",
            )
        )
    ).scalar() or 0

    route_count = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(GatewayRoute.workspace_id == workspace.id)
        )
    ).scalar() or 0
    guardrail_count = (
        await db.execute(
            select(func.count(GuardrailRule.id)).where(GuardrailRule.workspace_id == workspace.id)
        )
    ).scalar() or 0

    approval_count = (
        await db.execute(
            select(func.count(Approval.id)).where(Approval.workspace_id == workspace.id)
        )
    ).scalar() or 0
    audit_event_count = (
        await db.execute(
            select(func.count(AuditEvent.id)).where(AuditEvent.workspace_id == workspace.id)
        )
    ).scalar() or 0
    chargeback_rule_count = (
        await db.execute(
            select(func.count(ChargebackRule.id)).where(ChargebackRule.workspace_id == workspace.id)
        )
    ).scalar() or 0

    return {
        "workspace_id": str(workspace.id),
        "server_count": server_count,
        "active_server_count": active_server_count,
        "tool_call_count_30d": tool_call_count_30d,
        "distinct_tools_used": distinct_tools_used,
        "error_call_count": error_call_count,
        "gateway": {
            "route_count": route_count,
            "guardrail_count": guardrail_count,
        },
        "governance": {
            "approval_count": approval_count,
            "audit_event_count": audit_event_count,
            "chargeback_rule_count": chargeback_rule_count,
        },
    }


@router.get("/ai-hub-runtime-posture")
async def ai_hub_runtime_posture(
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    now = datetime.now(UTC)
    thirty_days_ago = now - timedelta(days=30)

    model_count = (
        await db.execute(
            select(func.count(HubModel.id)).where(HubModel.workspace_id == workspace.id)
        )
    ).scalar() or 0
    featured_count = (
        await db.execute(
            select(func.count(HubModel.id)).where(
                HubModel.workspace_id == workspace.id, HubModel.is_featured.is_(True)
            )
        )
    ).scalar() or 0
    deprecated_count = (
        await db.execute(
            select(func.count(HubModel.id)).where(
                HubModel.workspace_id == workspace.id, HubModel.is_deprecated.is_(True)
            )
        )
    ).scalar() or 0

    run_count_30d = (
        await db.execute(
            select(func.count(AgentRun.id)).where(
                AgentRun.workspace_id == workspace.id, AgentRun.started_at >= thirty_days_ago
            )
        )
    ).scalar() or 0
    distinct_models_used = (
        await db.execute(
            select(func.count(func.distinct(ProviderCall.model))).where(
                ProviderCall.workspace_id == workspace.id,
                ProviderCall.started_at >= thirty_days_ago,
            )
        )
    ).scalar() or 0

    budget_count = (
        await db.execute(select(func.count(Budget.id)).where(Budget.workspace_id == workspace.id))
    ).scalar() or 0
    budget_notification_count = (
        await db.execute(
            select(func.count(BudgetNotification.id)).where(
                BudgetNotification.budget_id.in_(
                    select(Budget.id).where(Budget.workspace_id == workspace.id)
                )
            )
        )
    ).scalar() or 0

    guardrail_count = (
        await db.execute(
            select(func.count(GuardrailRule.id)).where(GuardrailRule.workspace_id == workspace.id)
        )
    ).scalar() or 0

    return {
        "workspace_id": str(workspace.id),
        "model_count": model_count,
        "featured_count": featured_count,
        "deprecated_count": deprecated_count,
        "observe": {
            "run_count_30d": run_count_30d,
            "distinct_models_used": distinct_models_used,
        },
        "finops": {
            "budget_count": budget_count,
            "budget_notification_count": budget_notification_count,
        },
        "gateway": {
            "guardrail_count": guardrail_count,
        },
    }


@router.get("/provider-profile-finops-posture")
async def provider_profile_finops_posture(
    profile_id: uuid.UUID = Query(..., description="Provider pricing profile UUID"),
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    profile = (
        await db.execute(
            select(ProviderPricing).where(
                ProviderPricing.id == profile_id,
                or_(
                    ProviderPricing.workspace_id == workspace.id,
                    ProviderPricing.workspace_id.is_(None),
                ),
            )
        )
    ).scalar_one_or_none()
    if profile is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "Provider profile not found")

    now = datetime.now(UTC)

    provider_budgets_q = select(Budget).where(
        Budget.workspace_id == workspace.id,
        Budget.scope_type == "provider_profile",
        Budget.scope_id == str(profile_id),
    )
    budgets = (await db.execute(provider_budgets_q)).scalars().all()
    budget_ids = [b.id for b in budgets]

    budget_count = len(budgets)
    active_budget_count = sum(1 for b in budgets if b.is_active)

    override_count = 0
    active_override_count = 0
    if budget_ids:
        override_count = (
            await db.execute(
                select(func.count(BudgetOverride.id)).where(
                    BudgetOverride.budget_id.in_(budget_ids)
                )
            )
        ).scalar() or 0
        active_override_count = (
            await db.execute(
                select(func.count(BudgetOverride.id)).where(
                    BudgetOverride.budget_id.in_(budget_ids),
                    BudgetOverride.status == "active",
                    BudgetOverride.expires_at > now,
                )
            )
        ).scalar() or 0

    billing_period_count = (
        await db.execute(
            select(func.count(BillingPeriod.id)).where(BillingPeriod.workspace_id == workspace.id)
        )
    ).scalar() or 0
    open_billing_periods = (
        await db.execute(
            select(func.count(BillingPeriod.id)).where(
                BillingPeriod.workspace_id == workspace.id,
                BillingPeriod.status == "open",
            )
        )
    ).scalar() or 0

    chargeback_rule_count = (
        await db.execute(
            select(func.count(ChargebackRule.id)).where(ChargebackRule.workspace_id == workspace.id)
        )
    ).scalar() or 0

    total_limit_usd = sum(float(b.limit_usd) for b in budgets if b.is_active)
    breach_count = 0
    if budget_ids:
        from runledger_api.models.budgets import BudgetBreach

        breach_count = (
            await db.execute(
                select(func.count(BudgetBreach.id)).where(BudgetBreach.budget_id.in_(budget_ids))
            )
        ).scalar() or 0

    return {
        "workspace_id": str(workspace.id),
        "profile_id": str(profile_id),
        "provider": profile.provider,
        "model": profile.model,
        "budgets": {
            "budget_count": budget_count,
            "active_budget_count": active_budget_count,
            "total_limit_usd": round(total_limit_usd, 6),
            "breach_count": breach_count,
        },
        "overrides": {
            "override_count": override_count,
            "active_override_count": active_override_count,
        },
        "billing": {
            "billing_period_count": billing_period_count,
            "open_billing_periods": open_billing_periods,
        },
        "chargeback": {
            "chargeback_rule_count": chargeback_rule_count,
        },
    }


@router.get("/budget-performance-posture/{budget_id}")
async def budget_performance_posture(
    budget_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    from runledger_api.models.budget_overrides import BudgetOverride
    from runledger_api.models.gateway import GatewayRequest, GatewayRoute

    budget = (
        await db.execute(
            select(Budget).where(
                Budget.id == budget_id,
                Budget.workspace_id == workspace.id,
            )
        )
    ).scalar_one_or_none()
    if budget is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "Budget not found")

    now = datetime.now(UTC)
    thirty_days_ago = now - timedelta(days=30)

    total_requests = (
        await db.execute(
            select(func.count(GatewayRequest.id)).where(
                GatewayRequest.workspace_id == workspace.id,
                GatewayRequest.created_at >= thirty_days_ago,
            )
        )
    ).scalar() or 0

    cache_hits = (
        await db.execute(
            select(func.count(GatewayRequest.id)).where(
                GatewayRequest.workspace_id == workspace.id,
                GatewayRequest.created_at >= thirty_days_ago,
                GatewayRequest.cache_hit.is_(True),
            )
        )
    ).scalar() or 0

    cache_hit_rate = round(cache_hits / total_requests * 100, 2) if total_requests > 0 else 0.0

    rate_limited_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.per_user_rpm_limit.isnot(None),
                GatewayRoute.is_active.is_(True),
            )
        )
    ).scalar() or 0

    total_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
            )
        )
    ).scalar() or 0

    override_count = (
        await db.execute(
            select(func.count(BudgetOverride.id)).where(
                BudgetOverride.budget_id == budget_id,
            )
        )
    ).scalar() or 0

    active_overrides = (
        await db.execute(
            select(func.count(BudgetOverride.id)).where(
                BudgetOverride.budget_id == budget_id,
                BudgetOverride.status == "active",
                BudgetOverride.expires_at > now,
            )
        )
    ).scalar() or 0

    billing_period_count = (
        await db.execute(
            select(func.count(BillingPeriod.id)).where(
                BillingPeriod.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    chargeback_rule_count = (
        await db.execute(
            select(func.count(ChargebackRule.id)).where(
                ChargebackRule.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    return {
        "workspace_id": str(workspace.id),
        "budget_id": str(budget_id),
        "cache": {
            "total_requests_30d": total_requests,
            "cache_hits_30d": cache_hits,
            "cache_hit_rate_pct": cache_hit_rate,
            "estimated_savings_pct": round(cache_hit_rate * 0.5, 2),
        },
        "rate_limits": {
            "rate_limited_routes": rate_limited_routes,
            "total_active_routes": total_routes,
            "containment_coverage_pct": round(rate_limited_routes / total_routes * 100, 1)
            if total_routes > 0
            else 0.0,
        },
        "overrides": {
            "override_count": override_count,
            "active_overrides": active_overrides,
        },
        "billing": {
            "billing_period_count": billing_period_count,
        },
        "chargeback": {
            "chargeback_rule_count": chargeback_rule_count,
        },
    }


@router.get("/billing-period-performance-posture")
async def billing_period_performance_posture(
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    from runledger_api.models.gateway import GatewayRequest, GatewayRoute

    now = datetime.now(UTC)
    thirty_days_ago = now - timedelta(days=30)

    total_requests = (
        await db.execute(
            select(func.count(GatewayRequest.id)).where(
                GatewayRequest.workspace_id == workspace.id,
                GatewayRequest.created_at >= thirty_days_ago,
            )
        )
    ).scalar() or 0

    cache_hits = (
        await db.execute(
            select(func.count(GatewayRequest.id)).where(
                GatewayRequest.workspace_id == workspace.id,
                GatewayRequest.created_at >= thirty_days_ago,
                GatewayRequest.cache_hit.is_(True),
            )
        )
    ).scalar() or 0

    cache_hit_rate = round(cache_hits / total_requests * 100, 2) if total_requests > 0 else 0.0

    rate_limited_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.per_user_rpm_limit.isnot(None),
                GatewayRoute.is_active.is_(True),
            )
        )
    ).scalar() or 0

    total_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
            )
        )
    ).scalar() or 0

    open_periods = (
        await db.execute(
            select(func.count(BillingPeriod.id)).where(
                BillingPeriod.workspace_id == workspace.id,
                BillingPeriod.status == "open",
            )
        )
    ).scalar() or 0

    total_periods = (
        await db.execute(
            select(func.count(BillingPeriod.id)).where(
                BillingPeriod.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    budget_count = (
        await db.execute(
            select(func.count(Budget.id)).where(
                Budget.workspace_id == workspace.id,
                Budget.is_active.is_(True),
            )
        )
    ).scalar() or 0

    chargeback_rule_count = (
        await db.execute(
            select(func.count(ChargebackRule.id)).where(
                ChargebackRule.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    return {
        "workspace_id": str(workspace.id),
        "cache": {
            "total_requests_30d": total_requests,
            "cache_hits_30d": cache_hits,
            "cache_hit_rate_pct": cache_hit_rate,
            "estimated_savings_pct": round(cache_hit_rate * 0.5, 2),
        },
        "rate_limits": {
            "rate_limited_routes": rate_limited_routes,
            "total_active_routes": total_routes,
            "containment_coverage_pct": round(rate_limited_routes / total_routes * 100, 1)
            if total_routes > 0
            else 0.0,
        },
        "billing": {
            "open_periods": open_periods,
            "total_periods": total_periods,
            "active_budget_count": budget_count,
        },
        "chargeback": {
            "chargeback_rule_count": chargeback_rule_count,
        },
    }


@router.get("/gateway-finops-posture")
async def gateway_finops_posture(
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    from runledger_api.models.gateway import GatewayRequest

    now = datetime.now(UTC)
    thirty_days_ago = now - timedelta(days=30)

    total_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
            )
        )
    ).scalar() or 0

    routes_with_cost_caps = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
                or_(
                    GatewayRoute.daily_cost_limit_usd.isnot(None),
                    GatewayRoute.monthly_cost_limit_usd.isnot(None),
                ),
            )
        )
    ).scalar() or 0

    rate_limited_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
                GatewayRoute.per_user_rpm_limit.isnot(None),
            )
        )
    ).scalar() or 0

    total_requests_30d = (
        await db.execute(
            select(func.count(GatewayRequest.id)).where(
                GatewayRequest.workspace_id == workspace.id,
                GatewayRequest.created_at >= thirty_days_ago,
            )
        )
    ).scalar() or 0

    total_spend_rows = (
        await db.execute(
            select(
                func.coalesce(func.sum(UsageDaily.cost_usd), Decimal("0")),
            ).where(
                UsageDaily.workspace_id == workspace.id,
                UsageDaily.day >= thirty_days_ago.date(),
            )
        )
    ).scalar() or Decimal("0")

    budget_count = (
        await db.execute(
            select(func.count(Budget.id)).where(
                Budget.workspace_id == workspace.id,
                Budget.is_active.is_(True),
            )
        )
    ).scalar() or 0

    _budgets_near_limit = (
        await db.execute(
            select(func.count(Budget.id)).where(
                Budget.workspace_id == workspace.id,
                Budget.is_active.is_(True),
            )
        )
    ).scalar() or 0

    override_count = (
        await db.execute(
            select(func.count(BudgetOverride.id)).where(
                BudgetOverride.budget_id.in_(
                    select(Budget.id).where(Budget.workspace_id == workspace.id)
                )
            )
        )
    ).scalar() or 0

    active_overrides = (
        await db.execute(
            select(func.count(BudgetOverride.id)).where(
                BudgetOverride.budget_id.in_(
                    select(Budget.id).where(Budget.workspace_id == workspace.id)
                ),
                BudgetOverride.status == "active",
            )
        )
    ).scalar() or 0

    notification_count = (
        await db.execute(
            select(func.count(BudgetNotification.id)).where(
                BudgetNotification.workspace_id == workspace.id,
                BudgetNotification.is_active.is_(True),
            )
        )
    ).scalar() or 0

    open_periods = (
        await db.execute(
            select(func.count(BillingPeriod.id)).where(
                BillingPeriod.workspace_id == workspace.id,
                BillingPeriod.status == "open",
            )
        )
    ).scalar() or 0

    total_periods = (
        await db.execute(
            select(func.count(BillingPeriod.id)).where(
                BillingPeriod.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    chargeback_rule_count = (
        await db.execute(
            select(func.count(ChargebackRule.id)).where(
                ChargebackRule.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    distinct_models = (
        await db.execute(
            select(func.count(func.distinct(GatewayRoute.target_model))).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
            )
        )
    ).scalar() or 0

    routing_policy_count = (
        await db.execute(
            select(func.count(RoutingPolicy.id)).where(
                RoutingPolicy.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    return {
        "workspace_id": str(workspace.id),
        "routes": {
            "total_active": total_routes,
            "with_cost_caps": routes_with_cost_caps,
            "with_rate_limits": rate_limited_routes,
            "distinct_models": distinct_models,
            "routing_policies": routing_policy_count,
        },
        "spend": {
            "total_30d_usd": float(total_spend_rows),
            "total_requests_30d": total_requests_30d,
        },
        "budgets": {
            "active_count": budget_count,
            "override_count": override_count,
            "active_overrides": active_overrides,
        },
        "notifications": {
            "active_channels": notification_count,
        },
        "billing": {
            "open_periods": open_periods,
            "total_periods": total_periods,
        },
        "chargeback": {
            "rule_count": chargeback_rule_count,
        },
    }


@router.get("/user-gateway-posture")
async def user_gateway_posture(
    user_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    from runledger_api.models.gateway import GatewayRequest

    now = datetime.now(UTC)
    thirty_days_ago = now - timedelta(days=30)

    total_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
            )
        )
    ).scalar() or 0

    rate_limited_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
                GatewayRoute.per_user_rpm_limit.isnot(None),
            )
        )
    ).scalar() or 0

    guardrail_count = (
        await db.execute(
            select(func.count(GuardrailRule.id)).where(
                GuardrailRule.workspace_id == workspace.id,
                GuardrailRule.status == "active",
            )
        )
    ).scalar() or 0

    routing_policies = (
        await db.execute(
            select(func.count(RoutingPolicy.id)).where(
                RoutingPolicy.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    api_key_count = (
        await db.execute(
            select(func.count(ApiKey.id)).where(
                ApiKey.workspace_id == workspace.id,
                ApiKey.revoked_at.is_(None),
            )
        )
    ).scalar() or 0

    user_request_count = (
        await db.execute(
            select(func.count(GatewayRequest.id)).where(
                GatewayRequest.workspace_id == workspace.id,
                GatewayRequest.created_at >= thirty_days_ago,
            )
        )
    ).scalar() or 0

    return {
        "workspace_id": str(workspace.id),
        "user_id": str(user_id),
        "gateway": {
            "active_routes": total_routes,
            "rate_limited_routes": rate_limited_routes,
            "routing_policies": routing_policies,
            "requests_30d": user_request_count,
        },
        "guardrails": {
            "active_rules": guardrail_count,
        },
        "identity": {
            "api_keys": api_key_count,
        },
    }


@router.get("/provider-profile-observe-posture")
async def provider_profile_observe_posture(
    profile_id: uuid.UUID = Query(..., description="Provider pricing profile UUID"),
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    profile = (
        await db.execute(
            select(ProviderPricing).where(
                ProviderPricing.id == profile_id,
                or_(
                    ProviderPricing.workspace_id == workspace.id,
                    ProviderPricing.workspace_id.is_(None),
                ),
            )
        )
    ).scalar_one_or_none()
    if profile is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "Provider profile not found")

    since = datetime.now(UTC) - timedelta(days=30)

    call_stmt = select(
        func.count(ProviderCall.id).label("request_count"),
        func.coalesce(func.sum(ProviderCall.cost_usd), 0).label("total_cost"),
        func.coalesce(func.sum(ProviderCall.input_tokens), 0).label("input_tokens"),
        func.coalesce(func.sum(ProviderCall.output_tokens), 0).label("output_tokens"),
        func.coalesce(func.sum(ProviderCall.savings_usd), 0).label("total_savings"),
    ).where(
        ProviderCall.workspace_id == workspace.id,
        ProviderCall.provider == profile.provider,
        ProviderCall.model == profile.model,
        ProviderCall.created_at >= since,
    )
    call_row = (await db.execute(call_stmt)).one()

    run_count = (
        await db.execute(
            select(func.count(func.distinct(ProviderCall.run_id))).where(
                ProviderCall.workspace_id == workspace.id,
                ProviderCall.provider == profile.provider,
                ProviderCall.model == profile.model,
                ProviderCall.created_at >= since,
            )
        )
    ).scalar() or 0

    error_count = (
        await db.execute(
            select(func.count(ProviderCall.id)).where(
                ProviderCall.workspace_id == workspace.id,
                ProviderCall.provider == profile.provider,
                ProviderCall.model == profile.model,
                ProviderCall.created_at >= since,
                ProviderCall.status != "success",
            )
        )
    ).scalar() or 0

    avg_latency = (
        await db.execute(
            select(func.avg(ProviderCall.latency_ms)).where(
                ProviderCall.workspace_id == workspace.id,
                ProviderCall.provider == profile.provider,
                ProviderCall.model == profile.model,
                ProviderCall.created_at >= since,
                ProviderCall.latency_ms.isnot(None),
            )
        )
    ).scalar()

    return {
        "workspace_id": str(workspace.id),
        "profile_id": str(profile_id),
        "provider": profile.provider,
        "model": profile.model,
        "period_days": 30,
        "runs": {
            "run_count": run_count,
            "request_count": call_row.request_count,
            "error_count": error_count,
        },
        "cost": {
            "total_cost_usd": round(float(call_row.total_cost), 6),
            "total_savings_usd": round(float(call_row.total_savings), 6),
        },
        "tokens": {
            "input_tokens": int(call_row.input_tokens),
            "output_tokens": int(call_row.output_tokens),
        },
        "performance": {
            "avg_latency_ms": round(float(avg_latency), 1) if avg_latency else None,
        },
    }


@router.get("/gateway-observe-posture")
async def gateway_observe_posture(
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    from runledger_api.models.gateway import GatewayRequest

    since = datetime.now(UTC) - timedelta(days=30)

    total_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
            )
        )
    ).scalar() or 0

    cache_enabled = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
                GatewayRoute.semantic_cache_enabled.is_(True),
            )
        )
    ).scalar() or 0

    rate_limited = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
                GatewayRoute.per_user_rpm_limit.isnot(None),
                GatewayRoute.per_user_rpm_limit > 0,
            )
        )
    ).scalar() or 0

    req_stmt = select(
        func.count(GatewayRequest.id).label("total_requests"),
        func.coalesce(func.sum(case((GatewayRequest.cache_hit.is_(True), 1), else_=0)), 0).label(
            "cache_hits"
        ),
        func.coalesce(func.sum(case((GatewayRequest.status != "success", 1), else_=0)), 0).label(
            "errors"
        ),
        func.coalesce(
            func.sum(case((GatewayRequest.decision_reason.like("%throttle%"), 1), else_=0)), 0
        ).label("throttled"),
        func.coalesce(func.sum(GatewayRequest.input_tokens), 0).label("input_tokens"),
        func.coalesce(func.sum(GatewayRequest.output_tokens), 0).label("output_tokens"),
        func.avg(GatewayRequest.latency_ms).label("avg_latency"),
    ).where(
        GatewayRequest.workspace_id == workspace.id,
        GatewayRequest.created_at >= since,
    )
    req_row = (await db.execute(req_stmt)).one()

    total_requests = req_row.total_requests
    cache_hits = int(req_row.cache_hits)
    cache_misses = total_requests - cache_hits

    run_count = (
        await db.execute(
            select(func.count(AgentRun.id)).where(
                AgentRun.workspace_id == workspace.id,
                AgentRun.started_at >= since,
            )
        )
    ).scalar() or 0

    distinct_users = (
        await db.execute(
            select(func.count(func.distinct(AgentRun.end_user_id))).where(
                AgentRun.workspace_id == workspace.id,
                AgentRun.started_at >= since,
                AgentRun.end_user_id.isnot(None),
            )
        )
    ).scalar() or 0

    distinct_models = (
        await db.execute(
            select(func.count(func.distinct(GatewayRequest.model_used))).where(
                GatewayRequest.workspace_id == workspace.id,
                GatewayRequest.created_at >= since,
                GatewayRequest.model_used.isnot(None),
            )
        )
    ).scalar() or 0

    cost_stmt = select(
        func.coalesce(func.sum(ProviderCall.cost_usd), 0).label("total_cost"),
        func.coalesce(func.sum(ProviderCall.savings_usd), 0).label("total_savings"),
    ).where(
        ProviderCall.workspace_id == workspace.id,
        ProviderCall.created_at >= since,
    )
    cost_row = (await db.execute(cost_stmt)).one()

    return {
        "workspace_id": str(workspace.id),
        "period_days": 30,
        "routes": {
            "active_routes": total_routes,
            "cache_enabled": cache_enabled,
            "rate_limited": rate_limited,
        },
        "traffic": {
            "total_requests": total_requests,
            "cache_hits": cache_hits,
            "cache_misses": cache_misses,
            "cache_hit_rate": round(cache_hits / total_requests, 4) if total_requests > 0 else 0,
            "throttled_requests": int(req_row.throttled),
            "throttle_rate": round(int(req_row.throttled) / total_requests, 4)
            if total_requests > 0
            else 0,
            "errors": int(req_row.errors),
        },
        "runs": {
            "run_count": run_count,
            "distinct_users": distinct_users,
            "distinct_models": distinct_models,
        },
        "cost": {
            "total_cost_usd": round(float(cost_row.total_cost), 6),
            "total_savings_usd": round(float(cost_row.total_savings), 6),
        },
        "tokens": {
            "input_tokens": int(req_row.input_tokens),
            "output_tokens": int(req_row.output_tokens),
        },
        "performance": {
            "avg_latency_ms": round(float(req_row.avg_latency), 1) if req_row.avg_latency else None,
        },
    }


@router.get("/guardrails-observe-posture")
async def guardrails_observe_posture(
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    since = datetime.now(UTC) - timedelta(days=30)

    total_rules = (
        await db.execute(
            select(func.count(GuardrailRule.id)).where(
                GuardrailRule.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    active_rules = (
        await db.execute(
            select(func.count(GuardrailRule.id)).where(
                GuardrailRule.workspace_id == workspace.id,
                GuardrailRule.status == "active",
            )
        )
    ).scalar() or 0

    event_stmt = select(
        func.count(GuardrailEvent.id).label("total_evaluations"),
        func.coalesce(func.sum(case((GuardrailEvent.decision == "block", 1), else_=0)), 0).label(
            "blocks"
        ),
        func.coalesce(func.sum(case((GuardrailEvent.decision == "modify", 1), else_=0)), 0).label(
            "modifications"
        ),
        func.coalesce(func.sum(case((GuardrailEvent.decision == "allow", 1), else_=0)), 0).label(
            "allows"
        ),
        func.avg(GuardrailEvent.latency_ms).label("avg_latency"),
        func.max(GuardrailEvent.latency_ms).label("max_latency"),
        func.count(func.distinct(GuardrailEvent.guardrail_rule_id)).label("distinct_rules_fired"),
        func.count(func.distinct(GuardrailEvent.model)).label("distinct_models"),
    ).where(
        GuardrailEvent.workspace_id == workspace.id,
        GuardrailEvent.created_at >= since,
    )
    row = (await db.execute(event_stmt)).one()

    total_evaluations = row.total_evaluations
    blocks = int(row.blocks)
    modifications = int(row.modifications)
    allows = int(row.allows)

    false_positive_count = (
        await db.execute(
            select(func.count(GuardrailEvent.id)).where(
                GuardrailEvent.workspace_id == workspace.id,
                GuardrailEvent.created_at >= since,
                GuardrailEvent.is_false_positive.is_(True),
            )
        )
    ).scalar() or 0

    pre_call = (
        await db.execute(
            select(func.count(GuardrailEvent.id)).where(
                GuardrailEvent.workspace_id == workspace.id,
                GuardrailEvent.created_at >= since,
                GuardrailEvent.mode == "pre_call",
            )
        )
    ).scalar() or 0

    post_call = (
        await db.execute(
            select(func.count(GuardrailEvent.id)).where(
                GuardrailEvent.workspace_id == workspace.id,
                GuardrailEvent.created_at >= since,
                GuardrailEvent.mode == "post_call",
            )
        )
    ).scalar() or 0

    return {
        "workspace_id": str(workspace.id),
        "period_days": 30,
        "rules": {
            "total_rules": total_rules,
            "active_rules": active_rules,
        },
        "evaluations": {
            "total": total_evaluations,
            "blocks": blocks,
            "modifications": modifications,
            "allows": allows,
            "block_rate": round(blocks / total_evaluations, 4) if total_evaluations > 0 else 0,
            "modification_rate": round(modifications / total_evaluations, 4)
            if total_evaluations > 0
            else 0,
            "distinct_rules_fired": int(row.distinct_rules_fired),
            "distinct_models": int(row.distinct_models),
        },
        "mode_breakdown": {
            "pre_call": pre_call,
            "post_call": post_call,
        },
        "feedback": {
            "false_positive_count": false_positive_count,
        },
        "performance": {
            "avg_latency_ms": round(float(row.avg_latency), 1) if row.avg_latency else None,
            "max_latency_ms": round(float(row.max_latency), 1) if row.max_latency else None,
        },
    }


@router.get("/gateway-safety-posture")
async def gateway_safety_posture(
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):

    since = datetime.now(UTC) - timedelta(days=30)

    tool_policy_count = (
        await db.execute(
            select(func.count(ToolPolicy.id)).where(ToolPolicy.workspace_id == workspace.id)
        )
    ).scalar() or 0

    active_tool_policies = (
        await db.execute(
            select(func.count(ToolPolicy.id)).where(
                ToolPolicy.workspace_id == workspace.id,
                ToolPolicy.is_active.is_(True),
            )
        )
    ).scalar() or 0

    approval_count = (
        await db.execute(
            select(func.count(Approval.id)).where(
                Approval.workspace_id == workspace.id,
                Approval.created_at >= since,
            )
        )
    ).scalar() or 0

    pending_approvals = (
        await db.execute(
            select(func.count(Approval.id)).where(
                Approval.workspace_id == workspace.id,
                Approval.status == "pending",
            )
        )
    ).scalar() or 0

    audit_event_count = (
        await db.execute(
            select(func.count(AuditEvent.id)).where(
                AuditEvent.workspace_id == workspace.id,
                AuditEvent.created_at >= since,
            )
        )
    ).scalar() or 0

    gateway_audit_events = (
        await db.execute(
            select(func.count(AuditEvent.id)).where(
                AuditEvent.workspace_id == workspace.id,
                AuditEvent.created_at >= since,
                or_(
                    AuditEvent.resource_type.in_(
                        [
                            "gateway_route",
                            "routing_policy",
                            "provider_profile",
                            "guardrail_rule",
                            "response_cache_config",
                        ]
                    ),
                    AuditEvent.action.like("gateway%"),
                ),
            )
        )
    ).scalar() or 0

    alert_rule_count = (
        await db.execute(
            select(func.count(AlertRule.id)).where(AlertRule.workspace_id == workspace.id)
        )
    ).scalar() or 0

    active_alert_rules = (
        await db.execute(
            select(func.count(AlertRule.id)).where(
                AlertRule.workspace_id == workspace.id,
                AlertRule.is_active.is_(True),
            )
        )
    ).scalar() or 0

    tag_count = (
        await db.execute(select(func.count(Tag.id)).where(Tag.workspace_id == workspace.id))
    ).scalar() or 0

    guardrail_count = (
        await db.execute(
            select(func.count(GuardrailRule.id)).where(
                GuardrailRule.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    active_guardrails = (
        await db.execute(
            select(func.count(GuardrailRule.id)).where(
                GuardrailRule.workspace_id == workspace.id,
                GuardrailRule.status == "active",
            )
        )
    ).scalar() or 0

    guardrail_blocks_30d = (
        await db.execute(
            select(func.count(GuardrailEvent.id)).where(
                GuardrailEvent.workspace_id == workspace.id,
                GuardrailEvent.created_at >= since,
                GuardrailEvent.decision == "block",
            )
        )
    ).scalar() or 0

    active_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
            )
        )
    ).scalar() or 0

    cache_enabled_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
                GatewayRoute.semantic_cache_enabled.is_(True),
            )
        )
    ).scalar() or 0

    rate_limited_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
                GatewayRoute.per_user_rpm_limit.isnot(None),
                GatewayRoute.per_user_rpm_limit > 0,
            )
        )
    ).scalar() or 0

    mcp_server_count = (
        await db.execute(
            select(func.count(McpServer.id)).where(McpServer.workspace_id == workspace.id)
        )
    ).scalar() or 0

    return {
        "workspace_id": str(workspace.id),
        "period_days": 30,
        "gateway_context": {
            "active_routes": active_routes,
            "cache_enabled_routes": cache_enabled_routes,
            "rate_limited_routes": rate_limited_routes,
            "guardrail_rules": guardrail_count,
            "active_guardrails": active_guardrails,
            "guardrail_blocks_30d": guardrail_blocks_30d,
        },
        "tool_governance": {
            "tool_policy_count": tool_policy_count,
            "active_tool_policies": active_tool_policies,
            "mcp_server_count": mcp_server_count,
        },
        "approvals": {
            "total_30d": approval_count,
            "pending": pending_approvals,
        },
        "audit": {
            "total_events_30d": audit_event_count,
            "gateway_events_30d": gateway_audit_events,
        },
        "alert_rules": {
            "total": alert_rule_count,
            "active": active_alert_rules,
        },
        "tags": {
            "total": tag_count,
        },
    }


@router.get("/gateway-build-posture")
async def gateway_build_posture(
    request: Request,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):

    active_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
            )
        )
    ).scalar() or 0

    routing_policy_count = (
        await db.execute(
            select(func.count(RoutingPolicy.id)).where(RoutingPolicy.workspace_id == workspace.id)
        )
    ).scalar() or 0

    guardrail_count = (
        await db.execute(
            select(func.count(GuardrailRule.id)).where(
                GuardrailRule.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    active_guardrails = (
        await db.execute(
            select(func.count(GuardrailRule.id)).where(
                GuardrailRule.workspace_id == workspace.id,
                GuardrailRule.status == "active",
            )
        )
    ).scalar() or 0

    prompt_count = (
        await db.execute(select(func.count(Prompt.id)).where(Prompt.workspace_id == workspace.id))
    ).scalar() or 0

    agent_count = (
        await db.execute(select(func.count(Agent.id)).where(Agent.workspace_id == workspace.id))
    ).scalar() or 0

    workflow_count = (
        await db.execute(
            select(func.count(WorkflowDefinition.id)).where(
                WorkflowDefinition.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    workflow_run_count = (
        await db.execute(
            select(func.count(WorkflowRun.id)).where(WorkflowRun.workspace_id == workspace.id)
        )
    ).scalar() or 0

    eval_dataset_count = (
        await db.execute(
            select(func.count(EvalDataset.id)).where(EvalDataset.workspace_id == workspace.id)
        )
    ).scalar() or 0

    eval_experiment_count = (
        await db.execute(
            select(func.count(EvalExperiment.id)).where(EvalExperiment.workspace_id == workspace.id)
        )
    ).scalar() or 0

    replay_dataset_count = (
        await db.execute(
            select(func.count(ReplayDataset.id)).where(ReplayDataset.workspace_id == workspace.id)
        )
    ).scalar() or 0

    replay_experiment_count = (
        await db.execute(
            select(func.count(ReplayExperiment.id)).where(
                ReplayExperiment.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    return {
        "workspace_id": str(workspace.id),
        "gateway_context": {
            "active_routes": active_routes,
            "routing_policies": routing_policy_count,
            "guardrail_rules": guardrail_count,
            "active_guardrails": active_guardrails,
        },
        "prompts": {
            "total": prompt_count,
        },
        "agents": {
            "total": agent_count,
        },
        "workflows": {
            "total": workflow_count,
            "runs": workflow_run_count,
        },
        "evaluation": {
            "datasets": eval_dataset_count,
            "experiments": eval_experiment_count,
        },
        "replay": {
            "datasets": replay_dataset_count,
            "experiments": replay_experiment_count,
        },
    }


@router.get("/performance-controls-org-posture")
async def performance_controls_org_posture(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _user: TenantUser = Depends(get_current_user),
    _rl: None = Depends(analytics_rate_limit),
):
    cache_profiles = (
        await db.execute(
            select(func.count(ResponseCacheConfig.id)).where(
                ResponseCacheConfig.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    cache_enabled = (
        await db.execute(
            select(func.count(ResponseCacheConfig.id)).where(
                ResponseCacheConfig.workspace_id == workspace.id,
                ResponseCacheConfig.is_enabled.is_(True),
            )
        )
    ).scalar() or 0

    cache_enabled_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
                GatewayRoute.semantic_cache_enabled.is_(True),
            )
        )
    ).scalar() or 0

    api_key_count = (
        await db.execute(
            select(func.count(ApiKey.id)).where(
                ApiKey.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    routes_with_rpm = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
                GatewayRoute.per_user_rpm_limit.isnot(None),
            )
        )
    ).scalar() or 0

    passthrough_with_rpm = (
        await db.execute(
            select(func.count(GatewayPassThroughEndpoint.id)).where(
                GatewayPassThroughEndpoint.workspace_id == workspace.id,
                GatewayPassThroughEndpoint.is_active.is_(True),
                GatewayPassThroughEndpoint.rate_limit_rpm.isnot(None),
            )
        )
    ).scalar() or 0

    active_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
            )
        )
    ).scalar() or 0

    access_group_count = (
        await db.execute(
            select(func.count(AccessGroup.id)).where(
                AccessGroup.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    return {
        "workspace_id": str(workspace.id),
        "cache_context": {
            "profiles": cache_profiles,
            "enabled_profiles": cache_enabled,
            "cache_enabled_routes": cache_enabled_routes,
            "api_keys": api_key_count,
        },
        "rate_limit_context": {
            "routes_with_rpm": routes_with_rpm,
            "passthrough_with_rpm": passthrough_with_rpm,
            "active_routes": active_routes,
            "access_groups": access_group_count,
        },
        "platform_context": {
            "workspace_scoped": True,
            "cache_profiles_configured": cache_profiles > 0,
            "throttle_configured": routes_with_rpm > 0 or passthrough_with_rpm > 0,
        },
    }


@router.get("/gateway-internal-posture")
async def gateway_internal_posture(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _user: TenantUser = Depends(get_current_user),
    _rl: None = Depends(analytics_rate_limit),
):
    active_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
            )
        )
    ).scalar() or 0

    cache_enabled_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
                GatewayRoute.semantic_cache_enabled.is_(True),
            )
        )
    ).scalar() or 0

    rate_limited_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
                GatewayRoute.per_user_rpm_limit.isnot(None),
            )
        )
    ).scalar() or 0

    guardrail_rules = (
        await db.execute(
            select(func.count(GuardrailRule.id)).where(
                GuardrailRule.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    active_guardrails = (
        await db.execute(
            select(func.count(GuardrailRule.id)).where(
                GuardrailRule.workspace_id == workspace.id,
                GuardrailRule.status == "active",
            )
        )
    ).scalar() or 0

    cache_profiles = (
        await db.execute(
            select(func.count(ResponseCacheConfig.id)).where(
                ResponseCacheConfig.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    routing_policies = (
        await db.execute(
            select(func.count(RoutingPolicy.id)).where(
                RoutingPolicy.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    provider_count = (
        await db.execute(
            select(func.count(func.distinct(GatewayRoute.provider))).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
            )
        )
    ).scalar() or 0

    passthrough_count = (
        await db.execute(
            select(func.count(GatewayPassThroughEndpoint.id)).where(
                GatewayPassThroughEndpoint.workspace_id == workspace.id,
                GatewayPassThroughEndpoint.is_active.is_(True),
            )
        )
    ).scalar() or 0

    return {
        "workspace_id": str(workspace.id),
        "gateway_family": {
            "active_routes": active_routes,
            "providers": provider_count,
            "routing_policies": routing_policies,
            "passthrough_endpoints": passthrough_count,
        },
        "guardrail_context": {
            "rules": guardrail_rules,
            "active": active_guardrails,
        },
        "cache_context": {
            "profiles": cache_profiles,
            "cache_enabled_routes": cache_enabled_routes,
        },
        "throttle_context": {
            "rate_limited_routes": rate_limited_routes,
        },
        "platform_visibility": {
            "workspace_scoped": True,
            "provider_count": provider_count,
            "guardrails_active": active_guardrails > 0,
            "cache_configured": cache_profiles > 0,
            "throttle_configured": rate_limited_routes > 0,
        },
    }


@router.get("/response-cache-economics-posture")
async def response_cache_economics_posture(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _user: TenantUser = Depends(get_current_user),
    _rl: None = Depends(analytics_rate_limit),
):
    cache_profiles = (
        await db.execute(
            select(func.count(ResponseCacheConfig.id)).where(
                ResponseCacheConfig.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    cache_enabled_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
                GatewayRoute.semantic_cache_enabled.is_(True),
            )
        )
    ).scalar() or 0

    active_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
            )
        )
    ).scalar() or 0

    budgets = (
        await db.execute(
            select(func.count(Budget.id)).where(
                Budget.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    budget_overrides = (
        await db.execute(
            select(func.count(BudgetOverride.id)).where(
                BudgetOverride.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    budget_notifications = (
        await db.execute(
            select(func.count(BudgetNotification.id)).where(
                BudgetNotification.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    billing_periods = (
        await db.execute(
            select(func.count(BillingPeriod.id)).where(
                BillingPeriod.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    audit_events_30d = (
        await db.execute(
            select(func.count(AuditEvent.id)).where(
                AuditEvent.workspace_id == workspace.id,
                AuditEvent.created_at >= func.now() - text("interval '30 days'"),
            )
        )
    ).scalar() or 0

    ledger_snapshots = (
        await db.execute(
            select(func.count(LedgerSnapshot.id)).where(
                LedgerSnapshot.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    users_count = (
        await db.execute(
            select(func.count(TenantUser.id)).where(
                TenantUser.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    return {
        "workspace_id": str(workspace.id),
        "cache_context": {
            "profiles": cache_profiles,
            "cache_enabled_routes": cache_enabled_routes,
            "active_routes": active_routes,
        },
        "finops_context": {
            "budgets": budgets,
            "budget_overrides": budget_overrides,
            "budget_notifications": budget_notifications,
            "billing_periods": billing_periods,
            "ledger_snapshots": ledger_snapshots,
        },
        "governance_context": {
            "audit_events_30d": audit_events_30d,
        },
        "org_context": {
            "users": users_count,
        },
    }


@router.get("/rate-limit-scope-posture")
async def rate_limit_scope_posture(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _user: TenantUser = Depends(get_current_user),
    _rl: None = Depends(analytics_rate_limit),
):
    routes_with_rpm = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
                GatewayRoute.per_user_rpm_limit.isnot(None),
            )
        )
    ).scalar() or 0

    active_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
            )
        )
    ).scalar() or 0

    passthrough_with_rpm = (
        await db.execute(
            select(func.count(GatewayPassThroughEndpoint.id)).where(
                GatewayPassThroughEndpoint.workspace_id == workspace.id,
                GatewayPassThroughEndpoint.rpm_limit.isnot(None),
            )
        )
    ).scalar() or 0

    access_groups = (
        await db.execute(
            select(func.count(AccessGroup.id)).where(
                AccessGroup.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    budgets = (
        await db.execute(
            select(func.count(Budget.id)).where(
                Budget.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    budget_notifications = (
        await db.execute(
            select(func.count(BudgetNotification.id)).where(
                BudgetNotification.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    chargeback_rules = (
        await db.execute(
            select(func.count(ChargebackRule.id)).where(
                ChargebackRule.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    ledger_snapshots = (
        await db.execute(
            select(func.count(LedgerSnapshot.id)).where(
                LedgerSnapshot.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    monitoring_alerts = (
        await db.execute(
            select(func.count(AlertRule.id)).where(
                AlertRule.workspace_id == workspace.id,
                AlertRule.is_active.is_(True),
            )
        )
    ).scalar() or 0

    routing_policies = (
        await db.execute(
            select(func.count(RoutingPolicy.id)).where(
                RoutingPolicy.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    return {
        "workspace_id": str(workspace.id),
        "throttle_context": {
            "routes_with_rpm": routes_with_rpm,
            "active_routes": active_routes,
            "passthrough_with_rpm": passthrough_with_rpm,
            "routing_policies": routing_policies,
        },
        "scope_context": {
            "access_groups": access_groups,
            "monitoring_alerts": monitoring_alerts,
        },
        "finops_context": {
            "budgets": budgets,
            "budget_notifications": budget_notifications,
            "chargeback_rules": chargeback_rules,
            "ledger_snapshots": ledger_snapshots,
        },
    }


@router.get("/guardrails-finops-posture")
async def guardrails_finops_posture(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _user: TenantUser = Depends(get_current_user),
    _rl: None = Depends(analytics_rate_limit),
):
    thirty_days_ago = func.now() - text("interval '30 days'")

    guardrail_blocks_30d = (
        await db.execute(
            select(func.count(GuardrailEvent.id)).where(
                GuardrailEvent.workspace_id == workspace.id,
                GuardrailEvent.decision == "block",
                GuardrailEvent.created_at >= thirty_days_ago,
            )
        )
    ).scalar() or 0

    guardrail_evals_30d = (
        await db.execute(
            select(func.count(GuardrailEvent.id)).where(
                GuardrailEvent.workspace_id == workspace.id,
                GuardrailEvent.created_at >= thirty_days_ago,
            )
        )
    ).scalar() or 0

    active_rules = (
        await db.execute(
            select(func.count(GuardrailRule.id)).where(
                GuardrailRule.workspace_id == workspace.id,
                GuardrailRule.status == "active",
            )
        )
    ).scalar() or 0

    budgets = (
        await db.execute(
            select(func.count(Budget.id)).where(
                Budget.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    budget_notifications = (
        await db.execute(
            select(func.count(BudgetNotification.id)).where(
                BudgetNotification.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    billing_periods = (
        await db.execute(
            select(func.count(BillingPeriod.id)).where(
                BillingPeriod.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    chargeback_rules = (
        await db.execute(
            select(func.count(ChargebackRule.id)).where(
                ChargebackRule.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    active_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
            )
        )
    ).scalar() or 0

    return {
        "workspace_id": str(workspace.id),
        "period_days": 30,
        "guardrail_context": {
            "active_rules": active_rules,
            "evaluations_30d": guardrail_evals_30d,
            "blocks_30d": guardrail_blocks_30d,
            "active_routes": active_routes,
        },
        "finops_context": {
            "budgets": budgets,
            "budget_notifications": budget_notifications,
            "billing_periods": billing_periods,
            "chargeback_rules": chargeback_rules,
        },
    }


@router.get("/gateway-control-plane-posture")
async def gateway_control_plane_posture(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _user: TenantUser = Depends(get_current_user),
    _rl: None = Depends(analytics_rate_limit),
):
    users_count = (
        await db.execute(
            select(func.count(TenantUser.id)).where(
                TenantUser.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    access_groups = (
        await db.execute(
            select(func.count(AccessGroup.id)).where(
                AccessGroup.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    api_keys = (
        await db.execute(
            select(func.count(ApiKey.id)).where(
                ApiKey.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    active_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
            )
        )
    ).scalar() or 0

    routing_policies = (
        await db.execute(
            select(func.count(RoutingPolicy.id)).where(
                RoutingPolicy.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    approvals_pending = (
        await db.execute(
            select(func.count(Approval.id)).where(
                Approval.workspace_id == workspace.id,
                Approval.status == "pending",
            )
        )
    ).scalar() or 0

    audit_events_30d = (
        await db.execute(
            select(func.count(AuditEvent.id)).where(
                AuditEvent.workspace_id == workspace.id,
                AuditEvent.created_at >= func.now() - text("interval '30 days'"),
            )
        )
    ).scalar() or 0

    active_guardrails = (
        await db.execute(
            select(func.count(GuardrailRule.id)).where(
                GuardrailRule.workspace_id == workspace.id,
                GuardrailRule.status == "active",
            )
        )
    ).scalar() or 0

    monitoring_alerts = (
        await db.execute(
            select(func.count(AlertRule.id)).where(
                AlertRule.workspace_id == workspace.id,
                AlertRule.is_active.is_(True),
            )
        )
    ).scalar() or 0

    provider_profiles = (
        await db.execute(
            select(func.count(ProviderPricing.id)).where(
                ProviderPricing.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    return {
        "workspace_id": str(workspace.id),
        "org_context": {
            "users": users_count,
            "access_groups": access_groups,
            "api_keys": api_keys,
        },
        "gateway_context": {
            "active_routes": active_routes,
            "routing_policies": routing_policies,
            "provider_profiles": provider_profiles,
            "active_guardrails": active_guardrails,
        },
        "observe_context": {
            "monitoring_alerts": monitoring_alerts,
        },
        "governance_context": {
            "approvals_pending": approvals_pending,
            "audit_events_30d": audit_events_30d,
        },
    }


@router.get("/provider-profile-runtime-posture")
async def provider_profile_runtime_posture(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _user: TenantUser = Depends(get_current_user),
    _rl: None = Depends(analytics_rate_limit),
):
    budget_notifications = (
        await db.execute(
            select(func.count(BudgetNotification.id)).where(
                BudgetNotification.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    ledger_snapshots = (
        await db.execute(
            select(func.count(LedgerSnapshot.id)).where(
                LedgerSnapshot.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    users_count = (
        await db.execute(
            select(func.count(TenantUser.id)).where(
                TenantUser.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    mcp_servers = (
        await db.execute(
            select(func.count(McpServer.id)).where(
                McpServer.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    search_tools = (
        await db.execute(
            select(func.count(SearchTool.id)).where(
                SearchTool.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    capture_policies = (
        await db.execute(
            select(func.count(CapturePolicy.id)).where(
                CapturePolicy.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    monitoring_alerts = (
        await db.execute(
            select(func.count(AlertRule.id)).where(
                AlertRule.workspace_id == workspace.id,
                AlertRule.is_active.is_(True),
            )
        )
    ).scalar() or 0

    provider_profiles = (
        await db.execute(
            select(func.count(ProviderPricing.id)).where(
                ProviderPricing.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    return {
        "workspace_id": str(workspace.id),
        "provider_profiles": provider_profiles,
        "finops_context": {
            "budget_notifications": budget_notifications,
            "ledger_snapshots": ledger_snapshots,
        },
        "org_context": {
            "users": users_count,
            "workspace_scoped": True,
        },
        "observe_context": {
            "monitoring_alerts": monitoring_alerts,
        },
        "governance_context": {
            "mcp_servers": mcp_servers,
            "search_tools": search_tools,
            "capture_policies": capture_policies,
        },
    }


@router.get("/investigation-access-group-posture")
async def investigation_access_group_posture(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _user: TenantUser = Depends(get_current_user),
    _rl: None = Depends(analytics_rate_limit),
):
    t_from = _default_from()
    t_to = _default_to()

    access_groups = (
        await db.execute(
            select(func.count(AccessGroup.id)).where(
                AccessGroup.workspace_id == workspace.id,
                AccessGroup.is_active.is_(True),
            )
        )
    ).scalar() or 0

    access_group_members = (
        await db.execute(
            select(func.count(AccessGroupMember.id)).where(
                AccessGroupMember.group_id.in_(
                    select(AccessGroup.id).where(
                        AccessGroup.workspace_id == workspace.id,
                        AccessGroup.is_active.is_(True),
                    )
                )
            )
        )
    ).scalar() or 0

    total_runs_30d = (
        await db.execute(
            select(func.count(AgentRun.id)).where(
                AgentRun.workspace_id == workspace.id,
                AgentRun.started_at >= t_from,
                AgentRun.started_at < t_to,
            )
        )
    ).scalar() or 0

    total_requests_30d = (
        await db.execute(
            select(func.count(ProviderCall.id)).where(
                ProviderCall.workspace_id == workspace.id,
                ProviderCall.created_at >= t_from,
                ProviderCall.created_at < t_to,
            )
        )
    ).scalar() or 0

    active_users = (
        await db.execute(
            select(func.count(ProviderCall.end_user_id.distinct())).where(
                ProviderCall.workspace_id == workspace.id,
                ProviderCall.created_at >= t_from,
                ProviderCall.created_at < t_to,
            )
        )
    ).scalar() or 0

    active_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
            )
        )
    ).scalar() or 0

    return {
        "workspace_id": str(workspace.id),
        "period_days": 30,
        "access_group_context": {
            "access_groups": access_groups,
            "total_members": access_group_members,
        },
        "investigation_context": {
            "runs_30d": total_runs_30d,
            "requests_30d": total_requests_30d,
            "active_users": active_users,
            "active_routes": active_routes,
        },
    }


@router.get("/investigation-finops-budget-posture", response_model=InvestigationFinopsBudgetPosture)
async def investigation_finops_budget_posture(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _user: TenantUser = Depends(get_current_user),
    _rl: None = Depends(analytics_rate_limit),
):
    t_from = _default_from()
    t_to = _default_to()

    budget_count = (
        await db.execute(
            select(func.count(Budget.id)).where(
                Budget.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    active_budgets = (
        await db.execute(
            select(func.count(Budget.id)).where(
                Budget.workspace_id == workspace.id,
                Budget.is_active.is_(True),
            )
        )
    ).scalar() or 0

    total_limit = (
        await db.execute(
            select(func.coalesce(func.sum(Budget.limit_usd), 0)).where(
                Budget.workspace_id == workspace.id,
                Budget.is_active.is_(True),
            )
        )
    ).scalar() or 0

    breach_count = (
        await db.execute(
            select(func.count(Budget.id)).where(
                Budget.workspace_id == workspace.id,
                Budget.is_active.is_(True),
                Budget.id == BudgetBreach.budget_id,
            )
        )
    ).scalar() or 0

    override_count = (
        await db.execute(
            select(func.count(BudgetOverride.id)).where(
                BudgetOverride.budget_id.in_(
                    select(Budget.id).where(Budget.workspace_id == workspace.id)
                )
            )
        )
    ).scalar() or 0

    active_overrides = (
        await db.execute(
            select(func.count(BudgetOverride.id)).where(
                BudgetOverride.budget_id.in_(
                    select(Budget.id).where(Budget.workspace_id == workspace.id)
                ),
                BudgetOverride.status == "active",
            )
        )
    ).scalar() or 0

    billing_period_count = (
        await db.execute(
            select(func.count(BillingPeriod.id)).where(
                BillingPeriod.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    open_billing_periods = (
        await db.execute(
            select(func.count(BillingPeriod.id)).where(
                BillingPeriod.workspace_id == workspace.id,
                BillingPeriod.status == "open",
            )
        )
    ).scalar() or 0

    chargeback_rule_count = (
        await db.execute(
            select(func.count(ChargebackRule.id)).where(
                ChargebackRule.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    total_spend_30d = (
        await db.execute(
            select(func.coalesce(func.sum(ProviderCall.cost_usd), 0)).where(
                ProviderCall.workspace_id == workspace.id,
                ProviderCall.created_at >= t_from,
                ProviderCall.created_at < t_to,
            )
        )
    ).scalar() or 0

    total_runs_30d = (
        await db.execute(
            select(func.count(AgentRun.id)).where(
                AgentRun.workspace_id == workspace.id,
                AgentRun.started_at >= t_from,
                AgentRun.started_at < t_to,
            )
        )
    ).scalar() or 0

    return {
        "workspace_id": str(workspace.id),
        "period_days": 30,
        "budget_context": {
            "budgets": budget_count,
            "active_budgets": active_budgets,
            "total_limit_usd": float(total_limit),
            "breach_count": breach_count,
            "overrides": override_count,
            "active_overrides": active_overrides,
        },
        "billing_context": {
            "billing_periods": billing_period_count,
            "open_billing_periods": open_billing_periods,
            "chargeback_rules": chargeback_rule_count,
        },
        "spend_context": {
            "total_spend_30d": float(total_spend_30d),
            "total_runs_30d": total_runs_30d,
        },
    }


@router.get("/overview-finops-budget-posture", response_model=OverviewFinopsBudgetPosture)
async def overview_finops_budget_posture(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _user: TenantUser = Depends(get_current_user),
    _rl: None = Depends(analytics_rate_limit),
):
    t_from = _default_from()
    t_to = _default_to()

    budget_count = (
        await db.execute(select(func.count(Budget.id)).where(Budget.workspace_id == workspace.id))
    ).scalar() or 0

    active_budgets = (
        await db.execute(
            select(func.count(Budget.id)).where(
                Budget.workspace_id == workspace.id,
                Budget.is_active.is_(True),
            )
        )
    ).scalar() or 0

    total_limit = (
        await db.execute(
            select(func.coalesce(func.sum(Budget.limit_usd), 0)).where(
                Budget.workspace_id == workspace.id,
                Budget.is_active.is_(True),
            )
        )
    ).scalar() or 0

    breach_count = (
        await db.execute(
            select(func.count(Budget.id)).where(
                Budget.workspace_id == workspace.id,
                Budget.is_active.is_(True),
                Budget.id == BudgetBreach.budget_id,
            )
        )
    ).scalar() or 0

    override_count = (
        await db.execute(
            select(func.count(BudgetOverride.id)).where(
                BudgetOverride.budget_id.in_(
                    select(Budget.id).where(Budget.workspace_id == workspace.id)
                )
            )
        )
    ).scalar() or 0

    active_overrides = (
        await db.execute(
            select(func.count(BudgetOverride.id)).where(
                BudgetOverride.budget_id.in_(
                    select(Budget.id).where(Budget.workspace_id == workspace.id)
                ),
                BudgetOverride.status == "active",
            )
        )
    ).scalar() or 0

    billing_period_count = (
        await db.execute(
            select(func.count(BillingPeriod.id)).where(BillingPeriod.workspace_id == workspace.id)
        )
    ).scalar() or 0

    open_billing_periods = (
        await db.execute(
            select(func.count(BillingPeriod.id)).where(
                BillingPeriod.workspace_id == workspace.id,
                BillingPeriod.status == "open",
            )
        )
    ).scalar() or 0

    chargeback_rule_count = (
        await db.execute(
            select(func.count(ChargebackRule.id)).where(ChargebackRule.workspace_id == workspace.id)
        )
    ).scalar() or 0

    total_spend_30d = (
        await db.execute(
            select(func.coalesce(func.sum(ProviderCall.cost_usd), 0)).where(
                ProviderCall.workspace_id == workspace.id,
                ProviderCall.created_at >= t_from,
                ProviderCall.created_at < t_to,
            )
        )
    ).scalar() or 0

    total_runs_30d = (
        await db.execute(
            select(func.count(AgentRun.id)).where(
                AgentRun.workspace_id == workspace.id,
                AgentRun.started_at >= t_from,
                AgentRun.started_at < t_to,
            )
        )
    ).scalar() or 0

    notification_count = (
        await db.execute(
            select(func.count(BudgetNotification.id)).where(
                BudgetNotification.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    active_notifications = (
        await db.execute(
            select(func.count(BudgetNotification.id)).where(
                BudgetNotification.workspace_id == workspace.id,
                BudgetNotification.is_active.is_(True),
            )
        )
    ).scalar() or 0

    return {
        "workspace_id": str(workspace.id),
        "period_days": 30,
        "budget_context": {
            "budgets": budget_count,
            "active_budgets": active_budgets,
            "total_limit_usd": float(total_limit),
            "breach_count": breach_count,
            "overrides": override_count,
            "active_overrides": active_overrides,
        },
        "billing_context": {
            "billing_periods": billing_period_count,
            "open_billing_periods": open_billing_periods,
            "chargeback_rules": chargeback_rule_count,
        },
        "spend_context": {
            "total_spend_30d": float(total_spend_30d),
            "total_runs_30d": total_runs_30d,
        },
        "notification_context": {
            "notifications": notification_count,
            "active_notifications": active_notifications,
        },
    }


@router.get("/model-budget-utilization", response_model=ModelBudgetUtilization)
async def model_budget_utilization(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _user: TenantUser = Depends(get_current_user),
    _rl: None = Depends(analytics_rate_limit),
):
    t_from = _default_from()
    t_to = _default_to()

    api_key_ids_result = await db.execute(
        select(ApiKey.id).where(ApiKey.workspace_id == workspace.id)
    )
    api_key_ids = [row[0] for row in api_key_ids_result.fetchall()]

    model_budgets_result = await db.execute(
        select(ModelBudget).where(
            ModelBudget.api_key_id.in_(api_key_ids) if api_key_ids else sa.literal(False)
        )
    )
    model_budgets = model_budgets_result.scalars().all()

    model_spend_result = await db.execute(
        select(
            ProviderCall.model,
            func.coalesce(func.sum(ProviderCall.cost_usd), 0).label("spend"),
            func.count(ProviderCall.id).label("request_count"),
        )
        .where(
            ProviderCall.workspace_id == workspace.id,
            ProviderCall.created_at >= t_from,
            ProviderCall.created_at < t_to,
        )
        .group_by(ProviderCall.model)
    )
    spend_by_model = {
        row.model: (float(row.spend), row.request_count) for row in model_spend_result.fetchall()
    }

    budget_by_pattern: dict[str, ModelBudget] = {}
    for mb in model_budgets:
        budget_by_pattern[mb.model_pattern] = mb

    all_models = set(spend_by_model.keys()) | set(budget_by_pattern.keys())
    items: list[dict] = []
    for model in sorted(all_models):
        spend_info = spend_by_model.get(model, (0.0, 0))
        budget = budget_by_pattern.get(model)
        items.append(
            {
                "model": model,
                "spend_30d": spend_info[0],
                "request_count": spend_info[1],
                "budget_limit_usd": float(budget.max_spend_usd)
                if budget and budget.max_spend_usd
                else None,
                "budget_action": budget.action if budget else None,
                "period_type": budget.period_type if budget else None,
                "is_active": budget.is_active if budget else False,
            }
        )

    total_model_budgets = len(model_budgets)
    active_model_budgets = sum(1 for mb in model_budgets if mb.is_active)

    billing_period_count = (
        await db.execute(
            select(func.count(BillingPeriod.id)).where(BillingPeriod.workspace_id == workspace.id)
        )
    ).scalar() or 0

    open_billing_periods = (
        await db.execute(
            select(func.count(BillingPeriod.id)).where(
                BillingPeriod.workspace_id == workspace.id,
                BillingPeriod.status == "open",
            )
        )
    ).scalar() or 0

    chargeback_rule_count = (
        await db.execute(
            select(func.count(ChargebackRule.id)).where(ChargebackRule.workspace_id == workspace.id)
        )
    ).scalar() or 0

    return {
        "workspace_id": str(workspace.id),
        "period_days": 30,
        "models": items,
        "total_model_budgets": total_model_budgets,
        "active_model_budgets": active_model_budgets,
        "billing_periods": billing_period_count,
        "open_billing_periods": open_billing_periods,
        "chargeback_rules": chargeback_rule_count,
    }


@router.get("/investigation-org-identity-posture", response_model=InvestigationOrgIdentityPosture)
async def investigation_org_identity_posture(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _user: TenantUser = Depends(get_current_user),
    _rl: None = Depends(analytics_rate_limit),
):
    t_from = _default_from()
    t_to = _default_to()

    workspace_user_count = (
        await db.execute(
            select(func.count(WorkspaceUser.id)).where(WorkspaceUser.workspace_id == workspace.id)
        )
    ).scalar() or 0

    distinct_end_users_30d = (
        await db.execute(
            select(func.count(func.distinct(AgentRun.end_user_id))).where(
                AgentRun.workspace_id == workspace.id,
                AgentRun.end_user_id.isnot(None),
                AgentRun.started_at >= t_from,
                AgentRun.started_at < t_to,
            )
        )
    ).scalar() or 0

    api_key_count = (
        await db.execute(select(func.count(ApiKey.id)).where(ApiKey.workspace_id == workspace.id))
    ).scalar() or 0

    active_api_keys = (
        await db.execute(
            select(func.count(ApiKey.id)).where(
                ApiKey.workspace_id == workspace.id,
                ApiKey.revoked_at.is_(None),
            )
        )
    ).scalar() or 0

    api_keys_with_traffic_30d = (
        await db.execute(
            select(func.count(func.distinct(ProviderCall.api_key_id))).where(
                ProviderCall.workspace_id == workspace.id,
                ProviderCall.api_key_id.isnot(None),
                ProviderCall.created_at >= t_from,
                ProviderCall.created_at < t_to,
            )
        )
    ).scalar() or 0

    mcp_server_count = (
        await db.execute(
            select(func.count(McpServer.id)).where(McpServer.workspace_id == workspace.id)
        )
    ).scalar() or 0

    mcp_tool_calls_30d = (
        await db.execute(
            select(func.count(McpToolCall.id)).where(
                McpToolCall.workspace_id == workspace.id,
                McpToolCall.created_at >= t_from,
                McpToolCall.created_at < t_to,
            )
        )
    ).scalar() or 0

    telemetry_batches_30d = (
        await db.execute(
            select(func.count(OtlpIngestBatch.id)).where(
                OtlpIngestBatch.workspace_id == workspace.id,
                OtlpIngestBatch.created_at >= t_from,
                OtlpIngestBatch.created_at < t_to,
            )
        )
    ).scalar() or 0

    total_runs_30d = (
        await db.execute(
            select(func.count(AgentRun.id)).where(
                AgentRun.workspace_id == workspace.id,
                AgentRun.started_at >= t_from,
                AgentRun.started_at < t_to,
            )
        )
    ).scalar() or 0

    return {
        "workspace_id": str(workspace.id),
        "period_days": 30,
        "org_context": {
            "workspace_name": workspace.name,
            "workspace_users": workspace_user_count,
        },
        "user_context": {
            "workspace_users": workspace_user_count,
            "distinct_end_users_30d": distinct_end_users_30d,
            "runs_30d": total_runs_30d,
        },
        "api_key_context": {
            "total_keys": api_key_count,
            "active_keys": active_api_keys,
            "keys_with_traffic_30d": api_keys_with_traffic_30d,
        },
        "telemetry_context": {
            "batches_30d": telemetry_batches_30d,
            "runs_30d": total_runs_30d,
        },
        "mcp_context": {
            "servers": mcp_server_count,
            "tool_calls_30d": mcp_tool_calls_30d,
        },
    }


@router.get(
    "/investigation-gateway-runtime-posture", response_model=InvestigationGatewayRuntimePosture
)
async def investigation_gateway_runtime_posture(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    access_group_id: Annotated[uuid.UUID | None, Query()] = None,
) -> dict[str, Any]:
    from runledger_api.models.gateway import GatewayRequest, PromptCache

    cutoff = datetime.now(UTC) - timedelta(days=30)

    route_count = int(
        (
            await db.execute(
                select(func.count(GatewayRoute.id)).where(GatewayRoute.workspace_id == workspace.id)
            )
        ).scalar()
        or 0
    )
    active_routes = int(
        (
            await db.execute(
                select(func.count(GatewayRoute.id)).where(
                    GatewayRoute.workspace_id == workspace.id, GatewayRoute.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    distinct_providers = int(
        (
            await db.execute(
                select(func.count(func.distinct(GatewayRoute.provider))).where(
                    GatewayRoute.workspace_id == workspace.id, GatewayRoute.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    routing_policies = int(
        (
            await db.execute(
                select(func.count(RoutingPolicy.id)).where(
                    RoutingPolicy.workspace_id == workspace.id, RoutingPolicy.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )

    gw_requests_30d = int(
        (
            await db.execute(
                select(func.count(GatewayRequest.id)).where(
                    GatewayRequest.workspace_id == workspace.id, GatewayRequest.created_at >= cutoff
                )
            )
        ).scalar()
        or 0
    )
    cache_hits_30d = int(
        (
            await db.execute(
                select(func.count(GatewayRequest.id)).where(
                    GatewayRequest.workspace_id == workspace.id,
                    GatewayRequest.created_at >= cutoff,
                    GatewayRequest.cache_hit.is_(True),
                )
            )
        ).scalar()
        or 0
    )

    guardrail_rules = int(
        (
            await db.execute(
                select(func.count(GuardrailRule.id)).where(
                    GuardrailRule.workspace_id == workspace.id, GuardrailRule.status == "active"
                )
            )
        ).scalar()
        or 0
    )
    guardrail_events_30d = int(
        (
            await db.execute(
                select(func.count(GuardrailEvent.id)).where(
                    GuardrailEvent.workspace_id == workspace.id, GuardrailEvent.created_at >= cutoff
                )
            )
        ).scalar()
        or 0
    )
    guardrail_blocks_30d = int(
        (
            await db.execute(
                select(func.count(GuardrailEvent.id)).where(
                    GuardrailEvent.workspace_id == workspace.id,
                    GuardrailEvent.created_at >= cutoff,
                    GuardrailEvent.decision == "block",
                )
            )
        ).scalar()
        or 0
    )

    cache_configs = int(
        (
            await db.execute(
                select(func.count(ResponseCacheConfig.id)).where(
                    ResponseCacheConfig.workspace_id == workspace.id,
                    ResponseCacheConfig.is_enabled.is_(True),
                )
            )
        ).scalar()
        or 0
    )
    cache_entries = int(
        (
            await db.execute(
                select(func.count(PromptCache.id)).where(PromptCache.workspace_id == workspace.id)
            )
        ).scalar()
        or 0
    )
    cache_total_hits = int(
        (
            await db.execute(
                select(func.coalesce(func.sum(PromptCache.hit_count), 0)).where(
                    PromptCache.workspace_id == workspace.id
                )
            )
        ).scalar()
        or 0
    )
    cache_savings_usd = float(
        (
            await db.execute(
                select(func.coalesce(func.sum(ResponseCacheConfig.total_savings_usd), 0)).where(
                    ResponseCacheConfig.workspace_id == workspace.id
                )
            )
        ).scalar()
        or 0
    )

    routes_with_rate_limits = int(
        (
            await db.execute(
                select(func.count(GatewayRoute.id)).where(
                    GatewayRoute.workspace_id == workspace.id,
                    GatewayRoute.is_active.is_(True),
                    GatewayRoute.per_user_rpm_limit.is_not(None),
                )
            )
        ).scalar()
        or 0
    )
    routes_with_cost_limits = int(
        (
            await db.execute(
                select(func.count(GatewayRoute.id)).where(
                    GatewayRoute.workspace_id == workspace.id,
                    GatewayRoute.is_active.is_(True),
                    or_(
                        GatewayRoute.daily_cost_limit_usd.is_not(None),
                        GatewayRoute.monthly_cost_limit_usd.is_not(None),
                    ),
                )
            )
        ).scalar()
        or 0
    )
    passthrough_endpoints = int(
        (
            await db.execute(
                select(func.count(GatewayPassThroughEndpoint.id)).where(
                    GatewayPassThroughEndpoint.workspace_id == workspace.id,
                    GatewayPassThroughEndpoint.is_active.is_(True),
                )
            )
        ).scalar()
        or 0
    )

    return {
        "workspace_id": str(workspace.id),
        "period_days": 30,
        "provider_context": {
            "distinct_providers": distinct_providers,
            "active_routes": active_routes,
            "total_routes": route_count,
            "routing_policies": routing_policies,
        },
        "route_context": {
            "gateway_requests_30d": gw_requests_30d,
            "cache_hits_30d": cache_hits_30d,
            "passthrough_endpoints": passthrough_endpoints,
        },
        "guardrail_context": {
            "active_rules": guardrail_rules,
            "events_30d": guardrail_events_30d,
            "blocks_30d": guardrail_blocks_30d,
        },
        "cache_context": {
            "enabled_configs": cache_configs,
            "cache_entries": cache_entries,
            "total_hits": cache_total_hits,
            "savings_usd": cache_savings_usd,
        },
        "rate_limit_context": {
            "routes_with_rpm_limits": routes_with_rate_limits,
            "routes_with_cost_limits": routes_with_cost_limits,
        },
    }


@router.get("/economics-finops-posture", response_model=EconomicsFinopsPosture)
async def economics_finops_posture(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    cutoff = _default_from()

    budget_count = int(
        (
            await db.execute(
                select(func.count(Budget.id)).where(Budget.workspace_id == workspace.id)
            )
        ).scalar()
        or 0
    )
    active_budgets = int(
        (
            await db.execute(
                select(func.count(Budget.id)).where(
                    Budget.workspace_id == workspace.id, Budget.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    total_limit = float(
        (
            await db.execute(
                select(func.coalesce(func.sum(Budget.limit_usd), 0)).where(
                    Budget.workspace_id == workspace.id, Budget.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    breach_count = int(
        (
            await db.execute(
                select(func.count(Budget.id)).where(
                    Budget.workspace_id == workspace.id,
                    Budget.is_active.is_(True),
                    Budget.id == BudgetBreach.budget_id,
                )
            )
        ).scalar()
        or 0
    )

    override_count = int(
        (
            await db.execute(
                select(func.count(BudgetOverride.id)).where(
                    BudgetOverride.budget_id.in_(
                        select(Budget.id).where(Budget.workspace_id == workspace.id)
                    )
                )
            )
        ).scalar()
        or 0
    )
    active_overrides = int(
        (
            await db.execute(
                select(func.count(BudgetOverride.id)).where(
                    BudgetOverride.budget_id.in_(
                        select(Budget.id).where(Budget.workspace_id == workspace.id)
                    ),
                    BudgetOverride.status == "active",
                )
            )
        ).scalar()
        or 0
    )

    billing_periods = int(
        (
            await db.execute(
                select(func.count(BillingPeriod.id)).where(
                    BillingPeriod.workspace_id == workspace.id
                )
            )
        ).scalar()
        or 0
    )
    open_billing = int(
        (
            await db.execute(
                select(func.count(BillingPeriod.id)).where(
                    BillingPeriod.workspace_id == workspace.id, BillingPeriod.status == "open"
                )
            )
        ).scalar()
        or 0
    )
    chargeback_rules = int(
        (
            await db.execute(
                select(func.count(ChargebackRule.id)).where(
                    ChargebackRule.workspace_id == workspace.id
                )
            )
        ).scalar()
        or 0
    )

    notifications = int(
        (
            await db.execute(
                select(func.count(BudgetNotification.id)).where(
                    BudgetNotification.workspace_id == workspace.id
                )
            )
        ).scalar()
        or 0
    )
    active_notifications = int(
        (
            await db.execute(
                select(func.count(BudgetNotification.id)).where(
                    BudgetNotification.workspace_id == workspace.id,
                    BudgetNotification.is_active.is_(True),
                )
            )
        ).scalar()
        or 0
    )

    ledger_snapshots = int(
        (
            await db.execute(
                select(func.count(LedgerSnapshot.id)).where(
                    LedgerSnapshot.workspace_id == workspace.id
                )
            )
        ).scalar()
        or 0
    )
    ledger_snapshots_30d = int(
        (
            await db.execute(
                select(func.count(LedgerSnapshot.id)).where(
                    LedgerSnapshot.workspace_id == workspace.id, LedgerSnapshot.created_at >= cutoff
                )
            )
        ).scalar()
        or 0
    )

    total_spend_30d = float(
        (
            await db.execute(
                select(func.coalesce(func.sum(ProviderCall.cost_usd), 0)).where(
                    ProviderCall.workspace_id == workspace.id, ProviderCall.created_at >= cutoff
                )
            )
        ).scalar()
        or 0
    )
    total_runs_30d = int(
        (
            await db.execute(
                select(func.count(AgentRun.id)).where(
                    AgentRun.workspace_id == workspace.id, AgentRun.started_at >= cutoff
                )
            )
        ).scalar()
        or 0
    )

    return {
        "workspace_id": str(workspace.id),
        "period_days": 30,
        "budget_context": {
            "budgets": budget_count,
            "active_budgets": active_budgets,
            "total_limit_usd": total_limit,
            "breach_count": breach_count,
            "overrides": override_count,
            "active_overrides": active_overrides,
        },
        "billing_context": {
            "billing_periods": billing_periods,
            "open_billing_periods": open_billing,
            "chargeback_rules": chargeback_rules,
        },
        "notification_context": {
            "notifications": notifications,
            "active_notifications": active_notifications,
        },
        "ledger_context": {
            "ledger_snapshots": ledger_snapshots,
            "ledger_snapshots_30d": ledger_snapshots_30d,
        },
        "spend_context": {
            "total_spend_30d": total_spend_30d,
            "total_runs_30d": total_runs_30d,
        },
    }


@router.get("/outcomes-finops-posture", response_model=OutcomesFinopsPosture)
async def outcomes_finops_posture(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    cutoff = _default_from()

    budget_count = int(
        (
            await db.execute(
                select(func.count(Budget.id)).where(Budget.workspace_id == workspace.id)
            )
        ).scalar()
        or 0
    )
    active_budgets = int(
        (
            await db.execute(
                select(func.count(Budget.id)).where(
                    Budget.workspace_id == workspace.id, Budget.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    total_limit = float(
        (
            await db.execute(
                select(func.coalesce(func.sum(Budget.limit_usd), 0)).where(
                    Budget.workspace_id == workspace.id, Budget.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    breach_count = int(
        (
            await db.execute(
                select(func.count(Budget.id)).where(
                    Budget.workspace_id == workspace.id,
                    Budget.is_active.is_(True),
                    Budget.id == BudgetBreach.budget_id,
                )
            )
        ).scalar()
        or 0
    )

    billing_periods = int(
        (
            await db.execute(
                select(func.count(BillingPeriod.id)).where(
                    BillingPeriod.workspace_id == workspace.id
                )
            )
        ).scalar()
        or 0
    )
    open_billing = int(
        (
            await db.execute(
                select(func.count(BillingPeriod.id)).where(
                    BillingPeriod.workspace_id == workspace.id, BillingPeriod.status == "open"
                )
            )
        ).scalar()
        or 0
    )
    chargeback_rules = int(
        (
            await db.execute(
                select(func.count(ChargebackRule.id)).where(
                    ChargebackRule.workspace_id == workspace.id
                )
            )
        ).scalar()
        or 0
    )

    total_spend_30d = float(
        (
            await db.execute(
                select(func.coalesce(func.sum(ProviderCall.cost_usd), 0)).where(
                    ProviderCall.workspace_id == workspace.id, ProviderCall.created_at >= cutoff
                )
            )
        ).scalar()
        or 0
    )

    from runledger_api.models.outcomes import Outcome

    outcome_count_30d = int(
        (
            await db.execute(
                select(func.count(Outcome.id)).where(
                    Outcome.workspace_id == workspace.id, Outcome.created_at >= cutoff
                )
            )
        ).scalar()
        or 0
    )

    return {
        "workspace_id": str(workspace.id),
        "period_days": 30,
        "budget_context": {
            "budgets": budget_count,
            "active_budgets": active_budgets,
            "total_limit_usd": total_limit,
            "breach_count": breach_count,
        },
        "billing_context": {
            "billing_periods": billing_periods,
            "open_billing_periods": open_billing,
            "chargeback_rules": chargeback_rules,
        },
        "spend_context": {
            "total_spend_30d": total_spend_30d,
            "outcomes_30d": outcome_count_30d,
        },
    }


@router.get("/monitoring-finops-posture", response_model=MonitoringFinopsPosture)
async def monitoring_finops_posture(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    budget_count = int(
        (
            await db.execute(
                select(func.count(Budget.id)).where(Budget.workspace_id == workspace.id)
            )
        ).scalar()
        or 0
    )
    active_budgets = int(
        (
            await db.execute(
                select(func.count(Budget.id)).where(
                    Budget.workspace_id == workspace.id, Budget.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    breach_count = int(
        (
            await db.execute(
                select(func.count(Budget.id)).where(
                    Budget.workspace_id == workspace.id,
                    Budget.is_active.is_(True),
                    Budget.id == BudgetBreach.budget_id,
                )
            )
        ).scalar()
        or 0
    )

    override_count = int(
        (
            await db.execute(
                select(func.count(BudgetOverride.id)).where(
                    BudgetOverride.budget_id.in_(
                        select(Budget.id).where(Budget.workspace_id == workspace.id)
                    )
                )
            )
        ).scalar()
        or 0
    )
    active_overrides = int(
        (
            await db.execute(
                select(func.count(BudgetOverride.id)).where(
                    BudgetOverride.budget_id.in_(
                        select(Budget.id).where(Budget.workspace_id == workspace.id)
                    ),
                    BudgetOverride.status == "active",
                )
            )
        ).scalar()
        or 0
    )

    billing_periods = int(
        (
            await db.execute(
                select(func.count(BillingPeriod.id)).where(
                    BillingPeriod.workspace_id == workspace.id
                )
            )
        ).scalar()
        or 0
    )
    open_billing = int(
        (
            await db.execute(
                select(func.count(BillingPeriod.id)).where(
                    BillingPeriod.workspace_id == workspace.id, BillingPeriod.status == "open"
                )
            )
        ).scalar()
        or 0
    )
    chargeback_rules = int(
        (
            await db.execute(
                select(func.count(ChargebackRule.id)).where(
                    ChargebackRule.workspace_id == workspace.id
                )
            )
        ).scalar()
        or 0
    )

    notifications = int(
        (
            await db.execute(
                select(func.count(BudgetNotification.id)).where(
                    BudgetNotification.workspace_id == workspace.id
                )
            )
        ).scalar()
        or 0
    )
    active_notifications = int(
        (
            await db.execute(
                select(func.count(BudgetNotification.id)).where(
                    BudgetNotification.workspace_id == workspace.id,
                    BudgetNotification.is_active.is_(True),
                )
            )
        ).scalar()
        or 0
    )

    ledger_snapshots = int(
        (
            await db.execute(
                select(func.count(LedgerSnapshot.id)).where(
                    LedgerSnapshot.workspace_id == workspace.id
                )
            )
        ).scalar()
        or 0
    )

    return {
        "workspace_id": str(workspace.id),
        "period_days": 30,
        "budget_context": {
            "budgets": budget_count,
            "active_budgets": active_budgets,
            "breach_count": breach_count,
            "overrides": override_count,
            "active_overrides": active_overrides,
        },
        "billing_context": {
            "billing_periods": billing_periods,
            "open_billing_periods": open_billing,
            "chargeback_rules": chargeback_rules,
        },
        "notification_context": {
            "notifications": notifications,
            "active_notifications": active_notifications,
        },
        "ledger_context": {
            "ledger_snapshots": ledger_snapshots,
        },
    }


@router.get("/overview-gateway-posture", response_model=OverviewGatewayPosture)
async def overview_gateway_posture(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OverviewGatewayPosture:
    now = datetime.now(UTC)
    t30 = now - timedelta(days=30)
    ws = workspace.id

    total_routes = int(
        (
            await db.execute(
                select(func.count(GatewayRoute.id)).where(GatewayRoute.workspace_id == ws)
            )
        ).scalar()
        or 0
    )
    active_routes = int(
        (
            await db.execute(
                select(func.count(GatewayRoute.id)).where(
                    GatewayRoute.workspace_id == ws, GatewayRoute.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    distinct_providers = int(
        (
            await db.execute(
                select(func.count(func.distinct(GatewayRoute.provider))).where(
                    GatewayRoute.workspace_id == ws, GatewayRoute.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    routing_policies = int(
        (
            await db.execute(
                select(func.count(RoutingPolicy.id)).where(
                    RoutingPolicy.workspace_id == ws, RoutingPolicy.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    passthrough_endpoints = int(
        (
            await db.execute(
                select(func.count(GatewayPassThroughEndpoint.id)).where(
                    GatewayPassThroughEndpoint.workspace_id == ws,
                    GatewayPassThroughEndpoint.is_active.is_(True),
                )
            )
        ).scalar()
        or 0
    )

    guardrail_rules = int(
        (
            await db.execute(
                select(func.count(GuardrailRule.id)).where(
                    GuardrailRule.workspace_id == ws, GuardrailRule.status == "active"
                )
            )
        ).scalar()
        or 0
    )
    guardrail_events_30d = int(
        (
            await db.execute(
                select(func.count(GuardrailEvent.id)).where(
                    GuardrailEvent.workspace_id == ws, GuardrailEvent.created_at >= t30
                )
            )
        ).scalar()
        or 0
    )
    guardrail_blocks_30d = int(
        (
            await db.execute(
                select(func.count(GuardrailEvent.id)).where(
                    GuardrailEvent.workspace_id == ws,
                    GuardrailEvent.created_at >= t30,
                    GuardrailEvent.decision == "block",
                )
            )
        ).scalar()
        or 0
    )

    return OverviewGatewayPosture(
        workspace_id=str(ws),
        period_days=30,
        provider_context={
            "distinct_providers": distinct_providers,
            "active_routes": active_routes,
            "total_routes": total_routes,
            "routing_policies": routing_policies,
        },
        route_context={
            "passthrough_endpoints": passthrough_endpoints,
        },
        guardrail_context={
            "active_rules": guardrail_rules,
            "events_30d": guardrail_events_30d,
            "blocks_30d": guardrail_blocks_30d,
        },
    )


@router.get("/overview-governance-posture", response_model=OverviewGovernancePosture)
async def overview_governance_posture(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OverviewGovernancePosture:
    now = datetime.now(UTC)
    t30 = now - timedelta(days=30)
    ws = workspace.id

    security_events = int(
        (
            await db.execute(
                select(func.count(SecurityEvent.id)).where(SecurityEvent.workspace_id == ws)
            )
        ).scalar()
        or 0
    )
    security_events_30d = int(
        (
            await db.execute(
                select(func.count(SecurityEvent.id)).where(
                    SecurityEvent.workspace_id == ws, SecurityEvent.created_at >= t30
                )
            )
        ).scalar()
        or 0
    )

    alert_rules = int(
        (
            await db.execute(select(func.count(AlertRule.id)).where(AlertRule.workspace_id == ws))
        ).scalar()
        or 0
    )
    active_alert_rules = int(
        (
            await db.execute(
                select(func.count(AlertRule.id)).where(
                    AlertRule.workspace_id == ws, AlertRule.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    active_firings = int(
        (
            await db.execute(
                select(func.count(AlertFiring.id)).where(
                    AlertFiring.workspace_id == ws, AlertFiring.resolved_at.is_(None)
                )
            )
        ).scalar()
        or 0
    )

    audit_events_30d = int(
        (
            await db.execute(
                select(func.count(AuditEvent.id)).where(
                    AuditEvent.workspace_id == ws, AuditEvent.created_at >= t30
                )
            )
        ).scalar()
        or 0
    )

    tags = int(
        (await db.execute(select(func.count(Tag.id)).where(Tag.workspace_id == ws))).scalar() or 0
    )
    active_tags = int(
        (
            await db.execute(
                select(func.count(Tag.id)).where(Tag.workspace_id == ws, Tag.is_active.is_(True))
            )
        ).scalar()
        or 0
    )
    approvals = int(
        (
            await db.execute(select(func.count(Approval.id)).where(Approval.workspace_id == ws))
        ).scalar()
        or 0
    )
    capture_policies = int(
        (
            await db.execute(
                select(func.count(CapturePolicy.id)).where(CapturePolicy.workspace_id == ws)
            )
        ).scalar()
        or 0
    )

    return OverviewGovernancePosture(
        workspace_id=str(ws),
        period_days=30,
        security_context={
            "security_events": security_events,
            "security_events_30d": security_events_30d,
        },
        alert_context={
            "alert_rules": alert_rules,
            "active_alert_rules": active_alert_rules,
            "active_firings": active_firings,
        },
        audit_context={
            "audit_events_30d": audit_events_30d,
        },
        governance_context={
            "tags": tags,
            "active_tags": active_tags,
            "approvals": approvals,
            "capture_policies": capture_policies,
        },
    )


@router.get("/overview-org-posture", response_model=OverviewOrgPosture)
async def overview_org_posture(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OverviewOrgPosture:
    now = datetime.now(UTC)
    t30 = now - timedelta(days=30)
    ws = workspace.id

    workspace_users = int(
        (
            await db.execute(
                select(func.count(WorkspaceUser.id)).where(WorkspaceUser.workspace_id == ws)
            )
        ).scalar()
        or 0
    )
    api_keys = int(
        (await db.execute(select(func.count(ApiKey.id)).where(ApiKey.workspace_id == ws))).scalar()
        or 0
    )
    active_api_keys = int(
        (
            await db.execute(
                select(func.count(ApiKey.id)).where(
                    ApiKey.workspace_id == ws, ApiKey.revoked_at.is_(None)
                )
            )
        ).scalar()
        or 0
    )

    telemetry_batches = int(
        (
            await db.execute(
                select(func.count(OtlpIngestBatch.id)).where(OtlpIngestBatch.workspace_id == ws)
            )
        ).scalar()
        or 0
    )
    telemetry_batches_30d = int(
        (
            await db.execute(
                select(func.count(OtlpIngestBatch.id)).where(
                    OtlpIngestBatch.workspace_id == ws, OtlpIngestBatch.received_at >= t30
                )
            )
        ).scalar()
        or 0
    )

    mcp_servers = int(
        (
            await db.execute(select(func.count(McpServer.id)).where(McpServer.workspace_id == ws))
        ).scalar()
        or 0
    )
    active_mcp_servers = int(
        (
            await db.execute(
                select(func.count(McpServer.id)).where(
                    McpServer.workspace_id == ws, McpServer.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )

    hub_models = int(
        (
            await db.execute(select(func.count(HubModel.id)).where(HubModel.workspace_id == ws))
        ).scalar()
        or 0
    )
    active_hub_models = int(
        (
            await db.execute(
                select(func.count(HubModel.id)).where(
                    HubModel.workspace_id == ws, HubModel.is_deprecated.is_(False)
                )
            )
        ).scalar()
        or 0
    )

    return OverviewOrgPosture(
        workspace_id=str(ws),
        period_days=30,
        user_context={
            "workspace_users": workspace_users,
        },
        api_key_context={
            "api_keys": api_keys,
            "active_api_keys": active_api_keys,
        },
        telemetry_context={
            "telemetry_batches": telemetry_batches,
            "telemetry_batches_30d": telemetry_batches_30d,
        },
        mcp_context={
            "mcp_servers": mcp_servers,
            "active_mcp_servers": active_mcp_servers,
        },
        hub_context={
            "hub_models": hub_models,
            "active_hub_models": active_hub_models,
        },
    )


# ---------------------------------------------------------------------------
# WU-009  Model-usage gateway & intel posture
# ---------------------------------------------------------------------------


@router.get("/model-usage-gateway-posture", response_model=ModelUsageGatewayPosture)
async def model_usage_gateway_posture(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ModelUsageGatewayPosture:
    ws = workspace.id
    cutoff = datetime.now(UTC) - timedelta(days=30)

    active_routes = int(
        (
            await db.execute(
                select(func.count(GatewayRoute.id)).where(
                    GatewayRoute.workspace_id == ws, GatewayRoute.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )

    total_routes = int(
        (
            await db.execute(
                select(func.count(GatewayRoute.id)).where(GatewayRoute.workspace_id == ws)
            )
        ).scalar()
        or 0
    )

    distinct_models = int(
        (
            await db.execute(
                select(func.count(sa.distinct(GatewayRoute.target_model))).where(
                    GatewayRoute.workspace_id == ws, GatewayRoute.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )

    routing_policies = int(
        (
            await db.execute(
                select(func.count(RoutingPolicy.id)).where(RoutingPolicy.workspace_id == ws)
            )
        ).scalar()
        or 0
    )

    from runledger_api.models.gateway import GatewayRequest

    runs_30d = int(
        (
            await db.execute(
                select(func.count(AgentRun.id)).where(
                    AgentRun.workspace_id == ws, AgentRun.started_at >= cutoff
                )
            )
        ).scalar()
        or 0
    )

    gateway_requests_30d = int(
        (
            await db.execute(
                select(func.count(GatewayRequest.id)).where(
                    GatewayRequest.workspace_id == ws, GatewayRequest.created_at >= cutoff
                )
            )
        ).scalar()
        or 0
    )

    provider_calls_30d = int(
        (
            await db.execute(
                select(func.count(ProviderCall.id)).where(
                    ProviderCall.workspace_id == ws, ProviderCall.created_at >= cutoff
                )
            )
        ).scalar()
        or 0
    )

    tags = int(
        (await db.execute(select(func.count(Tag.id)).where(Tag.workspace_id == ws))).scalar() or 0
    )

    active_tags = int(
        (
            await db.execute(
                select(func.count(Tag.id)).where(Tag.workspace_id == ws, Tag.is_active.is_(True))
            )
        ).scalar()
        or 0
    )

    return ModelUsageGatewayPosture(
        workspace_id=str(ws),
        period_days=30,
        gateway_context={
            "active_routes": active_routes,
            "total_routes": total_routes,
            "distinct_models": distinct_models,
            "routing_policies": routing_policies,
        },
        investigation_context={
            "runs_30d": runs_30d,
            "gateway_requests_30d": gateway_requests_30d,
            "provider_calls_30d": provider_calls_30d,
        },
        tag_context={
            "tags": tags,
            "active_tags": active_tags,
        },
    )


# ---------------------------------------------------------------------------
# WU-009  Economics / Cost-savings gateway posture
# ---------------------------------------------------------------------------


@router.get("/economics-gateway-posture", response_model=EconomicsGatewayPosture)
async def economics_gateway_posture(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EconomicsGatewayPosture:
    ws = workspace.id
    cutoff = datetime.now(UTC) - timedelta(days=30)

    distinct_providers = int(
        (
            await db.execute(
                select(func.count(sa.distinct(GatewayRoute.provider))).where(
                    GatewayRoute.workspace_id == ws, GatewayRoute.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )

    active_routes = int(
        (
            await db.execute(
                select(func.count(GatewayRoute.id)).where(
                    GatewayRoute.workspace_id == ws, GatewayRoute.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )

    routing_policies = int(
        (
            await db.execute(
                select(func.count(RoutingPolicy.id)).where(RoutingPolicy.workspace_id == ws)
            )
        ).scalar()
        or 0
    )

    from runledger_api.models.gateway import GatewayRequest

    gateway_requests_30d = int(
        (
            await db.execute(
                select(func.count(GatewayRequest.id)).where(
                    GatewayRequest.workspace_id == ws, GatewayRequest.created_at >= cutoff
                )
            )
        ).scalar()
        or 0
    )

    distinct_models = int(
        (
            await db.execute(
                select(func.count(sa.distinct(GatewayRoute.target_model))).where(
                    GatewayRoute.workspace_id == ws, GatewayRoute.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )

    runs_30d = int(
        (
            await db.execute(
                select(func.count(AgentRun.id)).where(
                    AgentRun.workspace_id == ws, AgentRun.started_at >= cutoff
                )
            )
        ).scalar()
        or 0
    )

    provider_calls_30d = int(
        (
            await db.execute(
                select(func.count(ProviderCall.id)).where(
                    ProviderCall.workspace_id == ws, ProviderCall.created_at >= cutoff
                )
            )
        ).scalar()
        or 0
    )

    from runledger_api.models.alerts import AlertFiring

    monitoring_alerts_30d = int(
        (
            await db.execute(
                select(func.count(AlertFiring.id)).where(
                    AlertFiring.workspace_id == ws, AlertFiring.fired_at >= cutoff
                )
            )
        ).scalar()
        or 0
    )

    return EconomicsGatewayPosture(
        workspace_id=str(ws),
        period_days=30,
        provider_context={
            "distinct_providers": distinct_providers,
            "gateway_requests_30d": gateway_requests_30d,
        },
        gateway_context={
            "active_routes": active_routes,
            "distinct_models": distinct_models,
            "routing_policies": routing_policies,
        },
        investigation_context={
            "runs_30d": runs_30d,
            "provider_calls_30d": provider_calls_30d,
            "monitoring_alerts_30d": monitoring_alerts_30d,
        },
    )


# ---------------------------------------------------------------------------
# WU-010  Monitoring ops posture (gateway + governance + org + investigation)
# ---------------------------------------------------------------------------


@router.get("/monitoring-ops-posture", response_model=MonitoringOpsPosture)
async def monitoring_ops_posture(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MonitoringOpsPosture:
    ws = workspace.id
    cutoff = datetime.now(UTC) - timedelta(days=30)

    # Gateway context
    from runledger_api.models.gateway import GatewayRequest

    distinct_providers = int(
        (
            await db.execute(
                select(func.count(sa.distinct(GatewayRoute.provider))).where(
                    GatewayRoute.workspace_id == ws, GatewayRoute.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    active_routes = int(
        (
            await db.execute(
                select(func.count(GatewayRoute.id)).where(
                    GatewayRoute.workspace_id == ws, GatewayRoute.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    guardrail_rules = int(
        (
            await db.execute(
                select(func.count(GuardrailRule.id)).where(
                    GuardrailRule.workspace_id == ws, GuardrailRule.status == "active"
                )
            )
        ).scalar()
        or 0
    )
    guardrail_events_30d = int(
        (
            await db.execute(
                select(func.count(GuardrailEvent.id)).where(
                    GuardrailEvent.workspace_id == ws, GuardrailEvent.created_at >= cutoff
                )
            )
        ).scalar()
        or 0
    )
    from runledger_api.models.cache_config import ResponseCacheConfig

    cache_configs = int(
        (
            await db.execute(
                select(func.count(ResponseCacheConfig.id)).where(
                    ResponseCacheConfig.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )
    rate_limit_routes = int(
        (
            await db.execute(
                select(func.count(GatewayRoute.id)).where(
                    GatewayRoute.workspace_id == ws, GatewayRoute.per_user_rpm_limit.isnot(None)
                )
            )
        ).scalar()
        or 0
    )

    # Governance context
    tool_registry_count = int(
        (
            await db.execute(
                select(func.count(ToolRegistry.id)).where(ToolRegistry.workspace_id == ws)
            )
        ).scalar()
        or 0
    )
    tool_policies = int(
        (
            await db.execute(select(func.count(ToolPolicy.id)).where(ToolPolicy.workspace_id == ws))
        ).scalar()
        or 0
    )
    capture_policies = int(
        (
            await db.execute(
                select(func.count(CapturePolicy.id)).where(CapturePolicy.workspace_id == ws)
            )
        ).scalar()
        or 0
    )
    audit_events_30d = int(
        (
            await db.execute(
                select(func.count(AuditEvent.id)).where(
                    AuditEvent.workspace_id == ws, AuditEvent.created_at >= cutoff
                )
            )
        ).scalar()
        or 0
    )
    approvals = int(
        (
            await db.execute(select(func.count(Approval.id)).where(Approval.workspace_id == ws))
        ).scalar()
        or 0
    )
    tags = int(
        (await db.execute(select(func.count(Tag.id)).where(Tag.workspace_id == ws))).scalar() or 0
    )

    # Org context
    workspace_users = int(
        (
            await db.execute(
                select(func.count(WorkspaceUser.id)).where(WorkspaceUser.workspace_id == ws)
            )
        ).scalar()
        or 0
    )
    mcp_servers = int(
        (
            await db.execute(select(func.count(McpServer.id)).where(McpServer.workspace_id == ws))
        ).scalar()
        or 0
    )
    active_mcp_servers = int(
        (
            await db.execute(
                select(func.count(McpServer.id)).where(
                    McpServer.workspace_id == ws, McpServer.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )

    # Investigation context
    runs_30d = int(
        (
            await db.execute(
                select(func.count(AgentRun.id)).where(
                    AgentRun.workspace_id == ws, AgentRun.started_at >= cutoff
                )
            )
        ).scalar()
        or 0
    )
    gateway_requests_30d = int(
        (
            await db.execute(
                select(func.count(GatewayRequest.id)).where(
                    GatewayRequest.workspace_id == ws, GatewayRequest.created_at >= cutoff
                )
            )
        ).scalar()
        or 0
    )

    return MonitoringOpsPosture(
        workspace_id=str(ws),
        period_days=30,
        gateway_context={
            "distinct_providers": distinct_providers,
            "active_routes": active_routes,
            "guardrail_rules": guardrail_rules,
            "guardrail_events_30d": guardrail_events_30d,
            "cache_configs": cache_configs,
            "rate_limit_routes": rate_limit_routes,
        },
        governance_context={
            "tool_registry": tool_registry_count,
            "tool_policies": tool_policies,
            "capture_policies": capture_policies,
            "audit_events_30d": audit_events_30d,
            "approvals": approvals,
            "tags": tags,
        },
        org_context={
            "workspace_users": workspace_users,
            "mcp_servers": mcp_servers,
            "active_mcp_servers": active_mcp_servers,
        },
        investigation_context={
            "runs_30d": runs_30d,
            "gateway_requests_30d": gateway_requests_30d,
        },
    )


# ---------------------------------------------------------------------------
# WU-010  Telemetry ops posture (gateway + governance + org + investigation)
# ---------------------------------------------------------------------------


@router.get("/telemetry-ops-posture", response_model=TelemetryOpsPosture)
async def telemetry_ops_posture(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TelemetryOpsPosture:
    ws = workspace.id
    cutoff = datetime.now(UTC) - timedelta(days=30)

    # Gateway context
    active_routes = int(
        (
            await db.execute(
                select(func.count(GatewayRoute.id)).where(
                    GatewayRoute.workspace_id == ws, GatewayRoute.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    distinct_models = int(
        (
            await db.execute(
                select(func.count(sa.distinct(GatewayRoute.target_model))).where(
                    GatewayRoute.workspace_id == ws, GatewayRoute.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    from runledger_api.models.gateway import GatewayRequest

    gateway_requests_30d = int(
        (
            await db.execute(
                select(func.count(GatewayRequest.id)).where(
                    GatewayRequest.workspace_id == ws, GatewayRequest.created_at >= cutoff
                )
            )
        ).scalar()
        or 0
    )

    # Governance context
    capture_policies = int(
        (
            await db.execute(
                select(func.count(CapturePolicy.id)).where(CapturePolicy.workspace_id == ws)
            )
        ).scalar()
        or 0
    )
    security_events_30d = int(
        (
            await db.execute(
                select(func.count(SecurityEvent.id)).where(
                    SecurityEvent.workspace_id == ws, SecurityEvent.created_at >= cutoff
                )
            )
        ).scalar()
        or 0
    )
    alert_rules = int(
        (
            await db.execute(select(func.count(AlertRule.id)).where(AlertRule.workspace_id == ws))
        ).scalar()
        or 0
    )
    active_alert_rules = int(
        (
            await db.execute(
                select(func.count(AlertRule.id)).where(
                    AlertRule.workspace_id == ws, AlertRule.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    audit_events_30d = int(
        (
            await db.execute(
                select(func.count(AuditEvent.id)).where(
                    AuditEvent.workspace_id == ws, AuditEvent.created_at >= cutoff
                )
            )
        ).scalar()
        or 0
    )
    approvals = int(
        (
            await db.execute(select(func.count(Approval.id)).where(Approval.workspace_id == ws))
        ).scalar()
        or 0
    )
    tags = int(
        (await db.execute(select(func.count(Tag.id)).where(Tag.workspace_id == ws))).scalar() or 0
    )

    # Org context
    workspace_users = int(
        (
            await db.execute(
                select(func.count(WorkspaceUser.id)).where(WorkspaceUser.workspace_id == ws)
            )
        ).scalar()
        or 0
    )
    telemetry_batches_30d = int(
        (
            await db.execute(
                select(func.count(OtlpIngestBatch.id)).where(
                    OtlpIngestBatch.workspace_id == ws, OtlpIngestBatch.received_at >= cutoff
                )
            )
        ).scalar()
        or 0
    )

    # Investigation context
    runs_30d = int(
        (
            await db.execute(
                select(func.count(AgentRun.id)).where(
                    AgentRun.workspace_id == ws, AgentRun.started_at >= cutoff
                )
            )
        ).scalar()
        or 0
    )
    provider_calls_30d = int(
        (
            await db.execute(
                select(func.count(ProviderCall.id)).where(
                    ProviderCall.workspace_id == ws, ProviderCall.created_at >= cutoff
                )
            )
        ).scalar()
        or 0
    )

    return TelemetryOpsPosture(
        workspace_id=str(ws),
        period_days=30,
        gateway_context={
            "active_routes": active_routes,
            "distinct_models": distinct_models,
            "gateway_requests_30d": gateway_requests_30d,
        },
        governance_context={
            "capture_policies": capture_policies,
            "security_events_30d": security_events_30d,
            "alert_rules": alert_rules,
            "active_alert_rules": active_alert_rules,
            "audit_events_30d": audit_events_30d,
            "approvals": approvals,
            "tags": tags,
        },
        org_context={
            "workspace_users": workspace_users,
            "telemetry_batches_30d": telemetry_batches_30d,
        },
        investigation_context={
            "runs_30d": runs_30d,
            "provider_calls_30d": provider_calls_30d,
        },
    )


@router.get("/user-analytics-org-posture", response_model=UserAnalyticsOrgPosture)
async def user_analytics_org_posture(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _user: TenantUser = Depends(get_current_user),
    _rl: None = Depends(analytics_rate_limit),
):
    t_from = _default_from()
    t_to = _default_to()

    org_name = (
        await db.execute(select(Tenant.name).where(Tenant.id == workspace.tenant_id))
    ).scalar() or ""

    workspace_count = (
        await db.execute(
            select(func.count(Workspace.id)).where(Workspace.tenant_id == workspace.tenant_id)
        )
    ).scalar() or 0

    workspace_user_count = (
        await db.execute(
            select(func.count(WorkspaceUser.id)).where(WorkspaceUser.workspace_id == workspace.id)
        )
    ).scalar() or 0

    distinct_end_users_30d = (
        await db.execute(
            select(func.count(func.distinct(AgentRun.end_user_id))).where(
                AgentRun.workspace_id == workspace.id,
                AgentRun.end_user_id.isnot(None),
                AgentRun.started_at >= t_from,
                AgentRun.started_at < t_to,
            )
        )
    ).scalar() or 0

    total_end_users = (
        await db.execute(
            select(func.count(func.distinct(AgentRun.end_user_id))).where(
                AgentRun.workspace_id == workspace.id,
                AgentRun.end_user_id.isnot(None),
            )
        )
    ).scalar() or 0

    api_key_count = (
        await db.execute(select(func.count(ApiKey.id)).where(ApiKey.workspace_id == workspace.id))
    ).scalar() or 0

    active_api_keys = (
        await db.execute(
            select(func.count(ApiKey.id)).where(
                ApiKey.workspace_id == workspace.id,
                ApiKey.revoked_at.is_(None),
            )
        )
    ).scalar() or 0

    telemetry_batches_30d = (
        await db.execute(
            select(func.count(OtlpIngestBatch.id)).where(
                OtlpIngestBatch.workspace_id == workspace.id,
                OtlpIngestBatch.received_at >= t_from,
                OtlpIngestBatch.received_at < t_to,
            )
        )
    ).scalar() or 0

    return UserAnalyticsOrgPosture(
        workspace_id=str(workspace.id),
        period_days=30,
        org_context={
            "org_name": org_name,
            "workspace_count": workspace_count,
            "workspace_users": workspace_user_count,
        },
        user_context={
            "total_end_users": total_end_users,
            "active_end_users_30d": distinct_end_users_30d,
            "api_keys": api_key_count,
            "active_api_keys": active_api_keys,
        },
        workspace_context={
            "telemetry_batches_30d": telemetry_batches_30d,
        },
    )


@router.get("/overview-scope-posture", response_model=OverviewScopePosture)
async def overview_scope_posture(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OverviewScopePosture:
    ws = workspace.id

    access_groups = int(
        (
            await db.execute(
                select(func.count(AccessGroup.id)).where(AccessGroup.workspace_id == ws)
            )
        ).scalar()
        or 0
    )
    active_access_groups = int(
        (
            await db.execute(
                select(func.count(AccessGroup.id)).where(
                    AccessGroup.workspace_id == ws, AccessGroup.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    total_members = int(
        (
            await db.execute(
                select(func.count(AccessGroupMember.id)).where(
                    AccessGroupMember.group_id.in_(
                        select(AccessGroup.id).where(
                            AccessGroup.workspace_id == ws, AccessGroup.is_active.is_(True)
                        )
                    )
                )
            )
        ).scalar()
        or 0
    )

    cache_configs = int(
        (
            await db.execute(
                select(func.count(ResponseCacheConfig.id)).where(
                    ResponseCacheConfig.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )
    enabled_configs = int(
        (
            await db.execute(
                select(func.count(ResponseCacheConfig.id)).where(
                    ResponseCacheConfig.workspace_id == ws, ResponseCacheConfig.is_enabled.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    total_hits = int(
        (
            await db.execute(
                select(func.coalesce(func.sum(ResponseCacheConfig.total_hits), 0)).where(
                    ResponseCacheConfig.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )
    total_savings_usd = float(
        (
            await db.execute(
                select(func.coalesce(func.sum(ResponseCacheConfig.total_savings_usd), 0)).where(
                    ResponseCacheConfig.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )

    routes_with_limits = int(
        (
            await db.execute(
                select(func.count(GatewayRoute.id)).where(
                    GatewayRoute.workspace_id == ws,
                    GatewayRoute.is_active.is_(True),
                    GatewayRoute.per_user_rpm_limit.isnot(None),
                )
            )
        ).scalar()
        or 0
    )
    routes_without_limits = int(
        (
            await db.execute(
                select(func.count(GatewayRoute.id)).where(
                    GatewayRoute.workspace_id == ws,
                    GatewayRoute.is_active.is_(True),
                    GatewayRoute.per_user_rpm_limit.is_(None),
                )
            )
        ).scalar()
        or 0
    )

    tool_registry_entries = int(
        (
            await db.execute(
                select(func.count(ToolRegistry.id)).where(ToolRegistry.workspace_id == ws)
            )
        ).scalar()
        or 0
    )
    tool_policies = int(
        (
            await db.execute(select(func.count(ToolPolicy.id)).where(ToolPolicy.workspace_id == ws))
        ).scalar()
        or 0
    )
    active_tool_policies = int(
        (
            await db.execute(
                select(func.count(ToolPolicy.id)).where(
                    ToolPolicy.workspace_id == ws, ToolPolicy.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    pending_approvals = int(
        (
            await db.execute(
                select(func.count(Approval.id)).where(
                    Approval.workspace_id == ws, Approval.status == "pending"
                )
            )
        ).scalar()
        or 0
    )
    capture_policies = int(
        (
            await db.execute(
                select(func.count(CapturePolicy.id)).where(CapturePolicy.workspace_id == ws)
            )
        ).scalar()
        or 0
    )

    return OverviewScopePosture(
        workspace_id=str(ws),
        period_days=30,
        access_group_context={
            "access_groups": access_groups,
            "active_access_groups": active_access_groups,
            "total_members": total_members,
        },
        cache_context={
            "cache_configs": cache_configs,
            "enabled_configs": enabled_configs,
            "total_hits": total_hits,
            "total_savings_usd": total_savings_usd,
        },
        rate_limit_context={
            "routes_with_limits": routes_with_limits,
            "routes_without_limits": routes_without_limits,
        },
        tool_context={
            "tool_registry_entries": tool_registry_entries,
            "tool_policies": tool_policies,
            "active_tool_policies": active_tool_policies,
            "pending_approvals": pending_approvals,
            "capture_policies": capture_policies,
        },
    )


@router.get("/tool-registry-finops-posture", response_model=ToolRegistryFinopsPosture)
async def tool_registry_finops_posture(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ToolRegistryFinopsPosture:
    ws = workspace.id
    from_dt = _default_from()

    total_budgets = int(
        (
            await db.execute(
                select(func.count(Budget.id)).where(
                    Budget.workspace_id == ws, Budget.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    tool_scoped_budgets = int(
        (
            await db.execute(
                select(func.count(Budget.id)).where(
                    Budget.workspace_id == ws,
                    Budget.is_active.is_(True),
                    Budget.scope_type == "feature_tag",
                )
            )
        ).scalar()
        or 0
    )
    total_budget_limit_usd = float(
        (
            await db.execute(
                select(func.coalesce(func.sum(Budget.limit_usd), 0)).where(
                    Budget.workspace_id == ws, Budget.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )

    chargeback_rules = int(
        (
            await db.execute(
                select(func.count(ChargebackRule.id)).where(
                    ChargebackRule.workspace_id == ws,
                    ChargebackRule.status == "active",
                )
            )
        ).scalar()
        or 0
    )
    tool_dimension_rules = int(
        (
            await db.execute(
                select(func.count(ChargebackRule.id)).where(
                    ChargebackRule.workspace_id == ws,
                    ChargebackRule.status == "active",
                    ChargebackRule.dimension == "feature_tag",
                )
            )
        ).scalar()
        or 0
    )

    tool_spend_30d = float(
        (
            await db.execute(
                select(func.coalesce(func.sum(ProviderCall.cost_usd), 0)).where(
                    ProviderCall.workspace_id == ws,
                    ProviderCall.created_at >= from_dt,
                    ProviderCall.tool_call_id.isnot(None),
                )
            )
        ).scalar()
        or 0
    )
    tool_call_count_30d = int(
        (
            await db.execute(
                select(func.count(ProviderCall.id)).where(
                    ProviderCall.workspace_id == ws,
                    ProviderCall.created_at >= from_dt,
                    ProviderCall.tool_call_id.isnot(None),
                )
            )
        ).scalar()
        or 0
    )
    total_spend_30d = float(
        (
            await db.execute(
                select(func.coalesce(func.sum(ProviderCall.cost_usd), 0)).where(
                    ProviderCall.workspace_id == ws,
                    ProviderCall.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    return ToolRegistryFinopsPosture(
        workspace_id=str(ws),
        period_days=30,
        budget_context={
            "total_budgets": total_budgets,
            "tool_scoped_budgets": tool_scoped_budgets,
            "total_budget_limit_usd": total_budget_limit_usd,
        },
        chargeback_context={
            "chargeback_rules": chargeback_rules,
            "tool_dimension_rules": tool_dimension_rules,
        },
        spend_context={
            "tool_spend_30d": tool_spend_30d,
            "tool_call_count_30d": tool_call_count_30d,
            "total_spend_30d": total_spend_30d,
        },
    )


@router.get(
    "/approvals-alert-finops-posture", response_model=ApprovalsAlertFinopsPosture
)
async def approvals_alert_finops_posture(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApprovalsAlertFinopsPosture:
    ws = workspace.id

    from runledger_api.models.budgets import BudgetBreach

    budget_increase_total = int(
        (
            await db.execute(
                select(func.count(Approval.id)).where(
                    Approval.workspace_id == ws,
                    Approval.request_type == "budget_increase",
                )
            )
        ).scalar()
        or 0
    )
    budget_increase_pending = int(
        (
            await db.execute(
                select(func.count(Approval.id)).where(
                    Approval.workspace_id == ws,
                    Approval.request_type == "budget_increase",
                    Approval.status == "pending",
                )
            )
        ).scalar()
        or 0
    )
    budget_increase_approved = int(
        (
            await db.execute(
                select(func.count(Approval.id)).where(
                    Approval.workspace_id == ws,
                    Approval.request_type == "budget_increase",
                    Approval.status == "approved",
                )
            )
        ).scalar()
        or 0
    )

    total_budgets = int(
        (
            await db.execute(
                select(func.count(Budget.id)).where(
                    Budget.workspace_id == ws, Budget.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    total_budget_limit_usd = float(
        (
            await db.execute(
                select(func.coalesce(func.sum(Budget.limit_usd), 0)).where(
                    Budget.workspace_id == ws, Budget.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    active_overrides = int(
        (
            await db.execute(
                select(func.count(BudgetOverride.id)).where(
                    BudgetOverride.workspace_id == ws,
                    BudgetOverride.status == "active",
                )
            )
        ).scalar()
        or 0
    )
    breach_count_30d = int(
        (
            await db.execute(
                select(func.count(BudgetBreach.id)).where(
                    BudgetBreach.budget_id.in_(
                        select(Budget.id).where(Budget.workspace_id == ws)
                    ),
                    BudgetBreach.occurred_at >= _default_from(),
                )
            )
        ).scalar()
        or 0
    )

    budget_alert_rules = int(
        (
            await db.execute(
                select(func.count(AlertRule.id)).where(
                    AlertRule.workspace_id == ws,
                    AlertRule.is_active.is_(True),
                    AlertRule.metric.in_(
                        [
                            "spend_velocity",
                            "budget_utilization",
                            "budget_breach_count",
                        ]
                    ),
                )
            )
        ).scalar()
        or 0
    )
    total_alert_rules = int(
        (
            await db.execute(
                select(func.count(AlertRule.id)).where(
                    AlertRule.workspace_id == ws, AlertRule.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    recent_firings = int(
        (
            await db.execute(
                select(func.count(AlertFiring.id)).where(
                    AlertFiring.workspace_id == ws,
                    AlertFiring.fired_at >= _default_from(),
                )
            )
        ).scalar()
        or 0
    )

    return ApprovalsAlertFinopsPosture(
        workspace_id=str(ws),
        period_days=30,
        approval_context={
            "budget_increase_total": budget_increase_total,
            "budget_increase_pending": budget_increase_pending,
            "budget_increase_approved": budget_increase_approved,
        },
        budget_context={
            "total_budgets": total_budgets,
            "total_budget_limit_usd": total_budget_limit_usd,
            "active_overrides": active_overrides,
            "breach_count_30d": breach_count_30d,
        },
        alert_context={
            "budget_alert_rules": budget_alert_rules,
            "total_alert_rules": total_alert_rules,
            "recent_firings_30d": recent_firings,
        },
    )


@router.get(
    "/tags-finops-budget-posture", response_model=TagsFinopsBudgetPosture
)
async def tags_finops_budget_posture(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TagsFinopsBudgetPosture:
    ws = workspace.id
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    total_tags = int(
        (
            await db.execute(
                select(func.count(Tag.id)).where(Tag.workspace_id == ws)
            )
        ).scalar()
        or 0
    )
    active_tags = int(
        (
            await db.execute(
                select(func.count(Tag.id)).where(
                    Tag.workspace_id == ws, Tag.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    from runledger_api.models.tags import AutoTaggingRule

    active_auto_rules = int(
        (
            await db.execute(
                select(func.count(AutoTaggingRule.id)).where(
                    AutoTaggingRule.workspace_id == ws,
                    AutoTaggingRule.is_active.is_(True),
                )
            )
        ).scalar()
        or 0
    )

    total_budgets = int(
        (
            await db.execute(
                select(func.count(Budget.id)).where(
                    Budget.workspace_id == ws, Budget.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    tag_scoped_budgets = int(
        (
            await db.execute(
                select(func.count(Budget.id)).where(
                    Budget.workspace_id == ws,
                    Budget.is_active.is_(True),
                    Budget.scope_type == "feature_tag",
                )
            )
        ).scalar()
        or 0
    )
    total_budget_limit = float(
        (
            await db.execute(
                select(func.coalesce(func.sum(Budget.limit_usd), 0)).where(
                    Budget.workspace_id == ws, Budget.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )

    total_chargeback_rules = int(
        (
            await db.execute(
                select(func.count(ChargebackRule.id)).where(
                    ChargebackRule.workspace_id == ws,
                    ChargebackRule.status == "active",
                )
            )
        ).scalar()
        or 0
    )
    tag_dimension_rules = int(
        (
            await db.execute(
                select(func.count(ChargebackRule.id)).where(
                    ChargebackRule.workspace_id == ws,
                    ChargebackRule.status == "active",
                    ChargebackRule.dimension == "feature_tag",
                )
            )
        ).scalar()
        or 0
    )

    tagged_spend_row = (
        await db.execute(
            select(
                func.coalesce(func.sum(ProviderCall.cost_usd), 0),
                func.count(ProviderCall.id),
            )
            .join(AgentRun, ProviderCall.run_id == AgentRun.id)
            .where(
                AgentRun.workspace_id == ws,
                AgentRun.feature_tag.isnot(None),
                ProviderCall.created_at >= cutoff,
            )
        )
    ).one()
    tagged_spend = float(tagged_spend_row[0])
    tagged_call_count = int(tagged_spend_row[1])

    total_spend = float(
        (
            await db.execute(
                select(func.coalesce(func.sum(ProviderCall.cost_usd), 0))
                .join(AgentRun, ProviderCall.run_id == AgentRun.id)
                .where(
                    AgentRun.workspace_id == ws,
                    ProviderCall.created_at >= cutoff,
                )
            )
        ).scalar()
        or 0
    )

    distinct_tags_with_spend = int(
        (
            await db.execute(
                select(func.count(func.distinct(AgentRun.feature_tag)))
                .join(ProviderCall, ProviderCall.run_id == AgentRun.id)
                .where(
                    AgentRun.workspace_id == ws,
                    AgentRun.feature_tag.isnot(None),
                    ProviderCall.created_at >= cutoff,
                )
            )
        ).scalar()
        or 0
    )

    return TagsFinopsBudgetPosture(
        workspace_id=str(ws),
        period_days=30,
        tag_context={
            "total_tags": total_tags,
            "active_tags": active_tags,
            "active_auto_rules": active_auto_rules,
            "distinct_tags_with_spend": distinct_tags_with_spend,
        },
        budget_context={
            "total_budgets": total_budgets,
            "tag_scoped_budgets": tag_scoped_budgets,
            "total_budget_limit_usd": total_budget_limit,
        },
        chargeback_context={
            "total_chargeback_rules": total_chargeback_rules,
            "tag_dimension_rules": tag_dimension_rules,
        },
        spend_context={
            "tagged_spend_30d": tagged_spend,
            "tagged_call_count": tagged_call_count,
            "total_spend_30d": total_spend,
        },
    )


@router.get(
    "/tool-governance-org-posture", response_model=ToolGovernanceOrgPosture
)
async def tool_governance_org_posture(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ToolGovernanceOrgPosture:
    ws = workspace.id

    tenant_row = (
        await db.execute(
            select(Tenant.name).join(
                Workspace, Workspace.tenant_id == Tenant.id
            ).where(Workspace.id == ws)
        )
    ).scalar()
    org_name = str(tenant_row) if tenant_row else ""

    workspace_count = int(
        (
            await db.execute(
                select(func.count(Workspace.id)).where(
                    Workspace.tenant_id == (
                        select(Workspace.tenant_id).where(Workspace.id == ws).scalar_subquery()
                    )
                )
            )
        ).scalar()
        or 0
    )

    total_users = int(
        (
            await db.execute(
                select(func.count(func.distinct(WorkspaceUser.user_id))).where(
                    WorkspaceUser.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )

    total_access_groups = int(
        (
            await db.execute(
                select(func.count(AccessGroup.id)).where(
                    AccessGroup.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )
    tool_policy_groups = int(
        (
            await db.execute(
                select(func.count(func.distinct(ToolPolicy.scope_id))).where(
                    ToolPolicy.workspace_id == ws,
                    ToolPolicy.is_active.is_(True),
                    ToolPolicy.scope_type == "access_group",
                )
            )
        ).scalar()
        or 0
    )

    total_api_keys = int(
        (
            await db.execute(
                select(func.count(ApiKey.id)).where(
                    ApiKey.workspace_id == ws, ApiKey.revoked_at.is_(None)
                )
            )
        ).scalar()
        or 0
    )

    total_registry = int(
        (
            await db.execute(
                select(func.count(ToolRegistry.id)).where(
                    ToolRegistry.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )
    active_registry = int(
        (
            await db.execute(
                select(func.count(ToolRegistry.id)).where(
                    ToolRegistry.workspace_id == ws,
                    ToolRegistry.runtime_enforcement.is_(True),
                )
            )
        ).scalar()
        or 0
    )

    total_policies = int(
        (
            await db.execute(
                select(func.count(ToolPolicy.id)).where(
                    ToolPolicy.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )
    active_policies = int(
        (
            await db.execute(
                select(func.count(ToolPolicy.id)).where(
                    ToolPolicy.workspace_id == ws, ToolPolicy.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    org_scope_policies = int(
        (
            await db.execute(
                select(func.count(ToolPolicy.id)).where(
                    ToolPolicy.workspace_id == ws,
                    ToolPolicy.is_active.is_(True),
                    ToolPolicy.scope_type == "organization",
                )
            )
        ).scalar()
        or 0
    )
    ws_scope_policies = int(
        (
            await db.execute(
                select(func.count(ToolPolicy.id)).where(
                    ToolPolicy.workspace_id == ws,
                    ToolPolicy.is_active.is_(True),
                    ToolPolicy.scope_type == "workspace",
                )
            )
        ).scalar()
        or 0
    )
    ag_scope_policies = int(
        (
            await db.execute(
                select(func.count(ToolPolicy.id)).where(
                    ToolPolicy.workspace_id == ws,
                    ToolPolicy.is_active.is_(True),
                    ToolPolicy.scope_type == "access_group",
                )
            )
        ).scalar()
        or 0
    )

    total_mcp_servers = int(
        (
            await db.execute(
                select(func.count(McpServer.id)).where(
                    McpServer.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )
    active_mcp_servers = int(
        (
            await db.execute(
                select(func.count(McpServer.id)).where(
                    McpServer.workspace_id == ws, McpServer.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )

    return ToolGovernanceOrgPosture(
        workspace_id=str(ws),
        period_days=30,
        org_context={
            "org_name": org_name,
            "workspace_count": workspace_count,
        },
        user_context={
            "total_users": total_users,
        },
        access_group_context={
            "total_groups": total_access_groups,
            "tool_policy_groups": tool_policy_groups,
        },
        api_key_context={
            "total_keys": total_api_keys,
        },
        registry_context={
            "total_entries": total_registry,
            "active_entries": active_registry,
        },
        policy_context={
            "total_policies": total_policies,
            "active_policies": active_policies,
            "org_scope": org_scope_policies,
            "workspace_scope": ws_scope_policies,
            "access_group_scope": ag_scope_policies,
        },
        mcp_context={
            "total_servers": total_mcp_servers,
            "active_servers": active_mcp_servers,
        },
    )


@router.get(
    "/tool-governance-gateway-posture", response_model=ToolGovernanceGatewayPosture
)
async def tool_governance_gateway_posture(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ToolGovernanceGatewayPosture:
    ws = workspace.id
    from_dt = _default_from()

    total_providers = int(
        (
            await db.execute(
                select(func.count(func.distinct(GatewayRoute.provider))).where(
                    GatewayRoute.workspace_id == ws, GatewayRoute.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    total_routes = int(
        (
            await db.execute(
                select(func.count(GatewayRoute.id)).where(
                    GatewayRoute.workspace_id == ws, GatewayRoute.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )

    total_guardrails = int(
        (
            await db.execute(
                select(func.count(GuardrailRule.id)).where(
                    GuardrailRule.workspace_id == ws, GuardrailRule.status == "active"
                )
            )
        ).scalar()
        or 0
    )
    guardrail_events_30d = int(
        (
            await db.execute(
                select(func.count(GuardrailEvent.id)).where(
                    GuardrailEvent.workspace_id == ws,
                    GuardrailEvent.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    cache_configs = int(
        (
            await db.execute(
                select(func.count(ResponseCacheConfig.id)).where(
                    ResponseCacheConfig.workspace_id == ws,
                    ResponseCacheConfig.is_enabled.is_(True),
                )
            )
        ).scalar()
        or 0
    )

    rate_limited_routes = int(
        (
            await db.execute(
                select(func.count(GatewayRoute.id)).where(
                    GatewayRoute.workspace_id == ws,
                    GatewayRoute.is_active.is_(True),
                    GatewayRoute.per_user_rpm_limit.isnot(None),
                )
            )
        ).scalar()
        or 0
    )

    tool_runs_30d = int(
        (
            await db.execute(
                select(func.count(ProviderCall.id)).where(
                    ProviderCall.workspace_id == ws,
                    ProviderCall.created_at >= from_dt,
                    ProviderCall.tool_call_id.isnot(None),
                )
            )
        ).scalar()
        or 0
    )
    total_runs_30d = int(
        (
            await db.execute(
                select(func.count(AgentRun.id)).where(
                    AgentRun.workspace_id == ws,
                    AgentRun.started_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    total_alert_rules = int(
        (
            await db.execute(
                select(func.count(AlertRule.id)).where(
                    AlertRule.workspace_id == ws, AlertRule.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    alert_firings_30d = int(
        (
            await db.execute(
                select(func.count(AlertFiring.id)).where(
                    AlertFiring.workspace_id == ws,
                    AlertFiring.fired_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    return ToolGovernanceGatewayPosture(
        workspace_id=str(ws),
        period_days=30,
        provider_context={
            "total_providers": total_providers,
            "total_routes": total_routes,
        },
        guardrail_context={
            "total_guardrails": total_guardrails,
            "guardrail_events_30d": guardrail_events_30d,
        },
        cache_context={
            "cache_configs": cache_configs,
        },
        rate_limit_context={
            "rate_limited_routes": rate_limited_routes,
        },
        run_context={
            "tool_runs_30d": tool_runs_30d,
            "total_runs_30d": total_runs_30d,
        },
        monitoring_context={
            "total_alert_rules": total_alert_rules,
            "alert_firings_30d": alert_firings_30d,
        },
    )


@router.get(
    "/exception-workflows-org-posture", response_model=ExceptionWorkflowsOrgPosture
)
async def exception_workflows_org_posture(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExceptionWorkflowsOrgPosture:
    ws = workspace.id
    from_dt = _default_from()

    tenant_row = (
        await db.execute(
            select(Tenant.name).join(
                Workspace, Workspace.tenant_id == Tenant.id
            ).where(Workspace.id == ws)
        )
    ).scalar()
    org_name = str(tenant_row) if tenant_row else ""

    workspace_count = int(
        (
            await db.execute(
                select(func.count(Workspace.id)).where(
                    Workspace.tenant_id == (
                        select(Workspace.tenant_id).where(Workspace.id == ws).scalar_subquery()
                    )
                )
            )
        ).scalar()
        or 0
    )

    total_users = int(
        (
            await db.execute(
                select(func.count(func.distinct(WorkspaceUser.user_id))).where(
                    WorkspaceUser.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )

    total_access_groups = int(
        (
            await db.execute(
                select(func.count(AccessGroup.id)).where(
                    AccessGroup.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )

    total_api_keys = int(
        (
            await db.execute(
                select(func.count(ApiKey.id)).where(
                    ApiKey.workspace_id == ws, ApiKey.revoked_at.is_(None)
                )
            )
        ).scalar()
        or 0
    )

    total_approvals = int(
        (
            await db.execute(
                select(func.count(Approval.id)).where(
                    Approval.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )
    pending_approvals = int(
        (
            await db.execute(
                select(func.count(Approval.id)).where(
                    Approval.workspace_id == ws,
                    Approval.status == "pending",
                )
            )
        ).scalar()
        or 0
    )
    approvals_30d = int(
        (
            await db.execute(
                select(func.count(Approval.id)).where(
                    Approval.workspace_id == ws,
                    Approval.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    total_alert_rules = int(
        (
            await db.execute(
                select(func.count(AlertRule.id)).where(
                    AlertRule.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )
    active_alert_rules = int(
        (
            await db.execute(
                select(func.count(AlertRule.id)).where(
                    AlertRule.workspace_id == ws, AlertRule.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    alert_firings_30d = int(
        (
            await db.execute(
                select(func.count(AlertFiring.id)).where(
                    AlertFiring.workspace_id == ws,
                    AlertFiring.fired_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    total_mcp_servers = int(
        (
            await db.execute(
                select(func.count(McpServer.id)).where(
                    McpServer.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )
    active_mcp_servers = int(
        (
            await db.execute(
                select(func.count(McpServer.id)).where(
                    McpServer.workspace_id == ws, McpServer.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )

    return ExceptionWorkflowsOrgPosture(
        workspace_id=str(ws),
        period_days=30,
        org_context={
            "org_name": org_name,
            "workspace_count": workspace_count,
        },
        user_context={
            "total_users": total_users,
        },
        access_group_context={
            "total_groups": total_access_groups,
        },
        api_key_context={
            "total_keys": total_api_keys,
        },
        approval_context={
            "total_approvals": total_approvals,
            "pending_approvals": pending_approvals,
            "approvals_30d": approvals_30d,
        },
        alert_context={
            "total_alert_rules": total_alert_rules,
            "active_alert_rules": active_alert_rules,
            "alert_firings_30d": alert_firings_30d,
        },
        mcp_context={
            "total_servers": total_mcp_servers,
            "active_servers": active_mcp_servers,
        },
    )


@router.get(
    "/exception-workflows-gateway-posture",
    response_model=ExceptionWorkflowsGatewayPosture,
)
async def exception_workflows_gateway_posture(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExceptionWorkflowsGatewayPosture:
    ws = workspace.id
    from_dt = _default_from()

    total_providers = int(
        (
            await db.execute(
                select(func.count(func.distinct(GatewayRoute.provider))).where(
                    GatewayRoute.workspace_id == ws, GatewayRoute.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    total_routes = int(
        (
            await db.execute(
                select(func.count(GatewayRoute.id)).where(
                    GatewayRoute.workspace_id == ws, GatewayRoute.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )

    total_guardrails = int(
        (
            await db.execute(
                select(func.count(GuardrailRule.id)).where(
                    GuardrailRule.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )
    guardrail_events_30d = int(
        (
            await db.execute(
                select(func.count(GuardrailEvent.id)).where(
                    GuardrailEvent.workspace_id == ws,
                    GuardrailEvent.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    cache_configs = int(
        (
            await db.execute(
                select(func.count(ResponseCacheConfig.id)).where(
                    ResponseCacheConfig.workspace_id == ws,
                    ResponseCacheConfig.is_enabled.is_(True),
                )
            )
        ).scalar()
        or 0
    )

    rate_limited_routes = int(
        (
            await db.execute(
                select(func.count(GatewayRoute.id)).where(
                    GatewayRoute.workspace_id == ws,
                    GatewayRoute.is_active.is_(True),
                    GatewayRoute.per_user_rpm_limit.isnot(None),
                )
            )
        ).scalar()
        or 0
    )

    tool_runs_30d = int(
        (
            await db.execute(
                select(func.count(ProviderCall.id)).where(
                    ProviderCall.workspace_id == ws,
                    ProviderCall.created_at >= from_dt,
                    ProviderCall.tool_call_id.isnot(None),
                )
            )
        ).scalar()
        or 0
    )
    total_runs_30d = int(
        (
            await db.execute(
                select(func.count(AgentRun.id)).where(
                    AgentRun.workspace_id == ws,
                    AgentRun.started_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    ew_alert_rules = int(
        (
            await db.execute(
                select(func.count(AlertRule.id)).where(
                    AlertRule.workspace_id == ws, AlertRule.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    ew_alert_firings_30d = int(
        (
            await db.execute(
                select(func.count(AlertFiring.id)).where(
                    AlertFiring.workspace_id == ws,
                    AlertFiring.fired_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    return ExceptionWorkflowsGatewayPosture(
        workspace_id=str(ws),
        period_days=30,
        provider_context={
            "total_providers": total_providers,
            "total_routes": total_routes,
        },
        guardrail_context={
            "total_guardrails": total_guardrails,
            "guardrail_events_30d": guardrail_events_30d,
        },
        cache_context={
            "cache_configs": cache_configs,
        },
        rate_limit_context={
            "rate_limited_routes": rate_limited_routes,
        },
        run_context={
            "tool_runs_30d": tool_runs_30d,
            "total_runs_30d": total_runs_30d,
        },
        monitoring_context={
            "total_alert_rules": ew_alert_rules,
            "alert_firings_30d": ew_alert_firings_30d,
        },
    )


@router.get(
    "/data-protection-org-posture", response_model=DataProtectionOrgPosture
)
async def data_protection_org_posture(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataProtectionOrgPosture:
    ws = workspace.id
    from_dt = _default_from()

    tenant_row = (
        await db.execute(
            select(Tenant.name).join(
                Workspace, Workspace.tenant_id == Tenant.id
            ).where(Workspace.id == ws)
        )
    ).scalar()
    org_name = str(tenant_row) if tenant_row else ""

    workspace_count = int(
        (
            await db.execute(
                select(func.count(Workspace.id)).where(
                    Workspace.tenant_id == (
                        select(Workspace.tenant_id).where(Workspace.id == ws).scalar_subquery()
                    )
                )
            )
        ).scalar()
        or 0
    )

    total_users = int(
        (
            await db.execute(
                select(func.count(func.distinct(WorkspaceUser.user_id))).where(
                    WorkspaceUser.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )

    total_access_groups = int(
        (
            await db.execute(
                select(func.count(AccessGroup.id)).where(
                    AccessGroup.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )

    total_api_keys = int(
        (
            await db.execute(
                select(func.count(ApiKey.id)).where(
                    ApiKey.workspace_id == ws, ApiKey.revoked_at.is_(None)
                )
            )
        ).scalar()
        or 0
    )

    total_capture_policies = int(
        (
            await db.execute(
                select(func.count(CapturePolicy.id)).where(
                    CapturePolicy.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )
    active_capture_policies = int(
        (
            await db.execute(
                select(func.count(CapturePolicy.id)).where(
                    CapturePolicy.workspace_id == ws,
                )
            )
        ).scalar()
        or 0
    )

    total_security_events = int(
        (
            await db.execute(
                select(func.count(SecurityEvent.id)).where(
                    SecurityEvent.workspace_id == ws,
                    SecurityEvent.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    total_tags = int(
        (
            await db.execute(
                select(func.count(Tag.id)).where(Tag.workspace_id == ws)
            )
        ).scalar()
        or 0
    )
    active_tags = int(
        (
            await db.execute(
                select(func.count(Tag.id)).where(
                    Tag.workspace_id == ws, Tag.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )

    total_mcp_servers = int(
        (
            await db.execute(
                select(func.count(McpServer.id)).where(
                    McpServer.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )
    active_mcp_servers = int(
        (
            await db.execute(
                select(func.count(McpServer.id)).where(
                    McpServer.workspace_id == ws, McpServer.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )

    return DataProtectionOrgPosture(
        workspace_id=str(ws),
        period_days=30,
        org_context={
            "org_name": org_name,
            "workspace_count": workspace_count,
        },
        user_context={
            "total_users": total_users,
        },
        access_group_context={
            "total_groups": total_access_groups,
        },
        api_key_context={
            "total_keys": total_api_keys,
        },
        capture_context={
            "total_policies": total_capture_policies,
            "active_policies": active_capture_policies,
        },
        security_context={
            "security_events_30d": total_security_events,
        },
        tag_context={
            "total_tags": total_tags,
            "active_tags": active_tags,
        },
        mcp_context={
            "total_servers": total_mcp_servers,
            "active_servers": active_mcp_servers,
        },
    )


@router.get(
    "/data-protection-gateway-posture",
    response_model=DataProtectionGatewayPosture,
)
async def data_protection_gateway_posture(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataProtectionGatewayPosture:
    ws = workspace.id
    from_dt = _default_from()

    total_providers = int(
        (
            await db.execute(
                select(func.count(func.distinct(GatewayRoute.provider_id))).where(
                    GatewayRoute.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )
    total_routes = int(
        (
            await db.execute(
                select(func.count(GatewayRoute.id)).where(
                    GatewayRoute.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )

    total_guardrails = int(
        (
            await db.execute(
                select(func.count(GuardrailRule.id)).where(
                    GuardrailRule.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )
    guardrail_events_30d = int(
        (
            await db.execute(
                select(func.count(GuardrailEvent.id)).where(
                    GuardrailEvent.workspace_id == ws,
                    GuardrailEvent.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    cache_configs = int(
        (
            await db.execute(
                select(func.count(ResponseCacheConfig.id)).where(
                    ResponseCacheConfig.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )

    rate_limited_routes = int(
        (
            await db.execute(
                select(func.count(GatewayRoute.id)).where(
                    GatewayRoute.workspace_id == ws,
                    GatewayRoute.rpm_limit.isnot(None),
                )
            )
        ).scalar()
        or 0
    )

    total_runs_30d = int(
        (
            await db.execute(
                select(func.count(AgentRun.id)).where(
                    AgentRun.workspace_id == ws,
                    AgentRun.started_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )
    tool_runs_30d = int(
        (
            await db.execute(
                select(func.count(ToolCall.id)).where(
                    ToolCall.workspace_id == ws,
                    ToolCall.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    total_alert_rules = int(
        (
            await db.execute(
                select(func.count(AlertRule.id)).where(
                    AlertRule.workspace_id == ws, AlertRule.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    alert_firings_30d = int(
        (
            await db.execute(
                select(func.count(AlertFiring.id)).where(
                    AlertFiring.workspace_id == ws,
                    AlertFiring.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    return DataProtectionGatewayPosture(
        workspace_id=str(ws),
        period_days=30,
        provider_context={
            "total_providers": total_providers,
            "total_routes": total_routes,
        },
        guardrail_context={
            "total_guardrails": total_guardrails,
            "guardrail_events_30d": guardrail_events_30d,
        },
        cache_context={
            "cache_configs": cache_configs,
        },
        rate_limit_context={
            "rate_limited_routes": rate_limited_routes,
        },
        run_context={
            "total_runs_30d": total_runs_30d,
            "tool_runs_30d": tool_runs_30d,
        },
        monitoring_context={
            "total_alert_rules": total_alert_rules,
            "alert_firings_30d": alert_firings_30d,
        },
    )


@router.get(
    "/evidence-audit-cross-posture",
    response_model=EvidenceAuditCrossPosture,
)
async def evidence_audit_cross_posture(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EvidenceAuditCrossPosture:
    ws = workspace.id
    from_dt = _default_from()

    active_budgets = int(
        (
            await db.execute(
                select(func.count(Budget.id)).where(
                    Budget.workspace_id == ws, Budget.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    total_chargebacks = int(
        (
            await db.execute(
                select(func.count(ChargebackRule.id)).where(
                    ChargebackRule.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )
    billing_periods = int(
        (
            await db.execute(
                select(func.count(BillingPeriod.id)).where(
                    BillingPeriod.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )
    ledger_snapshots = int(
        (
            await db.execute(
                select(func.count(LedgerSnapshot.id)).where(
                    LedgerSnapshot.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )

    org_name = ""
    if workspace.tenant_id:
        tenant = (
            await db.execute(
                select(Tenant).where(Tenant.id == workspace.tenant_id)
            )
        ).scalar_one_or_none()
        if tenant:
            org_name = tenant.name or ""
    workspace_users = int(
        (
            await db.execute(
                select(func.count(WorkspaceUser.id)).where(
                    WorkspaceUser.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )
    active_api_keys = int(
        (
            await db.execute(
                select(func.count(ApiKey.id)).where(
                    ApiKey.workspace_id == ws, ApiKey.revoked_at.is_(None)
                )
            )
        ).scalar()
        or 0
    )

    total_routes = int(
        (
            await db.execute(
                select(func.count(GatewayRoute.id)).where(
                    GatewayRoute.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )
    total_providers = int(
        (
            await db.execute(
                select(func.count(func.distinct(GatewayRoute.provider_id))).where(
                    GatewayRoute.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )
    rate_limited_routes = int(
        (
            await db.execute(
                select(func.count(GatewayRoute.id)).where(
                    GatewayRoute.workspace_id == ws,
                    GatewayRoute.rpm_limit.isnot(None),
                )
            )
        ).scalar()
        or 0
    )

    audit_events_30d = int(
        (
            await db.execute(
                select(func.count(AuditEvent.id)).where(
                    AuditEvent.workspace_id == ws,
                    AuditEvent.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )
    total_runs_30d = int(
        (
            await db.execute(
                select(func.count(AgentRun.id)).where(
                    AgentRun.workspace_id == ws,
                    AgentRun.started_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )
    total_alert_rules_ev = int(
        (
            await db.execute(
                select(func.count(AlertRule.id)).where(
                    AlertRule.workspace_id == ws, AlertRule.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    alert_firings_30d_ev = int(
        (
            await db.execute(
                select(func.count(AlertFiring.id)).where(
                    AlertFiring.workspace_id == ws,
                    AlertFiring.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    return EvidenceAuditCrossPosture(
        workspace_id=str(ws),
        period_days=30,
        finops_context={
            "active_budgets": active_budgets,
            "billing_periods": billing_periods,
            "chargeback_rules": total_chargebacks,
            "ledger_snapshots": ledger_snapshots,
        },
        org_context={
            "org_name": org_name,
            "workspace_users": workspace_users,
            "active_api_keys": active_api_keys,
        },
        gateway_context={
            "total_providers": total_providers,
            "total_routes": total_routes,
            "rate_limited_routes": rate_limited_routes,
        },
        observe_context={
            "audit_events_30d": audit_events_30d,
            "total_runs_30d": total_runs_30d,
            "total_alert_rules": total_alert_rules_ev,
            "alert_firings_30d": alert_firings_30d_ev,
        },
    )


@router.get(
    "/governance-internal-posture",
    response_model=GovernanceInternalPosture,
)
async def governance_internal_posture(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GovernanceInternalPosture:
    ws = workspace.id
    from_dt = _default_from()

    total_tools = int(
        (
            await db.execute(
                select(func.count(ToolRegistry.id)).where(
                    ToolRegistry.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )
    enforced_tools = int(
        (
            await db.execute(
                select(func.count(ToolRegistry.id)).where(
                    ToolRegistry.workspace_id == ws,
                    ToolRegistry.runtime_enforcement.is_(True),
                )
            )
        ).scalar()
        or 0
    )

    total_policies = int(
        (
            await db.execute(
                select(func.count(ToolPolicy.id)).where(
                    ToolPolicy.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )
    active_policies = int(
        (
            await db.execute(
                select(func.count(ToolPolicy.id)).where(
                    ToolPolicy.workspace_id == ws, ToolPolicy.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )

    pending_approvals = int(
        (
            await db.execute(
                select(func.count(Approval.id)).where(
                    Approval.workspace_id == ws, Approval.status == "pending"
                )
            )
        ).scalar()
        or 0
    )
    total_approvals_30d = int(
        (
            await db.execute(
                select(func.count(Approval.id)).where(
                    Approval.workspace_id == ws,
                    Approval.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    capture_policies = int(
        (
            await db.execute(
                select(func.count(CapturePolicy.id)).where(
                    CapturePolicy.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )
    security_events_30d = int(
        (
            await db.execute(
                select(func.count(SecurityEvent.id)).where(
                    SecurityEvent.workspace_id == ws,
                    SecurityEvent.detected_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    active_alert_rules_gi = int(
        (
            await db.execute(
                select(func.count(AlertRule.id)).where(
                    AlertRule.workspace_id == ws, AlertRule.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    alert_firings_30d_gi = int(
        (
            await db.execute(
                select(func.count(AlertFiring.id)).where(
                    AlertFiring.workspace_id == ws,
                    AlertFiring.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    audit_events_30d_gi = int(
        (
            await db.execute(
                select(func.count(AuditEvent.id)).where(
                    AuditEvent.workspace_id == ws,
                    AuditEvent.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    total_tags = int(
        (
            await db.execute(
                select(func.count(Tag.id)).where(
                    Tag.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )
    active_tags = int(
        (
            await db.execute(
                select(func.count(Tag.id)).where(
                    Tag.workspace_id == ws, Tag.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )

    return GovernanceInternalPosture(
        workspace_id=str(ws),
        period_days=30,
        tool_registry_context={
            "total_tools": total_tools,
            "enforced_tools": enforced_tools,
        },
        tool_policies_context={
            "total_policies": total_policies,
            "active_policies": active_policies,
        },
        approvals_context={
            "pending_approvals": pending_approvals,
            "total_approvals_30d": total_approvals_30d,
        },
        data_capture_context={
            "capture_policies": capture_policies,
            "security_events_30d": security_events_30d,
        },
        security_context={
            "security_events_30d": security_events_30d,
        },
        alert_rules_context={
            "active_alert_rules": active_alert_rules_gi,
            "alert_firings_30d": alert_firings_30d_gi,
        },
        audit_context={
            "audit_events_30d": audit_events_30d_gi,
        },
        tags_context={
            "total_tags": total_tags,
            "active_tags": active_tags,
        },
    )


@router.get(
    "/tool-registry-runtime-posture",
    response_model=ToolRegistryRuntimePosture,
)
async def tool_registry_runtime_posture(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ToolRegistryRuntimePosture:
    ws = workspace.id
    from_dt = _default_from()

    total_workspaces_trp = int(
        (
            await db.execute(
                select(func.count(Workspace.id)).where(
                    Workspace.tenant_id == workspace.tenant_id
                )
            )
        ).scalar()
        or 0
    )
    workspace_scoped_tools = int(
        (
            await db.execute(
                select(func.count(ToolRegistry.id)).where(
                    ToolRegistry.workspace_id == ws,
                    ToolRegistry.runtime_enforcement.is_(True),
                )
            )
        ).scalar()
        or 0
    )

    active_keys_trp = int(
        (
            await db.execute(
                select(func.count(ApiKey.id)).where(
                    ApiKey.workspace_id == ws, ApiKey.revoked_at.is_(None)
                )
            )
        ).scalar()
        or 0
    )
    keys_with_tool_calls_30d = int(
        (
            await db.execute(
                select(func.count(func.distinct(ProviderCall.api_key_id))).where(
                    ProviderCall.workspace_id == ws,
                    ProviderCall.created_at >= from_dt,
                    ProviderCall.tool_call_id.isnot(None),
                )
            )
        ).scalar()
        or 0
    )

    mcp_servers_total_trp = int(
        (
            await db.execute(
                select(func.count(McpServer.id)).where(
                    McpServer.workspace_id == ws, McpServer.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    mcp_tool_calls_30d = int(
        (
            await db.execute(
                select(func.count(McpToolCall.id)).where(
                    McpToolCall.workspace_id == ws,
                    McpToolCall.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    model_routes_trp = int(
        (
            await db.execute(
                select(func.count(GatewayRoute.id)).where(
                    GatewayRoute.workspace_id == ws,
                    GatewayRoute.is_active.is_(True),
                )
            )
        ).scalar()
        or 0
    )
    cached_responses_30d = int(
        (
            await db.execute(
                select(func.count(ResponseCacheConfig.id)).where(
                    ResponseCacheConfig.workspace_id == ws,
                    ResponseCacheConfig.is_enabled.is_(True),
                )
            )
        ).scalar()
        or 0
    )
    rate_limited_routes_trp = int(
        (
            await db.execute(
                select(func.count(GatewayRoute.id)).where(
                    GatewayRoute.workspace_id == ws,
                    GatewayRoute.per_user_rpm_limit.isnot(None),
                )
            )
        ).scalar()
        or 0
    )

    tool_runs_30d_trp = int(
        (
            await db.execute(
                select(func.count(AgentRun.id)).where(
                    AgentRun.workspace_id == ws,
                    AgentRun.started_at >= from_dt,
                    AgentRun.feature_tag.isnot(None),
                )
            )
        ).scalar()
        or 0
    )
    tool_requests_30d = int(
        (
            await db.execute(
                select(func.count(ProviderCall.id)).where(
                    ProviderCall.workspace_id == ws,
                    ProviderCall.created_at >= from_dt,
                    ProviderCall.tool_call_id.isnot(None),
                )
            )
        ).scalar()
        or 0
    )

    tool_scoped_budgets_trp = int(
        (
            await db.execute(
                select(func.count(Budget.id)).where(
                    Budget.workspace_id == ws,
                    Budget.is_active.is_(True),
                    Budget.scope_type == "feature_tag",
                )
            )
        ).scalar()
        or 0
    )
    budget_notifications_30d = int(
        (
            await db.execute(
                select(func.count(BudgetNotification.id)).where(
                    BudgetNotification.workspace_id == ws,
                    BudgetNotification.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    return ToolRegistryRuntimePosture(
        workspace_id=str(ws),
        period_days=30,
        workspace_scope={
            "total_workspaces": total_workspaces_trp,
            "workspace_scoped_tools": workspace_scoped_tools,
        },
        api_key_scope={
            "active_keys": active_keys_trp,
            "keys_with_tool_calls_30d": keys_with_tool_calls_30d,
        },
        mcp_scope={
            "active_mcp_servers": mcp_servers_total_trp,
            "mcp_tool_calls_30d": mcp_tool_calls_30d,
        },
        gateway_runtime={
            "model_routes": model_routes_trp,
            "cache_configs_active": cached_responses_30d,
            "rate_limited_routes": rate_limited_routes_trp,
        },
        observe_evidence={
            "tool_runs_30d": tool_runs_30d_trp,
            "tool_requests_30d": tool_requests_30d,
        },
        budget_linkage={
            "tool_scoped_budgets": tool_scoped_budgets_trp,
            "budget_notifications_30d": budget_notifications_30d,
        },
    )


@router.get(
    "/tool-policies-runtime-posture",
    response_model=ToolPoliciesRuntimePosture,
)
async def tool_policies_runtime_posture(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ToolPoliciesRuntimePosture:
    ws = workspace.id
    from_dt = _default_from()

    total_workspaces_tpr = int(
        (
            await db.execute(
                select(func.count(Workspace.id)).where(
                    Workspace.tenant_id == workspace.tenant_id
                )
            )
        ).scalar()
        or 0
    )
    workspace_scoped_policies = int(
        (
            await db.execute(
                select(func.count(ToolPolicy.id)).where(
                    ToolPolicy.workspace_id == ws,
                    ToolPolicy.is_active.is_(True),
                    ToolPolicy.scope_type == "workspace",
                )
            )
        ).scalar()
        or 0
    )
    access_group_scoped = int(
        (
            await db.execute(
                select(func.count(ToolPolicy.id)).where(
                    ToolPolicy.workspace_id == ws,
                    ToolPolicy.is_active.is_(True),
                    ToolPolicy.scope_type == "access_group",
                )
            )
        ).scalar()
        or 0
    )
    active_api_keys_tpr = int(
        (
            await db.execute(
                select(func.count(ApiKey.id)).where(
                    ApiKey.workspace_id == ws, ApiKey.revoked_at.is_(None)
                )
            )
        ).scalar()
        or 0
    )

    model_routes_tpr = int(
        (
            await db.execute(
                select(func.count(GatewayRoute.id)).where(
                    GatewayRoute.workspace_id == ws,
                    GatewayRoute.is_active.is_(True),
                )
            )
        ).scalar()
        or 0
    )
    guardrail_rules_tpr = int(
        (
            await db.execute(
                select(func.count(GuardrailRule.id)).where(
                    GuardrailRule.workspace_id == ws,
                    GuardrailRule.status == "active",
                )
            )
        ).scalar()
        or 0
    )
    guardrail_events_30d_tpr = int(
        (
            await db.execute(
                select(func.count(GuardrailEvent.id)).where(
                    GuardrailEvent.workspace_id == ws,
                    GuardrailEvent.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    policy_violations_30d = int(
        (
            await db.execute(
                select(func.count(GuardrailEvent.id)).where(
                    GuardrailEvent.workspace_id == ws,
                    GuardrailEvent.created_at >= from_dt,
                    GuardrailEvent.decision == "block",
                )
            )
        ).scalar()
        or 0
    )
    request_flows_30d_tpr = int(
        (
            await db.execute(
                select(func.count(ProviderCall.id)).where(
                    ProviderCall.workspace_id == ws,
                    ProviderCall.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )
    monitoring_alerts_30d_tpr = int(
        (
            await db.execute(
                select(func.count(AlertFiring.id)).where(
                    AlertFiring.workspace_id == ws,
                    AlertFiring.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    total_budgets_tpr = int(
        (
            await db.execute(
                select(func.count(Budget.id)).where(
                    Budget.workspace_id == ws, Budget.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    budget_notifications_30d_tpr = int(
        (
            await db.execute(
                select(func.count(BudgetNotification.id)).where(
                    BudgetNotification.workspace_id == ws,
                    BudgetNotification.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    ledger_snapshots_tpr = int(
        (
            await db.execute(
                select(func.count(LedgerSnapshot.id)).where(
                    LedgerSnapshot.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )
    ledger_entries_30d = int(
        (
            await db.execute(
                select(func.count(LedgerSnapshot.id)).where(
                    LedgerSnapshot.workspace_id == ws,
                    LedgerSnapshot.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    return ToolPoliciesRuntimePosture(
        workspace_id=str(ws),
        period_days=30,
        scope_context={
            "total_workspaces": total_workspaces_tpr,
            "workspace_scoped_policies": workspace_scoped_policies,
            "access_group_scoped_policies": access_group_scoped,
            "active_api_keys": active_api_keys_tpr,
        },
        gateway_enforcement={
            "model_routes": model_routes_tpr,
            "guardrail_rules": guardrail_rules_tpr,
            "guardrail_events_30d": guardrail_events_30d_tpr,
        },
        observe_evidence={
            "policy_violations_30d": policy_violations_30d,
            "request_flows_30d": request_flows_30d_tpr,
            "monitoring_alerts_30d": monitoring_alerts_30d_tpr,
        },
        budget_context={
            "total_budgets": total_budgets_tpr,
            "budget_notifications_30d": budget_notifications_30d_tpr,
        },
        ledger_context={
            "ledger_snapshots": ledger_snapshots_tpr,
            "ledger_entries_30d": ledger_entries_30d,
        },
    )


@router.get(
    "/approvals-runtime-posture",
    response_model=ApprovalsRuntimePosture,
)
async def approvals_runtime_posture(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApprovalsRuntimePosture:
    ws = workspace.id
    from_dt = _default_from()

    workspace_users_arp = int(
        (
            await db.execute(
                select(func.count(WorkspaceUser.id)).where(
                    WorkspaceUser.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )
    active_api_keys_arp = int(
        (
            await db.execute(
                select(func.count(ApiKey.id)).where(
                    ApiKey.workspace_id == ws, ApiKey.revoked_at.is_(None)
                )
            )
        ).scalar()
        or 0
    )
    total_workspaces_arp = int(
        (
            await db.execute(
                select(func.count(Workspace.id)).where(
                    Workspace.tenant_id == workspace.tenant_id
                )
            )
        ).scalar()
        or 0
    )

    model_routes_arp = int(
        (
            await db.execute(
                select(func.count(GatewayRoute.id)).where(
                    GatewayRoute.workspace_id == ws,
                    GatewayRoute.is_active.is_(True),
                )
            )
        ).scalar()
        or 0
    )
    guardrail_rules_arp = int(
        (
            await db.execute(
                select(func.count(GuardrailRule.id)).where(
                    GuardrailRule.workspace_id == ws,
                    GuardrailRule.status == "active",
                )
            )
        ).scalar()
        or 0
    )

    runs_30d_arp = int(
        (
            await db.execute(
                select(func.count(AgentRun.id)).where(
                    AgentRun.workspace_id == ws,
                    AgentRun.started_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )
    approval_linked_runs_30d = int(
        (
            await db.execute(
                select(func.count(AgentRun.id)).where(
                    AgentRun.workspace_id == ws,
                    AgentRun.started_at >= from_dt,
                    AgentRun.feature_tag.isnot(None),
                )
            )
        ).scalar()
        or 0
    )

    active_alert_rules_arp = int(
        (
            await db.execute(
                select(func.count(AlertRule.id)).where(
                    AlertRule.workspace_id == ws, AlertRule.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    alert_firings_30d_arp = int(
        (
            await db.execute(
                select(func.count(AlertFiring.id)).where(
                    AlertFiring.workspace_id == ws,
                    AlertFiring.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    total_budgets_arp = int(
        (
            await db.execute(
                select(func.count(Budget.id)).where(
                    Budget.workspace_id == ws, Budget.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    budget_increase_approvals_30d = int(
        (
            await db.execute(
                select(func.count(Approval.id)).where(
                    Approval.workspace_id == ws,
                    Approval.request_type == "budget_increase",
                    Approval.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    return ApprovalsRuntimePosture(
        workspace_id=str(ws),
        period_days=30,
        requester_context={
            "workspace_users": workspace_users_arp,
            "active_api_keys": active_api_keys_arp,
            "total_workspaces": total_workspaces_arp,
        },
        gateway_escalation={
            "model_routes": model_routes_arp,
            "guardrail_rules": guardrail_rules_arp,
        },
        observe_evidence={
            "runs_30d": runs_30d_arp,
            "approval_linked_runs_30d": approval_linked_runs_30d,
        },
        monitoring_context={
            "active_alert_rules": active_alert_rules_arp,
            "alert_firings_30d": alert_firings_30d_arp,
        },
        budget_context={
            "total_budgets": total_budgets_arp,
            "budget_increase_approvals_30d": budget_increase_approvals_30d,
        },
    )


@router.get(
    "/data-capture-runtime-posture",
    response_model=DataCaptureRuntimePosture,
)
async def data_capture_runtime_posture(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataCaptureRuntimePosture:
    ws = workspace.id
    from_dt = _default_from()

    total_workspaces_dcp = int(
        (
            await db.execute(
                select(func.count(Workspace.id)).where(
                    Workspace.tenant_id == workspace.tenant_id
                )
            )
        ).scalar()
        or 0
    )
    capture_policies_dcp = int(
        (
            await db.execute(
                select(func.count(CapturePolicy.id)).where(
                    CapturePolicy.workspace_id == ws,
                )
            )
        ).scalar()
        or 0
    )
    active_api_keys_dcp = int(
        (
            await db.execute(
                select(func.count(ApiKey.id)).where(
                    ApiKey.workspace_id == ws, ApiKey.revoked_at.is_(None)
                )
            )
        ).scalar()
        or 0
    )
    security_events_30d_dcp = int(
        (
            await db.execute(
                select(func.count(SecurityEvent.id)).where(
                    SecurityEvent.workspace_id == ws,
                    SecurityEvent.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    provider_calls_30d_dcp = int(
        (
            await db.execute(
                select(func.count(ProviderCall.id)).where(
                    ProviderCall.workspace_id == ws,
                    ProviderCall.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )
    model_routes_dcp = int(
        (
            await db.execute(
                select(func.count(GatewayRoute.id)).where(
                    GatewayRoute.workspace_id == ws,
                    GatewayRoute.is_active.is_(True),
                )
            )
        ).scalar()
        or 0
    )
    cache_configs_dcp = int(
        (
            await db.execute(
                select(func.count(ResponseCacheConfig.id)).where(
                    ResponseCacheConfig.workspace_id == ws,
                    ResponseCacheConfig.is_enabled.is_(True),
                )
            )
        ).scalar()
        or 0
    )

    runs_30d_dcp = int(
        (
            await db.execute(
                select(func.count(AgentRun.id)).where(
                    AgentRun.workspace_id == ws,
                    AgentRun.started_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )
    audit_events_30d_dcp = int(
        (
            await db.execute(
                select(func.count(AuditEvent.id)).where(
                    AuditEvent.workspace_id == ws,
                    AuditEvent.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    total_budgets_dcp = int(
        (
            await db.execute(
                select(func.count(Budget.id)).where(
                    Budget.workspace_id == ws, Budget.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    budget_notifications_30d_dcp = int(
        (
            await db.execute(
                select(func.count(BudgetNotification.id)).where(
                    BudgetNotification.workspace_id == ws,
                    BudgetNotification.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    ledger_snapshots_dcp = int(
        (
            await db.execute(
                select(func.count(LedgerSnapshot.id)).where(
                    LedgerSnapshot.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )
    ledger_entries_30d_dcp = int(
        (
            await db.execute(
                select(func.count(LedgerSnapshot.id)).where(
                    LedgerSnapshot.workspace_id == ws,
                    LedgerSnapshot.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    return DataCaptureRuntimePosture(
        workspace_id=str(ws),
        period_days=30,
        capture_scope={
            "total_workspaces": total_workspaces_dcp,
            "capture_policies": capture_policies_dcp,
            "active_api_keys": active_api_keys_dcp,
            "security_events_30d": security_events_30d_dcp,
        },
        gateway_evidence={
            "provider_calls_30d": provider_calls_30d_dcp,
            "model_routes": model_routes_dcp,
            "cache_configs_active": cache_configs_dcp,
        },
        observe_evidence={
            "runs_30d": runs_30d_dcp,
            "audit_events_30d": audit_events_30d_dcp,
        },
        budget_context={
            "total_budgets": total_budgets_dcp,
            "budget_notifications_30d": budget_notifications_30d_dcp,
        },
        ledger_context={
            "ledger_snapshots": ledger_snapshots_dcp,
            "ledger_entries_30d": ledger_entries_30d_dcp,
        },
    )


@router.get(
    "/security-runtime-posture",
    response_model=SecurityRuntimePosture,
)
async def security_runtime_posture(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SecurityRuntimePosture:
    ws = workspace.id
    from_dt = _default_from()

    workspace_users_srp = int(
        (
            await db.execute(
                select(func.count(WorkspaceUser.id)).where(
                    WorkspaceUser.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )
    total_workspaces_srp = int(
        (
            await db.execute(
                select(func.count(Workspace.id)).where(
                    Workspace.tenant_id == workspace.tenant_id
                )
            )
        ).scalar()
        or 0
    )
    active_api_keys_srp = int(
        (
            await db.execute(
                select(func.count(ApiKey.id)).where(
                    ApiKey.workspace_id == ws, ApiKey.revoked_at.is_(None)
                )
            )
        ).scalar()
        or 0
    )
    security_events_30d_srp = int(
        (
            await db.execute(
                select(func.count(SecurityEvent.id)).where(
                    SecurityEvent.workspace_id == ws,
                    SecurityEvent.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    model_routes_srp = int(
        (
            await db.execute(
                select(func.count(GatewayRoute.id)).where(
                    GatewayRoute.workspace_id == ws,
                    GatewayRoute.is_active.is_(True),
                )
            )
        ).scalar()
        or 0
    )
    guardrail_rules_srp = int(
        (
            await db.execute(
                select(func.count(GuardrailRule.id)).where(
                    GuardrailRule.workspace_id == ws,
                    GuardrailRule.status == "active",
                )
            )
        ).scalar()
        or 0
    )
    guardrail_events_30d_srp = int(
        (
            await db.execute(
                select(func.count(GuardrailEvent.id)).where(
                    GuardrailEvent.workspace_id == ws,
                    GuardrailEvent.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    runs_30d_srp = int(
        (
            await db.execute(
                select(func.count(AgentRun.id)).where(
                    AgentRun.workspace_id == ws,
                    AgentRun.started_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )
    provider_calls_30d_srp = int(
        (
            await db.execute(
                select(func.count(ProviderCall.id)).where(
                    ProviderCall.workspace_id == ws,
                    ProviderCall.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    active_alert_rules_srp = int(
        (
            await db.execute(
                select(func.count(AlertRule.id)).where(
                    AlertRule.workspace_id == ws, AlertRule.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    alert_firings_30d_srp = int(
        (
            await db.execute(
                select(func.count(AlertFiring.id)).where(
                    AlertFiring.workspace_id == ws,
                    AlertFiring.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    chargeback_rules_srp = int(
        (
            await db.execute(
                select(func.count(ChargebackRule.id)).where(
                    ChargebackRule.workspace_id == ws,
                    ChargebackRule.status == "active",
                )
            )
        ).scalar()
        or 0
    )
    ledger_snapshots_srp = int(
        (
            await db.execute(
                select(func.count(LedgerSnapshot.id)).where(
                    LedgerSnapshot.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )
    ledger_entries_30d_srp = int(
        (
            await db.execute(
                select(func.count(LedgerSnapshot.id)).where(
                    LedgerSnapshot.workspace_id == ws,
                    LedgerSnapshot.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    return SecurityRuntimePosture(
        workspace_id=str(ws),
        period_days=30,
        identity_context={
            "workspace_users": workspace_users_srp,
            "total_workspaces": total_workspaces_srp,
            "active_api_keys": active_api_keys_srp,
            "security_events_30d": security_events_30d_srp,
        },
        gateway_posture={
            "model_routes": model_routes_srp,
            "guardrail_rules": guardrail_rules_srp,
            "guardrail_events_30d": guardrail_events_30d_srp,
        },
        observe_evidence={
            "runs_30d": runs_30d_srp,
            "provider_calls_30d": provider_calls_30d_srp,
        },
        monitoring_context={
            "active_alert_rules": active_alert_rules_srp,
            "alert_firings_30d": alert_firings_30d_srp,
        },
        finops_context={
            "chargeback_rules": chargeback_rules_srp,
            "ledger_snapshots": ledger_snapshots_srp,
            "ledger_entries_30d": ledger_entries_30d_srp,
        },
    )


@router.get(
    "/alert-rules-runtime-posture",
    response_model=AlertRulesRuntimePosture,
)
async def alert_rules_runtime_posture(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AlertRulesRuntimePosture:
    ws = workspace.id
    from_dt = _default_from()

    active_alert_rules_arr = int(
        (
            await db.execute(
                select(func.count(AlertRule.id)).where(
                    AlertRule.workspace_id == ws, AlertRule.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    alert_firings_30d_arr = int(
        (
            await db.execute(
                select(func.count(AlertFiring.id)).where(
                    AlertFiring.workspace_id == ws,
                    AlertFiring.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )
    total_workspaces_arr = int(
        (
            await db.execute(
                select(func.count(Workspace.id)).where(
                    Workspace.tenant_id == workspace.tenant_id
                )
            )
        ).scalar()
        or 0
    )

    model_routes_arr = int(
        (
            await db.execute(
                select(func.count(GatewayRoute.id)).where(
                    GatewayRoute.workspace_id == ws,
                    GatewayRoute.is_active.is_(True),
                )
            )
        ).scalar()
        or 0
    )
    guardrail_rules_arr = int(
        (
            await db.execute(
                select(func.count(GuardrailRule.id)).where(
                    GuardrailRule.workspace_id == ws,
                    GuardrailRule.status == "active",
                )
            )
        ).scalar()
        or 0
    )
    rate_limited_routes_arr = int(
        (
            await db.execute(
                select(func.count(GatewayRoute.id)).where(
                    GatewayRoute.workspace_id == ws,
                    GatewayRoute.is_active.is_(True),
                    GatewayRoute.per_user_rpm_limit.isnot(None),
                )
            )
        ).scalar()
        or 0
    )

    runs_30d_arr = int(
        (
            await db.execute(
                select(func.count(AgentRun.id)).where(
                    AgentRun.workspace_id == ws,
                    AgentRun.started_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )
    provider_calls_30d_arr = int(
        (
            await db.execute(
                select(func.count(ProviderCall.id)).where(
                    ProviderCall.workspace_id == ws,
                    ProviderCall.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    chargeback_rules_arr = int(
        (
            await db.execute(
                select(func.count(ChargebackRule.id)).where(
                    ChargebackRule.workspace_id == ws,
                    ChargebackRule.status == "active",
                )
            )
        ).scalar()
        or 0
    )
    active_budgets_arr = int(
        (
            await db.execute(
                select(func.count(Budget.id)).where(
                    Budget.workspace_id == ws, Budget.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    budget_notifications_30d_arr = int(
        (
            await db.execute(
                select(func.count(BudgetNotification.id)).where(
                    BudgetNotification.workspace_id == ws,
                    BudgetNotification.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    return AlertRulesRuntimePosture(
        workspace_id=str(ws),
        period_days=30,
        ops_context={
            "active_alert_rules": active_alert_rules_arr,
            "alert_firings_30d": alert_firings_30d_arr,
            "total_workspaces": total_workspaces_arr,
        },
        gateway_runtime={
            "model_routes": model_routes_arr,
            "guardrail_rules": guardrail_rules_arr,
            "rate_limited_routes": rate_limited_routes_arr,
        },
        observe_evidence={
            "runs_30d": runs_30d_arr,
            "provider_calls_30d": provider_calls_30d_arr,
        },
        finops_context={
            "chargeback_rules": chargeback_rules_arr,
            "active_budgets": active_budgets_arr,
            "budget_notifications_30d": budget_notifications_30d_arr,
        },
    )


@router.get(
    "/audit-log-runtime-posture",
    response_model=AuditLogRuntimePosture,
)
async def audit_log_runtime_posture(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuditLogRuntimePosture:
    ws = workspace.id
    from_dt = _default_from()

    audit_events_30d_alr = int(
        (
            await db.execute(
                select(func.count(AuditEvent.id)).where(
                    AuditEvent.workspace_id == ws,
                    AuditEvent.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )
    workspace_users_alr = int(
        (
            await db.execute(
                select(func.count(WorkspaceUser.id)).where(
                    WorkspaceUser.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )
    api_keys_alr = int(
        (
            await db.execute(
                select(func.count(ApiKey.id)).where(
                    ApiKey.workspace_id == ws, ApiKey.revoked_at.is_(None)
                )
            )
        ).scalar()
        or 0
    )

    guardrail_rules_alr = int(
        (
            await db.execute(
                select(func.count(GuardrailRule.id)).where(
                    GuardrailRule.workspace_id == ws,
                    GuardrailRule.status == "active",
                )
            )
        ).scalar()
        or 0
    )
    cache_configs_alr = int(
        (
            await db.execute(
                select(func.count(ResponseCacheConfig.id)).where(
                    ResponseCacheConfig.workspace_id == ws,
                    ResponseCacheConfig.is_enabled.is_(True),
                )
            )
        ).scalar()
        or 0
    )
    rate_limited_routes_alr = int(
        (
            await db.execute(
                select(func.count(GatewayRoute.id)).where(
                    GatewayRoute.workspace_id == ws,
                    GatewayRoute.is_active.is_(True),
                    GatewayRoute.per_user_rpm_limit.isnot(None),
                )
            )
        ).scalar()
        or 0
    )

    runs_30d_alr = int(
        (
            await db.execute(
                select(func.count(AgentRun.id)).where(
                    AgentRun.workspace_id == ws,
                    AgentRun.started_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )
    provider_calls_30d_alr = int(
        (
            await db.execute(
                select(func.count(ProviderCall.id)).where(
                    ProviderCall.workspace_id == ws,
                    ProviderCall.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    active_budgets_alr = int(
        (
            await db.execute(
                select(func.count(Budget.id)).where(
                    Budget.workspace_id == ws, Budget.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    ledger_snapshots_30d_alr = int(
        (
            await db.execute(
                select(func.count(LedgerSnapshot.id)).where(
                    LedgerSnapshot.workspace_id == ws,
                    LedgerSnapshot.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    return AuditLogRuntimePosture(
        workspace_id=str(ws),
        period_days=30,
        evidence_scope={
            "audit_events_30d": audit_events_30d_alr,
            "workspace_users": workspace_users_alr,
            "active_api_keys": api_keys_alr,
        },
        gateway_lineage={
            "guardrail_rules": guardrail_rules_alr,
            "cache_configs": cache_configs_alr,
            "rate_limited_routes": rate_limited_routes_alr,
        },
        observe_lineage={
            "runs_30d": runs_30d_alr,
            "provider_calls_30d": provider_calls_30d_alr,
        },
        finops_lineage={
            "active_budgets": active_budgets_alr,
            "ledger_snapshots_30d": ledger_snapshots_30d_alr,
        },
    )


@router.get(
    "/governance-pack-runtime-posture",
    response_model=GovernancePackRuntimePosture,
)
async def governance_pack_runtime_posture(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GovernancePackRuntimePosture:
    ws = workspace.id
    from_dt = _default_from()

    total_workspaces_gpr = int(
        (
            await db.execute(
                select(func.count(Workspace.id)).where(
                    Workspace.tenant_id == workspace.tenant_id
                )
            )
        ).scalar()
        or 0
    )
    workspace_users_gpr = int(
        (
            await db.execute(
                select(func.count(WorkspaceUser.id)).where(
                    WorkspaceUser.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )
    active_budgets_gpr = int(
        (
            await db.execute(
                select(func.count(Budget.id)).where(
                    Budget.workspace_id == ws, Budget.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )

    guardrail_rules_gpr = int(
        (
            await db.execute(
                select(func.count(GuardrailRule.id)).where(
                    GuardrailRule.workspace_id == ws,
                    GuardrailRule.status == "active",
                )
            )
        ).scalar()
        or 0
    )
    audit_events_30d_gpr = int(
        (
            await db.execute(
                select(func.count(AuditEvent.id)).where(
                    AuditEvent.workspace_id == ws,
                    AuditEvent.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )
    active_tags_gpr = int(
        (
            await db.execute(
                select(func.count(Tag.id)).where(
                    Tag.workspace_id == ws, Tag.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )

    alert_firings_30d_gpr = int(
        (
            await db.execute(
                select(func.count(AlertFiring.id)).where(
                    AlertFiring.workspace_id == ws,
                    AlertFiring.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )
    guardrail_events_30d_gpr = int(
        (
            await db.execute(
                select(func.count(GuardrailEvent.id)).where(
                    GuardrailEvent.workspace_id == ws,
                    GuardrailEvent.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    budget_notifications_30d_gpr = int(
        (
            await db.execute(
                select(func.count(BudgetNotification.id)).where(
                    BudgetNotification.workspace_id == ws,
                    BudgetNotification.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )
    ledger_snapshots_30d_gpr = int(
        (
            await db.execute(
                select(func.count(LedgerSnapshot.id)).where(
                    LedgerSnapshot.workspace_id == ws,
                    LedgerSnapshot.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    return GovernancePackRuntimePosture(
        workspace_id=str(ws),
        period_days=30,
        scope_context={
            "total_workspaces": total_workspaces_gpr,
            "workspace_users": workspace_users_gpr,
            "active_budgets": active_budgets_gpr,
        },
        governance_sources={
            "guardrail_rules": guardrail_rules_gpr,
            "audit_events_30d": audit_events_30d_gpr,
            "active_tags": active_tags_gpr,
        },
        monitoring_evidence={
            "alert_firings_30d": alert_firings_30d_gpr,
            "guardrail_events_30d": guardrail_events_30d_gpr,
        },
        finops_evidence={
            "budget_notifications_30d": budget_notifications_30d_gpr,
            "ledger_snapshots_30d": ledger_snapshots_30d_gpr,
        },
    )


@router.get(
    "/tags-runtime-posture",
    response_model=TagsRuntimePosture,
)
async def tags_runtime_posture(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TagsRuntimePosture:
    ws = workspace.id
    from_dt = _default_from()

    active_tags_trp = int(
        (
            await db.execute(
                select(func.count(Tag.id)).where(
                    Tag.workspace_id == ws, Tag.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    total_tags_trp = int(
        (
            await db.execute(
                select(func.count(Tag.id)).where(Tag.workspace_id == ws)
            )
        ).scalar()
        or 0
    )
    workspace_users_trp = int(
        (
            await db.execute(
                select(func.count(WorkspaceUser.id)).where(
                    WorkspaceUser.workspace_id == ws
                )
            )
        ).scalar()
        or 0
    )

    tool_policies_trp = int(
        (
            await db.execute(
                select(func.count(ToolPolicy.id)).where(
                    ToolPolicy.workspace_id == ws,
                    ToolPolicy.is_active.is_(True),
                )
            )
        ).scalar()
        or 0
    )
    audit_events_30d_trp = int(
        (
            await db.execute(
                select(func.count(AuditEvent.id)).where(
                    AuditEvent.workspace_id == ws,
                    AuditEvent.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )
    guardrail_rules_trp = int(
        (
            await db.execute(
                select(func.count(GuardrailRule.id)).where(
                    GuardrailRule.workspace_id == ws,
                    GuardrailRule.status == "active",
                )
            )
        ).scalar()
        or 0
    )

    runs_30d_trp = int(
        (
            await db.execute(
                select(func.count(AgentRun.id)).where(
                    AgentRun.workspace_id == ws,
                    AgentRun.started_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )
    provider_calls_30d_trp = int(
        (
            await db.execute(
                select(func.count(ProviderCall.id)).where(
                    ProviderCall.workspace_id == ws,
                    ProviderCall.created_at >= from_dt,
                )
            )
        ).scalar()
        or 0
    )

    active_budgets_trp = int(
        (
            await db.execute(
                select(func.count(Budget.id)).where(
                    Budget.workspace_id == ws, Budget.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    chargeback_rules_trp = int(
        (
            await db.execute(
                select(func.count(ChargebackRule.id)).where(
                    ChargebackRule.workspace_id == ws,
                    ChargebackRule.status == "active",
                )
            )
        ).scalar()
        or 0
    )

    return TagsRuntimePosture(
        workspace_id=str(ws),
        period_days=30,
        taxonomy_scope={
            "active_tags": active_tags_trp,
            "total_tags": total_tags_trp,
            "workspace_users": workspace_users_trp,
        },
        governance_attribution={
            "tool_policies": tool_policies_trp,
            "audit_events_30d": audit_events_30d_trp,
            "guardrail_rules": guardrail_rules_trp,
        },
        observe_attribution={
            "runs_30d": runs_30d_trp,
            "provider_calls_30d": provider_calls_30d_trp,
        },
        finops_attribution={
            "active_budgets": active_budgets_trp,
            "chargeback_rules": chargeback_rules_trp,
        },
    )


@router.get("/budget-org-scope-posture/{budget_id}")
async def budget_org_scope_posture(
    budget_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    budget = (
        await db.execute(
            select(Budget).where(
                Budget.id == budget_id,
                Budget.workspace_id == workspace.id,
            )
        )
    ).scalar_one_or_none()
    if budget is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "Budget not found")

    now = datetime.now(UTC)
    thirty_days_ago = now - timedelta(days=30)

    scope_display_name: str | None = None
    scope_entity: dict = {}

    if budget.scope_type == "access_group" and budget.scope_id:
        try:
            group_id = uuid.UUID(budget.scope_id)
        except ValueError:
            group_id = None
        if group_id:
            group = (
                await db.execute(
                    select(AccessGroup).where(
                        AccessGroup.id == group_id,
                        AccessGroup.workspace_id == workspace.id,
                    )
                )
            ).scalar_one_or_none()
            if group:
                scope_display_name = group.name
                scope_entity = {
                    "id": str(group.id),
                    "name": group.name,
                    "member_count": group.member_count,
                    "is_active": group.is_active,
                    "guardrail_profile": group.guardrail_profile,
                }
    elif budget.scope_type == "api_key" and budget.scope_id:
        try:
            key_id = uuid.UUID(budget.scope_id)
        except ValueError:
            key_id = None
        if key_id:
            api_key = (
                await db.execute(
                    select(ApiKey).where(
                        ApiKey.id == key_id,
                        ApiKey.workspace_id == workspace.id,
                    )
                )
            ).scalar_one_or_none()
            if api_key:
                scope_display_name = api_key.name or api_key.key_prefix
                scope_entity = {
                    "id": str(api_key.id),
                    "name": api_key.name,
                    "key_prefix": api_key.key_prefix,
                    "ownership_type": api_key.ownership_type,
                    "owner_reference": api_key.owner_reference,
                }
    elif budget.scope_type == "workspace":
        scope_display_name = "All workspace traffic"

    workspace_users = (
        await db.execute(
            select(func.count(WorkspaceUser.user_id)).where(
                WorkspaceUser.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    workspace_api_keys = (
        await db.execute(
            select(func.count(ApiKey.id)).where(
                ApiKey.workspace_id == workspace.id,
                ApiKey.revoked_at.is_(None),
            )
        )
    ).scalar() or 0

    workspace_access_groups = (
        await db.execute(
            select(func.count(AccessGroup.id)).where(
                AccessGroup.workspace_id == workspace.id,
                AccessGroup.is_active.is_(True),
            )
        )
    ).scalar() or 0

    total_budgets = (
        await db.execute(
            select(func.count(Budget.id)).where(
                Budget.workspace_id == workspace.id,
                Budget.is_active.is_(True),
            )
        )
    ).scalar() or 0

    total_spend_30d = (
        await db.execute(
            select(func.coalesce(func.sum(ProviderCall.cost_usd), 0)).where(
                ProviderCall.workspace_id == workspace.id,
                ProviderCall.created_at >= thirty_days_ago,
            )
        )
    ).scalar() or 0

    hub_model_count = (
        await db.execute(
            select(func.count(HubModel.id)).where(
                HubModel.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    distinct_models_30d = (
        await db.execute(
            select(func.count(sa.distinct(ProviderCall.model))).where(
                ProviderCall.workspace_id == workspace.id,
                ProviderCall.created_at >= thirty_days_ago,
            )
        )
    ).scalar() or 0

    return BudgetOrgScopePosture(
        workspace_id=str(workspace.id),
        budget_id=str(budget_id),
        scope_type=budget.scope_type,
        scope_id=budget.scope_id,
        scope_display_name=scope_display_name,
        org_context={
            "workspace_users": workspace_users,
            "workspace_api_keys": workspace_api_keys,
            "workspace_access_groups": workspace_access_groups,
            "total_active_budgets": total_budgets,
            "total_spend_30d_usd": float(total_spend_30d),
        },
        hub_context={
            "hub_model_count": hub_model_count,
            "distinct_models_30d": distinct_models_30d,
        },
        scope_entity=scope_entity,
    )


@router.get(
    "/budget-detail-observe-posture",
    response_model=BudgetDetailObservePosture,
)
async def budget_detail_observe_posture(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _user: TenantUser = Depends(get_current_user),
    _rl: None = Depends(analytics_rate_limit),
):
    t_from = _default_from()
    t_to = _default_to()

    budget_count = (
        await db.execute(
            select(func.count(Budget.id)).where(Budget.workspace_id == workspace.id)
        )
    ).scalar() or 0

    active_budgets = (
        await db.execute(
            select(func.count(Budget.id)).where(
                Budget.workspace_id == workspace.id,
                Budget.is_active.is_(True),
            )
        )
    ).scalar() or 0

    total_limit = (
        await db.execute(
            select(func.coalesce(func.sum(Budget.limit_usd), 0)).where(
                Budget.workspace_id == workspace.id,
                Budget.is_active.is_(True),
            )
        )
    ).scalar() or 0

    breach_count = (
        await db.execute(
            select(func.count(Budget.id)).where(
                Budget.workspace_id == workspace.id,
                Budget.is_active.is_(True),
                Budget.id == BudgetBreach.budget_id,
            )
        )
    ).scalar() or 0

    total_spend_30d = (
        await db.execute(
            select(func.coalesce(func.sum(ProviderCall.cost_usd), 0)).where(
                ProviderCall.workspace_id == workspace.id,
                ProviderCall.created_at >= t_from,
                ProviderCall.created_at < t_to,
            )
        )
    ).scalar() or 0

    total_runs_30d = (
        await db.execute(
            select(func.count(AgentRun.id)).where(
                AgentRun.workspace_id == workspace.id,
                AgentRun.started_at >= t_from,
                AgentRun.started_at < t_to,
            )
        )
    ).scalar() or 0

    users_with_budgets = (
        await db.execute(
            select(func.count(func.distinct(Budget.scope_id))).where(
                Budget.workspace_id == workspace.id,
                Budget.scope_type == "end_user",
                Budget.is_active.is_(True),
            )
        )
    ).scalar() or 0

    user_scoped_budget_total = (
        await db.execute(
            select(func.coalesce(func.sum(Budget.limit_usd), 0)).where(
                Budget.workspace_id == workspace.id,
                Budget.scope_type == "end_user",
                Budget.is_active.is_(True),
            )
        )
    ).scalar() or 0

    user_scoped_spend = float(
        (
            await db.execute(
                select(func.coalesce(func.sum(Budget.limit_usd), 0)).where(
                    Budget.workspace_id == workspace.id,
                    Budget.scope_type == "end_user",
                    Budget.is_active.is_(True),
                )
            )
        ).scalar() or 0
    )

    active_users_30d = (
        await db.execute(
            select(func.count(func.distinct(AgentRun.end_user_id))).where(
                AgentRun.workspace_id == workspace.id,
                AgentRun.started_at >= t_from,
                AgentRun.started_at < t_to,
            )
        )
    ).scalar() or 0

    feature_scoped_budgets = (
        await db.execute(
            select(func.count(Budget.id)).where(
                Budget.workspace_id == workspace.id,
                Budget.scope_type == "feature_tag",
                Budget.is_active.is_(True),
            )
        )
    ).scalar() or 0

    distinct_models_30d = (
        await db.execute(
            select(func.count(func.distinct(ProviderCall.model))).where(
                ProviderCall.workspace_id == workspace.id,
                ProviderCall.created_at >= t_from,
                ProviderCall.created_at < t_to,
            )
        )
    ).scalar() or 0

    avg_cost_per_run = float(total_spend_30d) / total_runs_30d if total_runs_30d > 0 else 0.0

    return BudgetDetailObservePosture(
        workspace_id=str(workspace.id),
        period_days=30,
        budget_context={
            "budgets": budget_count,
            "active_budgets": active_budgets,
            "total_limit_usd": float(total_limit),
            "breach_count": breach_count,
        },
        spend_context={
            "total_spend_30d": float(total_spend_30d),
            "total_runs_30d": total_runs_30d,
            "avg_cost_per_run": avg_cost_per_run,
            "distinct_models_30d": distinct_models_30d,
        },
        user_budget_context={
            "users_with_budgets": users_with_budgets,
            "active_users_30d": active_users_30d,
            "user_scoped_budget_total": float(user_scoped_budget_total),
            "user_scoped_spend": float(user_scoped_spend),
        },
        engineering_context={
            "feature_scoped_budgets": feature_scoped_budgets,
            "active_budgets": active_budgets,
            "breach_count": breach_count,
            "total_limit_usd": float(total_limit),
        },
    )


@router.get(
    "/budget-override-governance-posture",
    response_model=BudgetOverrideGovernancePosture,
)
async def budget_override_governance_posture(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _user: TenantUser = Depends(get_current_user),
    _rl: None = Depends(analytics_rate_limit),
):
    t_from = _default_from()
    t_to = _default_to()

    ws_budgets = select(Budget.id).where(Budget.workspace_id == workspace.id).scalar_subquery()

    total_overrides = (
        await db.execute(
            select(func.count(BudgetOverride.id)).where(
                BudgetOverride.budget_id.in_(
                    select(Budget.id).where(Budget.workspace_id == workspace.id)
                )
            )
        )
    ).scalar() or 0

    active_overrides = (
        await db.execute(
            select(func.count(BudgetOverride.id)).where(
                BudgetOverride.budget_id.in_(
                    select(Budget.id).where(Budget.workspace_id == workspace.id)
                ),
                BudgetOverride.status == "active",
            )
        )
    ).scalar() or 0

    overrides_with_approval = (
        await db.execute(
            select(func.count(BudgetOverride.id)).where(
                BudgetOverride.budget_id.in_(
                    select(Budget.id).where(Budget.workspace_id == workspace.id)
                ),
                BudgetOverride.approved_by.isnot(None),
            )
        )
    ).scalar() or 0

    pending_approvals = (
        await db.execute(
            select(func.count(Approval.id)).where(
                Approval.workspace_id == workspace.id,
                Approval.entity_type == "budget_override",
                Approval.status == "pending",
            )
        )
    ).scalar() or 0

    approved_30d = (
        await db.execute(
            select(func.count(Approval.id)).where(
                Approval.workspace_id == workspace.id,
                Approval.entity_type == "budget_override",
                Approval.status == "approved",
                Approval.updated_at >= t_from,
                Approval.updated_at < t_to,
            )
        )
    ).scalar() or 0

    denied_30d = (
        await db.execute(
            select(func.count(Approval.id)).where(
                Approval.workspace_id == workspace.id,
                Approval.entity_type == "budget_override",
                Approval.status == "denied",
                Approval.updated_at >= t_from,
                Approval.updated_at < t_to,
            )
        )
    ).scalar() or 0

    budget_alerts = (
        await db.execute(
            select(func.count(AlertRule.id)).where(
                AlertRule.workspace_id == workspace.id,
                AlertRule.metric.in_(["budget_spend", "budget_breach", "budget_utilization"]),
            )
        )
    ).scalar() or 0

    active_budget_alerts = (
        await db.execute(
            select(func.count(AlertRule.id)).where(
                AlertRule.workspace_id == workspace.id,
                AlertRule.metric.in_(["budget_spend", "budget_breach", "budget_utilization"]),
                AlertRule.is_active.is_(True),
            )
        )
    ).scalar() or 0

    audit_events_30d = (
        await db.execute(
            select(func.count(AuditEvent.id)).where(
                AuditEvent.workspace_id == workspace.id,
                AuditEvent.entity_type == "budget_override",
                AuditEvent.created_at >= t_from,
                AuditEvent.created_at < t_to,
            )
        )
    ).scalar() or 0

    budget_tags = (
        await db.execute(
            select(func.count(Tag.id)).where(
                Tag.workspace_id == workspace.id,
                Tag.entity_type == "budget",
            )
        )
    ).scalar() or 0

    override_tags = (
        await db.execute(
            select(func.count(Tag.id)).where(
                Tag.workspace_id == workspace.id,
                Tag.entity_type == "budget_override",
            )
        )
    ).scalar() or 0

    return BudgetOverrideGovernancePosture(
        workspace_id=str(workspace.id),
        period_days=30,
        approval_context={
            "pending_approvals": pending_approvals,
            "approved_30d": approved_30d,
            "denied_30d": denied_30d,
            "overrides_with_approval": overrides_with_approval,
        },
        alert_context={
            "budget_alert_rules": budget_alerts,
            "active_budget_alerts": active_budget_alerts,
        },
        audit_context={
            "override_audit_events_30d": audit_events_30d,
            "total_overrides": total_overrides,
            "active_overrides": active_overrides,
        },
        governance_context={
            "approval_coverage_pct": round(
                overrides_with_approval / total_overrides * 100
            ) if total_overrides > 0 else 0,
            "active_overrides": active_overrides,
        },
        tag_context={
            "budget_tags": budget_tags,
            "override_tags": override_tags,
        },
    )


@router.get(
    "/budget-detail-build-posture",
    response_model=BudgetDetailBuildPosture,
)
async def budget_detail_build_posture(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _user: TenantUser = Depends(get_current_user),
    _rl: None = Depends(analytics_rate_limit),
):
    t_from = _default_from()
    t_to = _default_to()

    active_budgets = (
        await db.execute(
            select(func.count(Budget.id)).where(
                Budget.workspace_id == workspace.id,
                Budget.is_active.is_(True),
            )
        )
    ).scalar() or 0

    total_limit = (
        await db.execute(
            select(func.coalesce(func.sum(Budget.limit_usd), 0)).where(
                Budget.workspace_id == workspace.id,
                Budget.is_active.is_(True),
            )
        )
    ).scalar() or 0

    breach_count = (
        await db.execute(
            select(func.count(Budget.id)).where(
                Budget.workspace_id == workspace.id,
                Budget.is_active.is_(True),
                Budget.id == BudgetBreach.budget_id,
            )
        )
    ).scalar() or 0

    feature_budgets = (
        await db.execute(
            select(func.count(Budget.id)).where(
                Budget.workspace_id == workspace.id,
                Budget.scope_type == "feature_tag",
                Budget.is_active.is_(True),
            )
        )
    ).scalar() or 0

    prompt_count = (
        await db.execute(
            select(func.count(Prompt.id)).where(
                Prompt.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    agent_count = (
        await db.execute(
            select(func.count(Agent.id)).where(
                Agent.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    workflow_count = (
        await db.execute(
            select(func.count(WorkflowDefinition.id)).where(
                WorkflowDefinition.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    workflow_runs_30d = (
        await db.execute(
            select(func.count(WorkflowRun.id)).where(
                WorkflowRun.workspace_id == workspace.id,
                WorkflowRun.started_at >= t_from,
                WorkflowRun.started_at < t_to,
            )
        )
    ).scalar() or 0

    eval_experiments = (
        await db.execute(
            select(func.count(EvalExperiment.id)).where(
                EvalExperiment.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    eval_experiments_30d = (
        await db.execute(
            select(func.count(EvalExperiment.id)).where(
                EvalExperiment.workspace_id == workspace.id,
                EvalExperiment.created_at >= t_from,
                EvalExperiment.created_at < t_to,
            )
        )
    ).scalar() or 0

    replay_experiments = (
        await db.execute(
            select(func.count(ReplayExperiment.id)).where(
                ReplayExperiment.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    replay_experiments_30d = (
        await db.execute(
            select(func.count(ReplayExperiment.id)).where(
                ReplayExperiment.workspace_id == workspace.id,
                ReplayExperiment.created_at >= t_from,
                ReplayExperiment.created_at < t_to,
            )
        )
    ).scalar() or 0

    score_events_30d = (
        await db.execute(
            select(func.count(ScoreEvent.id)).where(
                ScoreEvent.workspace_id == workspace.id,
                ScoreEvent.created_at >= t_from,
                ScoreEvent.created_at < t_to,
            )
        )
    ).scalar() or 0

    total_spend_30d = (
        await db.execute(
            select(func.coalesce(func.sum(ProviderCall.cost_usd), 0)).where(
                ProviderCall.workspace_id == workspace.id,
                ProviderCall.created_at >= t_from,
                ProviderCall.created_at < t_to,
            )
        )
    ).scalar() or 0

    distinct_models_30d = (
        await db.execute(
            select(func.count(func.distinct(ProviderCall.model))).where(
                ProviderCall.workspace_id == workspace.id,
                ProviderCall.created_at >= t_from,
                ProviderCall.created_at < t_to,
            )
        )
    ).scalar() or 0

    return BudgetDetailBuildPosture(
        workspace_id=str(workspace.id),
        period_days=30,
        budget_context={
            "active_budgets": active_budgets,
            "total_limit_usd": float(total_limit),
            "breach_count": breach_count,
            "feature_budgets": feature_budgets,
        },
        build_context={
            "prompts": prompt_count,
            "agents": agent_count,
            "workflows": workflow_count,
            "workflow_runs_30d": workflow_runs_30d,
        },
        experiment_context={
            "eval_experiments": eval_experiments,
            "eval_experiments_30d": eval_experiments_30d,
            "replay_experiments": replay_experiments,
            "replay_experiments_30d": replay_experiments_30d,
            "score_events_30d": score_events_30d,
        },
        spend_context={
            "total_spend_30d": float(total_spend_30d),
            "distinct_models_30d": distinct_models_30d,
        },
    )


@router.get(
    "/budget-control-platform-posture",
    response_model=BudgetControlPlatformPosture,
)
async def budget_control_platform_posture(
    admin: tuple = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
    _rl: None = Depends(analytics_rate_limit),
):
    workspace, user = admin
    t_from = _default_from()
    t_to = _default_to()

    rows = (
        await db.execute(
            select(
                Tenant.id,
                Tenant.name,
                func.count(Budget.id).label("budget_count"),
                func.coalesce(func.sum(Budget.limit_usd), 0).label("total_limit"),
                func.count(BudgetBreach.id).label("breach_count"),
            )
            .select_from(Tenant)
            .outerjoin(Workspace, Workspace.tenant_id == Tenant.id)
            .outerjoin(
                Budget,
                sa.and_(
                    Budget.workspace_id == Workspace.id,
                    Budget.is_active.is_(True),
                ),
            )
            .outerjoin(BudgetBreach, BudgetBreach.budget_id == Budget.id)
            .group_by(Tenant.id, Tenant.name)
            .order_by(Tenant.name)
        )
    ).all()

    org_budgets = []
    total_budgets = 0
    total_limit_usd = 0.0
    total_breaches = 0
    for row in rows:
        org_budgets.append({
            "org_id": str(row.id),
            "org_name": row.name,
            "budget_count": row.budget_count,
            "total_limit_usd": float(row.total_limit),
            "breach_count": row.breach_count,
        })
        total_budgets += row.budget_count
        total_limit_usd += float(row.total_limit)
        total_breaches += row.breach_count

    total_overrides = (
        await db.execute(
            select(func.count(BudgetOverride.id)).select_from(BudgetOverride).join(
                Budget, Budget.id == BudgetOverride.budget_id
            )
        )
    ).scalar() or 0

    active_overrides = (
        await db.execute(
            select(func.count(BudgetOverride.id)).select_from(BudgetOverride).join(
                Budget, Budget.id == BudgetOverride.budget_id
            ).where(BudgetOverride.status == "active")
        )
    ).scalar() or 0

    total_spend_30d = (
        await db.execute(
            select(func.coalesce(func.sum(ProviderCall.cost_usd), 0)).where(
                ProviderCall.created_at >= t_from,
                ProviderCall.created_at < t_to,
            )
        )
    ).scalar() or 0

    distinct_models_30d = (
        await db.execute(
            select(func.count(func.distinct(ProviderCall.model))).where(
                ProviderCall.created_at >= t_from,
                ProviderCall.created_at < t_to,
            )
        )
    ).scalar() or 0

    return BudgetControlPlatformPosture(
        period_days=30,
        platform_totals={
            "organizations": len(rows),
            "total_budgets": total_budgets,
            "total_limit_usd": total_limit_usd,
            "total_breaches": total_breaches,
        },
        org_budgets=org_budgets,
        override_context={
            "total_overrides": total_overrides,
            "active_overrides": active_overrides,
        },
        spend_context={
            "total_spend_30d": float(total_spend_30d),
            "distinct_models_30d": distinct_models_30d,
        },
    )


@router.get("/billing-org-scope-posture", response_model=BillingOrgScopePosture)
async def billing_org_scope_posture(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    workspace_id = str(workspace.id)
    t_to = datetime.utcnow()
    t_from = t_to - timedelta(days=30)

    billing_periods = (
        await db.execute(
            select(BillingPeriod).where(BillingPeriod.workspace_id == workspace_id)
        )
    ).scalars().all()

    open_periods = sum(1 for bp in billing_periods if bp.status == "open")
    closed_periods = sum(1 for bp in billing_periods if bp.status == "closed")
    total_billed_usd = sum(float(bp.total_cost_usd or 0) for bp in billing_periods)

    workspace_users = (
        await db.execute(
            select(func.count()).select_from(WorkspaceUser).where(
                WorkspaceUser.workspace_id == workspace_id
            )
        )
    ).scalar() or 0

    access_groups = (
        await db.execute(
            select(func.count()).select_from(AccessGroup).where(
                AccessGroup.workspace_id == workspace_id,
                AccessGroup.is_active.is_(True),
            )
        )
    ).scalar() or 0

    api_keys = (
        await db.execute(
            select(func.count()).select_from(ApiKey).where(
                ApiKey.workspace_id == workspace_id,
                ApiKey.revoked_at.is_(None),
            )
        )
    ).scalar() or 0

    spend_30d = float(
        (
            await db.execute(
                select(func.coalesce(func.sum(ProviderCall.cost_usd), 0)).where(
                    ProviderCall.workspace_id == workspace_id,
                    ProviderCall.created_at >= t_from,
                    ProviderCall.created_at < t_to,
                )
            )
        ).scalar() or 0
    )

    calls_30d = (
        await db.execute(
            select(func.count()).select_from(ProviderCall).where(
                ProviderCall.workspace_id == workspace_id,
                ProviderCall.created_at >= t_from,
                ProviderCall.created_at < t_to,
            )
        )
    ).scalar() or 0

    distinct_models = (
        await db.execute(
            select(func.count(func.distinct(ProviderCall.model))).where(
                ProviderCall.workspace_id == workspace_id,
                ProviderCall.created_at >= t_from,
                ProviderCall.created_at < t_to,
            )
        )
    ).scalar() or 0

    return BillingOrgScopePosture(
        workspace_id=workspace_id,
        period_days=30,
        billing_context={
            "total_periods": len(billing_periods),
            "open_periods": open_periods,
            "closed_periods": closed_periods,
            "total_billed_usd": total_billed_usd,
        },
        org_context={
            "workspace_users": workspace_users,
            "access_groups": access_groups,
            "api_keys": api_keys,
        },
        attribution_context={
            "calls_30d": calls_30d,
            "distinct_models": distinct_models,
            "avg_cost_per_call": round(spend_30d / calls_30d, 6) if calls_30d else 0,
        },
        spend_context={
            "total_spend_30d": spend_30d,
            "distinct_models_30d": distinct_models,
        },
    )


@router.get("/finops-internal-posture", response_model=FinOpsInternalPosture)
async def finops_internal_posture(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    workspace_id = str(workspace.id)
    t_to = datetime.utcnow()
    t_from = t_to - timedelta(days=30)

    budgets = (
        await db.execute(
            select(Budget).where(Budget.workspace_id == workspace_id)
        )
    ).scalars().all()

    active_budgets = sum(1 for b in budgets if b.is_active)
    total_limit_usd = sum(float(b.limit_usd or 0) for b in budgets)
    breached = sum(1 for b in budgets if getattr(b, "breach_count", 0) > 0)

    billing_periods = (
        await db.execute(
            select(BillingPeriod).where(BillingPeriod.workspace_id == workspace_id)
        )
    ).scalars().all()

    open_periods = sum(1 for bp in billing_periods if bp.status == "open")
    total_billed_usd = sum(float(bp.total_cost_usd or 0) for bp in billing_periods)

    chargeback_rules = (
        await db.execute(
            select(func.count()).select_from(ChargebackRule).where(
                ChargebackRule.workspace_id == workspace_id
            )
        )
    ).scalar() or 0

    active_chargeback = (
        await db.execute(
            select(func.count()).select_from(ChargebackRule).where(
                ChargebackRule.workspace_id == workspace_id,
                ChargebackRule.status == "active",
            )
        )
    ).scalar() or 0

    ledger_snapshots = (
        await db.execute(
            select(func.count()).select_from(LedgerSnapshot).where(
                LedgerSnapshot.workspace_id == workspace_id
            )
        )
    ).scalar() or 0

    latest_snapshot = (
        await db.execute(
            select(LedgerSnapshot.snapshot_date).where(
                LedgerSnapshot.workspace_id == workspace_id
            ).order_by(LedgerSnapshot.snapshot_date.desc()).limit(1)
        )
    ).scalar()

    budget_ids = [b.id for b in budgets]

    total_overrides = 0
    active_overrides = 0
    if budget_ids:
        total_overrides = (
            await db.execute(
                select(func.count()).select_from(BudgetOverride).where(
                    BudgetOverride.budget_id.in_(budget_ids)
                )
            )
        ).scalar() or 0

        active_overrides = (
            await db.execute(
                select(func.count()).select_from(BudgetOverride).where(
                    BudgetOverride.budget_id.in_(budget_ids),
                    BudgetOverride.status == "active",
                )
            )
        ).scalar() or 0

    total_notifications = 0
    if budget_ids:
        total_notifications = (
            await db.execute(
                select(func.count()).select_from(BudgetNotification).where(
                    BudgetNotification.budget_id.in_(budget_ids)
                )
            )
        ).scalar() or 0

    spend_30d = float(
        (
            await db.execute(
                select(func.coalesce(func.sum(ProviderCall.cost_usd), 0)).where(
                    ProviderCall.workspace_id == workspace_id,
                    ProviderCall.created_at >= t_from,
                    ProviderCall.created_at < t_to,
                )
            )
        ).scalar() or 0
    )

    return FinOpsInternalPosture(
        workspace_id=workspace_id,
        period_days=30,
        budget_context={
            "total_budgets": len(budgets),
            "active_budgets": active_budgets,
            "total_limit_usd": total_limit_usd,
            "breached_budgets": breached,
        },
        billing_context={
            "total_periods": len(billing_periods),
            "open_periods": open_periods,
            "total_billed_usd": total_billed_usd,
        },
        chargeback_context={
            "total_rules": chargeback_rules,
            "active_rules": active_chargeback,
        },
        ledger_context={
            "total_snapshots": ledger_snapshots,
            "latest_snapshot_date": int(latest_snapshot.timestamp()) if latest_snapshot else 0,
        },
        override_context={
            "total_overrides": total_overrides,
            "active_overrides": active_overrides,
        },
        notification_context={
            "total_notifications": total_notifications,
            "spend_30d": spend_30d,
        },
    )


@router.get("/budget-control-observe-posture", response_model=BudgetControlObservePosture)
async def budget_control_observe_posture(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    ws = workspace.id
    t_to = datetime.utcnow()
    t_from = t_to - timedelta(days=30)

    budgets = (
        await db.execute(
            select(Budget).where(Budget.workspace_id == ws)
        )
    ).scalars().all()

    active_budgets = sum(1 for b in budgets if b.is_active)
    total_limit_usd = sum(float(b.limit_usd or 0) for b in budgets)
    breached = sum(1 for b in budgets if getattr(b, "breach_count", 0) > 0)
    at_risk = sum(
        1 for b in budgets
        if b.is_active and float(getattr(b, "pct_used", 0) or 0) >= 80
        and float(getattr(b, "pct_used", 0) or 0) < 100
    )
    avg_utilization = (
        sum(float(getattr(b, "pct_used", 0) or 0) for b in budgets) / len(budgets)
        if budgets else 0
    )

    budget_ids = [b.id for b in budgets]

    total_overrides = 0
    active_overrides = 0
    if budget_ids:
        total_overrides = (
            await db.execute(
                select(func.count()).select_from(BudgetOverride).where(
                    BudgetOverride.budget_id.in_(budget_ids)
                )
            )
        ).scalar() or 0
        active_overrides = (
            await db.execute(
                select(func.count()).select_from(BudgetOverride).where(
                    BudgetOverride.budget_id.in_(budget_ids),
                    BudgetOverride.status == "active",
                )
            )
        ).scalar() or 0

    total_notifications = 0
    if budget_ids:
        total_notifications = (
            await db.execute(
                select(func.count()).select_from(BudgetNotification).where(
                    BudgetNotification.budget_id.in_(budget_ids)
                )
            )
        ).scalar() or 0

    spend_30d = float(
        (
            await db.execute(
                select(func.coalesce(func.sum(ProviderCall.cost_usd), 0)).where(
                    ProviderCall.workspace_id == ws,
                    ProviderCall.created_at >= t_from,
                    ProviderCall.created_at < t_to,
                )
            )
        ).scalar() or 0
    )

    calls_30d = (
        await db.execute(
            select(func.count()).select_from(ProviderCall).where(
                ProviderCall.workspace_id == ws,
                ProviderCall.created_at >= t_from,
                ProviderCall.created_at < t_to,
            )
        )
    ).scalar() or 0

    return BudgetControlObservePosture(
        workspace_id=str(ws),
        period_days=30,
        budget_policy={
            "total_budgets": len(budgets),
            "active_budgets": active_budgets,
            "breached_budgets": breached,
            "at_risk_budgets": at_risk,
            "avg_utilization_pct": round(avg_utilization, 1),
            "total_limit_usd": total_limit_usd,
        },
        override_status={
            "total_overrides": total_overrides,
            "active_overrides": active_overrides,
        },
        notification_summary={
            "total_notifications": total_notifications,
            "calls_30d": calls_30d,
        },
        spend_context={
            "total_spend_30d": spend_30d,
        },
    )


@router.get("/budget-control-build-posture", response_model=BudgetControlBuildPosture)
async def budget_control_build_posture(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    workspace_id = str(workspace.id)
    t_to = datetime.utcnow()
    t_from = t_to - timedelta(days=30)

    budgets = (
        await db.execute(
            select(Budget).where(Budget.workspace_id == workspace_id)
        )
    ).scalars().all()

    active_budgets = sum(1 for b in budgets if b.is_active)
    total_limit_usd = sum(float(b.limit_usd or 0) for b in budgets)
    breached = sum(1 for b in budgets if getattr(b, "breach_count", 0) > 0)
    avg_utilization = (
        sum(float(getattr(b, "pct_used", 0) or 0) for b in budgets) / len(budgets)
        if budgets else 0
    )

    scope_types: dict[str, int] = {}
    for b in budgets:
        st = getattr(b, "scope_type", "workspace") or "workspace"
        scope_types[st] = scope_types.get(st, 0) + 1

    budget_ids = [b.id for b in budgets]

    total_overrides = 0
    active_overrides = 0
    if budget_ids:
        total_overrides = (
            await db.execute(
                select(func.count()).select_from(BudgetOverride).where(
                    BudgetOverride.budget_id.in_(budget_ids)
                )
            )
        ).scalar() or 0
        active_overrides = (
            await db.execute(
                select(func.count()).select_from(BudgetOverride).where(
                    BudgetOverride.budget_id.in_(budget_ids),
                    BudgetOverride.status == "active",
                )
            )
        ).scalar() or 0

    spend_30d = float(
        (
            await db.execute(
                select(func.coalesce(func.sum(ProviderCall.cost_usd), 0)).where(
                    ProviderCall.workspace_id == workspace_id,
                    ProviderCall.created_at >= t_from,
                    ProviderCall.created_at < t_to,
                )
            )
        ).scalar() or 0
    )

    distinct_models = (
        await db.execute(
            select(func.count(func.distinct(ProviderCall.model))).where(
                ProviderCall.workspace_id == workspace_id,
                ProviderCall.created_at >= t_from,
                ProviderCall.created_at < t_to,
            )
        )
    ).scalar() or 0

    return BudgetControlBuildPosture(
        workspace_id=workspace_id,
        period_days=30,
        budget_policy={
            "total_budgets": len(budgets),
            "active_budgets": active_budgets,
            "breached_budgets": breached,
            "avg_utilization_pct": round(avg_utilization, 1),
            "total_limit_usd": total_limit_usd,
        },
        override_context={
            "total_overrides": total_overrides,
            "active_overrides": active_overrides,
        },
        scope_context=scope_types,
        spend_context={
            "total_spend_30d": spend_30d,
            "distinct_models_30d": distinct_models,
        },
    )


@router.get("/billing-cross-feature-posture", response_model=BillingCrossFeaturePosture)
async def billing_cross_feature_posture(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    workspace_id = str(workspace.id)
    t_to = datetime.utcnow()
    t_from = t_to - timedelta(days=30)

    routes = (
        await db.execute(
            select(func.count()).select_from(GatewayRoute).where(
                GatewayRoute.workspace_id == workspace_id
            )
        )
    ).scalar() or 0

    providers = (
        await db.execute(
            select(func.count(func.distinct(ProviderCall.provider))).where(
                ProviderCall.workspace_id == workspace_id,
                ProviderCall.created_at >= t_from,
                ProviderCall.created_at < t_to,
            )
        )
    ).scalar() or 0

    cache_configs = (
        await db.execute(
            select(func.count()).select_from(ResponseCacheConfig).where(
                ResponseCacheConfig.workspace_id == workspace_id
            )
        )
    ).scalar() or 0

    rate_limit_endpoints = (
        await db.execute(
            select(func.count()).select_from(GatewayPassThroughEndpoint).where(
                GatewayPassThroughEndpoint.workspace_id == workspace_id
            )
        )
    ).scalar() or 0

    provider_spend = float(
        (
            await db.execute(
                select(func.coalesce(func.sum(ProviderCall.cost_usd), 0)).where(
                    ProviderCall.workspace_id == workspace_id,
                    ProviderCall.created_at >= t_from,
                    ProviderCall.created_at < t_to,
                )
            )
        ).scalar() or 0
    )

    distinct_models = (
        await db.execute(
            select(func.count(func.distinct(ProviderCall.model))).where(
                ProviderCall.workspace_id == workspace_id,
                ProviderCall.created_at >= t_from,
                ProviderCall.created_at < t_to,
            )
        )
    ).scalar() or 0

    tool_count = (
        await db.execute(
            select(func.count()).select_from(ToolRegistry).where(
                ToolRegistry.workspace_id == workspace_id
            )
        )
    ).scalar() or 0

    alert_rules = (
        await db.execute(
            select(func.count()).select_from(AlertRule).where(
                AlertRule.workspace_id == workspace_id
            )
        )
    ).scalar() or 0

    audit_events_30d = (
        await db.execute(
            select(func.count()).select_from(AuditEvent).where(
                AuditEvent.workspace_id == workspace_id,
                AuditEvent.created_at >= t_from,
                AuditEvent.created_at < t_to,
            )
        )
    ).scalar() or 0

    tags = (
        await db.execute(
            select(func.count()).select_from(Tag).where(
                Tag.workspace_id == workspace_id
            )
        )
    ).scalar() or 0

    total_orgs = (
        await db.execute(
            select(func.count()).select_from(Tenant)
        )
    ).scalar() or 0

    return BillingCrossFeaturePosture(
        workspace_id=workspace_id,
        period_days=30,
        gateway_context={
            "routes": routes,
            "active_providers_30d": providers,
            "cache_configs": cache_configs,
            "rate_limit_endpoints": rate_limit_endpoints,
            "distinct_models_30d": distinct_models,
        },
        safety_context={
            "tool_registry_count": tool_count,
            "alert_rules": alert_rules,
            "audit_events_30d": audit_events_30d,
            "tags": tags,
        },
        platform_context={
            "total_organizations": total_orgs,
        },
        spend_context={
            "total_spend_30d": provider_spend,
        },
    )


@router.get("/chargeback-cross-feature-posture", response_model=ChargebackCrossFeaturePosture)
async def chargeback_cross_feature_posture(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    workspace_id = str(workspace.id)
    t_to = datetime.utcnow()
    t_from = t_to - timedelta(days=30)

    workspace_users = (
        await db.execute(
            select(func.count()).select_from(WorkspaceUser).where(
                WorkspaceUser.workspace_id == workspace_id
            )
        )
    ).scalar() or 0

    access_groups = (
        await db.execute(
            select(func.count()).select_from(AccessGroup).where(
                AccessGroup.workspace_id == workspace_id
            )
        )
    ).scalar() or 0

    api_keys = (
        await db.execute(
            select(func.count()).select_from(ApiKey).where(
                ApiKey.workspace_id == workspace_id
            )
        )
    ).scalar() or 0

    otlp_batches_30d = (
        await db.execute(
            select(func.count()).select_from(OtlpIngestBatch).where(
                OtlpIngestBatch.workspace_id == workspace_id,
                OtlpIngestBatch.created_at >= t_from,
                OtlpIngestBatch.created_at < t_to,
            )
        )
    ).scalar() or 0

    hub_models = (
        await db.execute(
            select(func.count()).select_from(HubModel).where(
                HubModel.workspace_id == workspace_id
            )
        )
    ).scalar() or 0

    routes = (
        await db.execute(
            select(func.count()).select_from(GatewayRoute).where(
                GatewayRoute.workspace_id == workspace_id
            )
        )
    ).scalar() or 0

    providers = (
        await db.execute(
            select(func.count(func.distinct(ProviderCall.provider))).where(
                ProviderCall.workspace_id == workspace_id,
                ProviderCall.created_at >= t_from,
                ProviderCall.created_at < t_to,
            )
        )
    ).scalar() or 0

    cache_configs = (
        await db.execute(
            select(func.count()).select_from(ResponseCacheConfig).where(
                ResponseCacheConfig.workspace_id == workspace_id
            )
        )
    ).scalar() or 0

    mcp_servers = (
        await db.execute(
            select(func.count()).select_from(McpServer).where(
                McpServer.workspace_id == workspace_id
            )
        )
    ).scalar() or 0

    tool_count = (
        await db.execute(
            select(func.count()).select_from(ToolRegistry).where(
                ToolRegistry.workspace_id == workspace_id
            )
        )
    ).scalar() or 0

    audit_events_30d = (
        await db.execute(
            select(func.count()).select_from(AuditEvent).where(
                AuditEvent.workspace_id == workspace_id,
                AuditEvent.created_at >= t_from,
                AuditEvent.created_at < t_to,
            )
        )
    ).scalar() or 0

    tags = (
        await db.execute(
            select(func.count()).select_from(Tag).where(
                Tag.workspace_id == workspace_id
            )
        )
    ).scalar() or 0

    total_orgs = (
        await db.execute(
            select(func.count()).select_from(Tenant)
        )
    ).scalar() or 0

    provider_spend = float(
        (
            await db.execute(
                select(func.coalesce(func.sum(ProviderCall.cost_usd), 0)).where(
                    ProviderCall.workspace_id == workspace_id,
                    ProviderCall.created_at >= t_from,
                    ProviderCall.created_at < t_to,
                )
            )
        ).scalar() or 0
    )

    chargeback_rules = (
        await db.execute(
            select(func.count()).select_from(ChargebackRule).where(
                ChargebackRule.workspace_id == workspace_id
            )
        )
    ).scalar() or 0

    return ChargebackCrossFeaturePosture(
        workspace_id=workspace_id,
        period_days=30,
        org_context={
            "workspace_users": workspace_users,
            "access_groups": access_groups,
            "api_keys": api_keys,
            "otlp_batches_30d": otlp_batches_30d,
            "hub_models": hub_models,
        },
        gateway_context={
            "routes": routes,
            "active_providers_30d": providers,
            "cache_configs": cache_configs,
        },
        safety_context={
            "mcp_servers": mcp_servers,
            "tool_registry_count": tool_count,
            "audit_events_30d": audit_events_30d,
            "tags": tags,
        },
        platform_context={
            "total_organizations": total_orgs,
            "chargeback_rules": chargeback_rules,
        },
        spend_context={
            "total_spend_30d": provider_spend,
        },
    )


@router.get("/ledger-cross-feature-posture", response_model=LedgerCrossFeaturePosture)
async def ledger_cross_feature_posture(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    workspace_id = str(workspace.id)
    t_to = datetime.utcnow()
    t_from = t_to - timedelta(days=30)

    workspace_users = (
        await db.execute(
            select(func.count()).select_from(WorkspaceUser).where(
                WorkspaceUser.workspace_id == workspace_id
            )
        )
    ).scalar() or 0

    workspaces = (
        await db.execute(
            select(func.count()).select_from(Workspace)
        )
    ).scalar() or 0

    access_groups = (
        await db.execute(
            select(func.count()).select_from(AccessGroup).where(
                AccessGroup.workspace_id == workspace_id
            )
        )
    ).scalar() or 0

    billing_periods = (
        await db.execute(
            select(func.count()).select_from(BillingPeriod).where(
                BillingPeriod.workspace_id == workspace_id
            )
        )
    ).scalar() or 0

    provider_spend = float(
        (
            await db.execute(
                select(func.coalesce(func.sum(ProviderCall.cost_usd), 0)).where(
                    ProviderCall.workspace_id == workspace_id,
                    ProviderCall.created_at >= t_from,
                    ProviderCall.created_at < t_to,
                )
            )
        ).scalar() or 0
    )

    distinct_models = (
        await db.execute(
            select(func.count(func.distinct(ProviderCall.model))).where(
                ProviderCall.workspace_id == workspace_id,
                ProviderCall.created_at >= t_from,
                ProviderCall.created_at < t_to,
            )
        )
    ).scalar() or 0

    audit_events_30d = (
        await db.execute(
            select(func.count()).select_from(AuditEvent).where(
                AuditEvent.workspace_id == workspace_id,
                AuditEvent.created_at >= t_from,
                AuditEvent.created_at < t_to,
            )
        )
    ).scalar() or 0

    tags = (
        await db.execute(
            select(func.count()).select_from(Tag).where(
                Tag.workspace_id == workspace_id
            )
        )
    ).scalar() or 0

    total_orgs = (
        await db.execute(
            select(func.count()).select_from(Tenant)
        )
    ).scalar() or 0

    snapshots = (
        await db.execute(
            select(func.count()).select_from(LedgerSnapshot).where(
                LedgerSnapshot.workspace_id == workspace_id
            )
        )
    ).scalar() or 0

    latest_snapshot_row = (
        await db.execute(
            select(LedgerSnapshot.snapshot_date).where(
                LedgerSnapshot.workspace_id == workspace_id
            ).order_by(LedgerSnapshot.snapshot_date.desc()).limit(1)
        )
    ).scalar()
    latest_snapshot_date = int(latest_snapshot_row.timestamp()) if latest_snapshot_row else 0

    return LedgerCrossFeaturePosture(
        workspace_id=workspace_id,
        period_days=30,
        org_context={
            "workspace_users": workspace_users,
            "workspaces": workspaces,
            "access_groups": access_groups,
        },
        observe_context={
            "billing_periods": billing_periods,
            "total_spend_30d": provider_spend,
            "distinct_models_30d": distinct_models,
        },
        safety_context={
            "audit_events_30d": audit_events_30d,
            "tags": tags,
        },
        platform_context={
            "total_organizations": total_orgs,
        },
        ledger_context={
            "total_snapshots": snapshots,
            "latest_snapshot_date": latest_snapshot_date,
        },
    )


@router.get("/budget-scope-governance-posture", response_model=BudgetScopeGovernancePosture)
async def budget_scope_governance_posture(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    workspace_id = str(workspace.id)
    t_to = datetime.utcnow()
    t_from = t_to - timedelta(days=30)

    workspace_users = (
        await db.execute(
            select(func.count()).select_from(WorkspaceUser).where(
                WorkspaceUser.workspace_id == workspace_id
            )
        )
    ).scalar() or 0

    api_keys = (
        await db.execute(
            select(func.count()).select_from(ApiKey).where(
                ApiKey.workspace_id == workspace_id
            )
        )
    ).scalar() or 0

    access_groups = (
        await db.execute(
            select(func.count()).select_from(AccessGroup).where(
                AccessGroup.workspace_id == workspace_id
            )
        )
    ).scalar() or 0

    hub_models = (
        await db.execute(
            select(func.count()).select_from(HubModel).where(
                HubModel.workspace_id == workspace_id
            )
        )
    ).scalar() or 0

    routes = (
        await db.execute(
            select(func.count()).select_from(GatewayRoute).where(
                GatewayRoute.workspace_id == workspace_id
            )
        )
    ).scalar() or 0

    providers = (
        await db.execute(
            select(func.count(func.distinct(ProviderCall.provider))).where(
                ProviderCall.workspace_id == workspace_id,
                ProviderCall.created_at >= t_from,
                ProviderCall.created_at < t_to,
            )
        )
    ).scalar() or 0

    cache_configs = (
        await db.execute(
            select(func.count()).select_from(ResponseCacheConfig).where(
                ResponseCacheConfig.workspace_id == workspace_id
            )
        )
    ).scalar() or 0

    provider_spend = float(
        (
            await db.execute(
                select(func.coalesce(func.sum(ProviderCall.cost_usd), 0)).where(
                    ProviderCall.workspace_id == workspace_id,
                    ProviderCall.created_at >= t_from,
                    ProviderCall.created_at < t_to,
                )
            )
        ).scalar() or 0
    )

    alert_rules = (
        await db.execute(
            select(func.count()).select_from(AlertRule).where(
                AlertRule.workspace_id == workspace_id
            )
        )
    ).scalar() or 0

    audit_events_30d = (
        await db.execute(
            select(func.count()).select_from(AuditEvent).where(
                AuditEvent.workspace_id == workspace_id,
                AuditEvent.created_at >= t_from,
                AuditEvent.created_at < t_to,
            )
        )
    ).scalar() or 0

    tags = (
        await db.execute(
            select(func.count()).select_from(Tag).where(
                Tag.workspace_id == workspace_id
            )
        )
    ).scalar() or 0

    return BudgetScopeGovernancePosture(
        workspace_id=workspace_id,
        period_days=30,
        identity_context={
            "workspace_users": workspace_users,
            "api_keys": api_keys,
            "access_groups": access_groups,
            "hub_models": hub_models,
        },
        runtime_context={
            "routes": routes,
            "active_providers_30d": providers,
            "cache_configs": cache_configs,
            "total_spend_30d": provider_spend,
        },
        governance_context={
            "alert_rules": alert_rules,
            "audit_events_30d": audit_events_30d,
            "tags": tags,
        },
        spend_context={
            "total_spend_30d": provider_spend,
        },
    )


@router.get(
    "/budget-detail-drillback-posture",
    response_model=BudgetDetailDrillbackPosture,
)
async def budget_detail_drillback_posture(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _user: TenantUser = Depends(get_current_user),
    _rl: None = Depends(analytics_rate_limit),
):
    workspace_id = str(workspace.id)
    t_from = _default_from()
    t_to = _default_to()

    workspace_users = (
        await db.execute(
            select(func.count(WorkspaceUser.id)).where(
                WorkspaceUser.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    access_groups = (
        await db.execute(
            select(func.count(AccessGroup.id)).where(
                AccessGroup.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    api_keys = (
        await db.execute(
            select(func.count(ApiKey.id)).where(
                ApiKey.workspace_id == workspace.id,
                ApiKey.revoked_at.is_(None),
            )
        )
    ).scalar() or 0

    cache_configs = (
        await db.execute(
            select(func.count(ResponseCacheConfig.id)).where(
                ResponseCacheConfig.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    rate_limited_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.per_user_rpm_limit.isnot(None),
                GatewayRoute.is_active.is_(True),
            )
        )
    ).scalar() or 0

    total_runs_30d = (
        await db.execute(
            select(func.count(AgentRun.id)).where(
                AgentRun.workspace_id == workspace.id,
                AgentRun.started_at >= t_from,
                AgentRun.started_at < t_to,
            )
        )
    ).scalar() or 0

    total_requests_30d = (
        await db.execute(
            select(func.count(ProviderCall.id)).where(
                ProviderCall.workspace_id == workspace.id,
                ProviderCall.created_at >= t_from,
                ProviderCall.created_at < t_to,
            )
        )
    ).scalar() or 0

    audit_events_30d = (
        await db.execute(
            select(func.count(AuditEvent.id)).where(
                AuditEvent.workspace_id == workspace.id,
                AuditEvent.created_at >= t_from,
                AuditEvent.created_at < t_to,
            )
        )
    ).scalar() or 0

    workflows = (
        await db.execute(
            select(func.count(WorkflowDefinition.id)).where(
                WorkflowDefinition.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    workflow_runs_30d = (
        await db.execute(
            select(func.count(WorkflowRun.id)).where(
                WorkflowRun.workspace_id == workspace.id,
                WorkflowRun.started_at >= t_from,
                WorkflowRun.started_at < t_to,
            )
        )
    ).scalar() or 0

    total_spend_30d = (
        await db.execute(
            select(func.coalesce(func.sum(ProviderCall.cost_usd), 0)).where(
                ProviderCall.workspace_id == workspace.id,
                ProviderCall.created_at >= t_from,
                ProviderCall.created_at < t_to,
            )
        )
    ).scalar() or 0

    distinct_models_30d = (
        await db.execute(
            select(func.count(func.distinct(ProviderCall.model))).where(
                ProviderCall.workspace_id == workspace.id,
                ProviderCall.created_at >= t_from,
                ProviderCall.created_at < t_to,
            )
        )
    ).scalar() or 0

    return BudgetDetailDrillbackPosture(
        workspace_id=workspace_id,
        period_days=30,
        scope_context={
            "workspace_users": workspace_users,
            "access_groups": access_groups,
            "api_keys": api_keys,
        },
        runtime_context={
            "cache_configs": cache_configs,
            "rate_limited_routes": rate_limited_routes,
        },
        evidence_context={
            "runs_30d": total_runs_30d,
            "requests_30d": total_requests_30d,
            "audit_events_30d": audit_events_30d,
        },
        workflow_context={
            "workflows": workflows,
            "workflow_runs_30d": workflow_runs_30d,
        },
        spend_context={
            "total_spend_30d": float(total_spend_30d),
            "distinct_models_30d": distinct_models_30d,
        },
    )


@router.get(
    "/budget-override-exception-posture",
    response_model=BudgetOverrideExceptionPosture,
)
async def budget_override_exception_posture(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _user: TenantUser = Depends(get_current_user),
    _rl: None = Depends(analytics_rate_limit),
):
    workspace_id = str(workspace.id)
    t_from = _default_from()
    t_to = _default_to()

    ws_budgets = select(Budget.id).where(Budget.workspace_id == workspace.id).scalar_subquery()

    total_overrides = (
        await db.execute(
            select(func.count(BudgetOverride.id)).where(
                BudgetOverride.budget_id.in_(
                    select(Budget.id).where(Budget.workspace_id == workspace.id)
                )
            )
        )
    ).scalar() or 0

    active_overrides = (
        await db.execute(
            select(func.count(BudgetOverride.id)).where(
                BudgetOverride.budget_id.in_(
                    select(Budget.id).where(Budget.workspace_id == workspace.id)
                ),
                BudgetOverride.status == "active",
            )
        )
    ).scalar() or 0

    expired_overrides = (
        await db.execute(
            select(func.count(BudgetOverride.id)).where(
                BudgetOverride.budget_id.in_(
                    select(Budget.id).where(Budget.workspace_id == workspace.id)
                ),
                BudgetOverride.is_active.is_(False),
            )
        )
    ).scalar() or 0

    override_limit_total = (
        await db.execute(
            select(func.coalesce(func.sum(BudgetOverride.override_limit_usd), 0)).where(
                BudgetOverride.budget_id.in_(
                    select(Budget.id).where(Budget.workspace_id == workspace.id)
                ),
                BudgetOverride.status == "active",
            )
        )
    ).scalar() or 0

    pending_approvals = (
        await db.execute(
            select(func.count(Approval.id)).where(
                Approval.workspace_id == workspace.id,
                Approval.status == "pending",
            )
        )
    ).scalar() or 0

    approved_30d = (
        await db.execute(
            select(func.count(Approval.id)).where(
                Approval.workspace_id == workspace.id,
                Approval.status == "approved",
                Approval.created_at >= t_from,
                Approval.created_at < t_to,
            )
        )
    ).scalar() or 0

    denied_30d = (
        await db.execute(
            select(func.count(Approval.id)).where(
                Approval.workspace_id == workspace.id,
                Approval.status == "denied",
                Approval.created_at >= t_from,
                Approval.created_at < t_to,
            )
        )
    ).scalar() or 0

    routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
            )
        )
    ).scalar() or 0

    rate_limited_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.per_user_rpm_limit.isnot(None),
                GatewayRoute.is_active.is_(True),
            )
        )
    ).scalar() or 0

    alert_rules = (
        await db.execute(
            select(func.count(AlertRule.id)).where(
                AlertRule.workspace_id == workspace.id,
                AlertRule.is_active.is_(True),
            )
        )
    ).scalar() or 0

    audit_events_30d = (
        await db.execute(
            select(func.count(AuditEvent.id)).where(
                AuditEvent.workspace_id == workspace.id,
                AuditEvent.created_at >= t_from,
                AuditEvent.created_at < t_to,
            )
        )
    ).scalar() or 0

    total_spend_30d = (
        await db.execute(
            select(func.coalesce(func.sum(ProviderCall.cost_usd), 0)).where(
                ProviderCall.workspace_id == workspace.id,
                ProviderCall.created_at >= t_from,
                ProviderCall.created_at < t_to,
            )
        )
    ).scalar() or 0

    return BudgetOverrideExceptionPosture(
        workspace_id=workspace_id,
        period_days=30,
        override_context={
            "total_overrides": total_overrides,
            "active_overrides": active_overrides,
            "expired_overrides": expired_overrides,
            "active_override_limit_usd": float(override_limit_total),
        },
        approval_context={
            "pending_approvals": pending_approvals,
            "approved_30d": approved_30d,
            "denied_30d": denied_30d,
        },
        runtime_context={
            "active_routes": routes,
            "rate_limited_routes": rate_limited_routes,
        },
        monitoring_context={
            "alert_rules": alert_rules,
            "audit_events_30d": audit_events_30d,
        },
        spend_context={
            "total_spend_30d": float(total_spend_30d),
        },
    )


@router.get(
    "/billing-reconciliation-posture",
    response_model=BillingReconciliationPosture,
)
async def billing_reconciliation_posture(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _user: TenantUser = Depends(get_current_user),
    _rl: None = Depends(analytics_rate_limit),
):
    workspace_id = str(workspace.id)
    t_from = _default_from()
    t_to = _default_to()

    workspace_users = (
        await db.execute(
            select(func.count(WorkspaceUser.id)).where(
                WorkspaceUser.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    api_keys = (
        await db.execute(
            select(func.count(ApiKey.id)).where(
                ApiKey.workspace_id == workspace.id,
                ApiKey.revoked_at.is_(None),
            )
        )
    ).scalar() or 0

    access_groups = (
        await db.execute(
            select(func.count(AccessGroup.id)).where(
                AccessGroup.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    active_providers = (
        await db.execute(
            select(func.count(func.distinct(ProviderCall.provider))).where(
                ProviderCall.workspace_id == workspace.id,
                ProviderCall.created_at >= t_from,
                ProviderCall.created_at < t_to,
            )
        )
    ).scalar() or 0

    cache_configs = (
        await db.execute(
            select(func.count(ResponseCacheConfig.id)).where(
                ResponseCacheConfig.workspace_id == workspace.id,
                ResponseCacheConfig.is_enabled.is_(True),
            )
        )
    ).scalar() or 0

    cache_hit_savings = (
        await db.execute(
            select(func.coalesce(func.sum(ProviderCall.cost_usd), 0)).where(
                ProviderCall.workspace_id == workspace.id,
                ProviderCall.cached_input_tokens > 0,
                ProviderCall.created_at >= t_from,
                ProviderCall.created_at < t_to,
            )
        )
    ).scalar() or 0

    distinct_models = (
        await db.execute(
            select(func.count(func.distinct(ProviderCall.model))).where(
                ProviderCall.workspace_id == workspace.id,
                ProviderCall.created_at >= t_from,
                ProviderCall.created_at < t_to,
            )
        )
    ).scalar() or 0

    alert_rules = (
        await db.execute(
            select(func.count(AlertRule.id)).where(
                AlertRule.workspace_id == workspace.id,
                AlertRule.is_active.is_(True),
            )
        )
    ).scalar() or 0

    audit_events_30d = (
        await db.execute(
            select(func.count(AuditEvent.id)).where(
                AuditEvent.workspace_id == workspace.id,
                AuditEvent.created_at >= t_from,
                AuditEvent.created_at < t_to,
            )
        )
    ).scalar() or 0

    billing_periods = (
        await db.execute(
            select(func.count(BillingPeriod.id)).where(
                BillingPeriod.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    total_spend_30d = (
        await db.execute(
            select(func.coalesce(func.sum(ProviderCall.cost_usd), 0)).where(
                ProviderCall.workspace_id == workspace.id,
                ProviderCall.created_at >= t_from,
                ProviderCall.created_at < t_to,
            )
        )
    ).scalar() or 0

    return BillingReconciliationPosture(
        workspace_id=workspace_id,
        period_days=30,
        identity_context={
            "workspace_users": workspace_users,
            "api_keys": api_keys,
            "access_groups": access_groups,
        },
        provider_context={
            "active_providers_30d": active_providers,
            "cache_configs": cache_configs,
            "cache_hit_savings_usd": float(cache_hit_savings),
            "distinct_models_30d": distinct_models,
        },
        optimization_context={
            "billing_periods": billing_periods,
            "alert_rules": alert_rules,
            "cache_savings_usd": float(cache_hit_savings),
        },
        evidence_context={
            "audit_events_30d": audit_events_30d,
            "alert_rules": alert_rules,
        },
        spend_context={
            "total_spend_30d": float(total_spend_30d),
        },
    )


@router.get(
    "/billing-detail-evidence-posture",
    response_model=BillingDetailEvidencePosture,
)
async def billing_detail_evidence_posture(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _user: TenantUser = Depends(get_current_user),
    _rl: None = Depends(analytics_rate_limit),
):
    workspace_id = str(workspace.id)
    t_from = _default_from()
    t_to = _default_to()

    workspace_users = (
        await db.execute(
            select(func.count(WorkspaceUser.id)).where(
                WorkspaceUser.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    api_keys = (
        await db.execute(
            select(func.count(ApiKey.id)).where(
                ApiKey.workspace_id == workspace.id,
                ApiKey.revoked_at.is_(None),
            )
        )
    ).scalar() or 0

    access_groups = (
        await db.execute(
            select(func.count(AccessGroup.id)).where(
                AccessGroup.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
            )
        )
    ).scalar() or 0

    distinct_models = (
        await db.execute(
            select(func.count(func.distinct(ProviderCall.model))).where(
                ProviderCall.workspace_id == workspace.id,
                ProviderCall.created_at >= t_from,
                ProviderCall.created_at < t_to,
            )
        )
    ).scalar() or 0

    sessions_30d = (
        await db.execute(
            select(func.count(func.distinct(Span.session_id))).where(
                Span.workspace_id == workspace.id,
                Span.session_id.isnot(None),
                Span.created_at >= t_from,
                Span.created_at < t_to,
            )
        )
    ).scalar() or 0

    requests_30d = (
        await db.execute(
            select(func.count(ProviderCall.id)).where(
                ProviderCall.workspace_id == workspace.id,
                ProviderCall.created_at >= t_from,
                ProviderCall.created_at < t_to,
            )
        )
    ).scalar() or 0

    replay_experiments = (
        await db.execute(
            select(func.count(ReplayExperiment.id)).where(
                ReplayExperiment.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    total_spend_30d = (
        await db.execute(
            select(func.coalesce(func.sum(ProviderCall.cost_usd), 0)).where(
                ProviderCall.workspace_id == workspace.id,
                ProviderCall.created_at >= t_from,
                ProviderCall.created_at < t_to,
            )
        )
    ).scalar() or 0

    return BillingDetailEvidencePosture(
        workspace_id=workspace_id,
        period_days=30,
        identity_context={
            "workspace_users": workspace_users,
            "api_keys": api_keys,
            "access_groups": access_groups,
        },
        gateway_context={
            "active_routes": routes,
            "distinct_models_30d": distinct_models,
        },
        observe_context={
            "sessions_30d": sessions_30d,
            "requests_30d": requests_30d,
        },
        build_context={
            "replay_experiments": replay_experiments,
        },
        spend_context={
            "total_spend_30d": float(total_spend_30d),
        },
    )


@router.get(
    "/chargeback-attribution-posture",
    response_model=ChargebackAttributionPosture,
)
async def chargeback_attribution_posture(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _user: TenantUser = Depends(get_current_user),
    _rl: None = Depends(analytics_rate_limit),
):
    workspace_id = str(workspace.id)
    t_from = _default_from()
    t_to = _default_to()

    workspace_users = (
        await db.execute(
            select(func.count(WorkspaceUser.id)).where(
                WorkspaceUser.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    api_keys = (
        await db.execute(
            select(func.count(ApiKey.id)).where(
                ApiKey.workspace_id == workspace.id,
                ApiKey.revoked_at.is_(None),
            )
        )
    ).scalar() or 0

    access_groups = (
        await db.execute(
            select(func.count(AccessGroup.id)).where(
                AccessGroup.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    cache_configs = (
        await db.execute(
            select(func.count(ResponseCacheConfig.id)).where(
                ResponseCacheConfig.workspace_id == workspace.id,
                ResponseCacheConfig.is_enabled.is_(True),
            )
        )
    ).scalar() or 0

    cache_hit_savings = (
        await db.execute(
            select(func.coalesce(func.sum(ProviderCall.cost_usd), 0)).where(
                ProviderCall.workspace_id == workspace.id,
                ProviderCall.cached_input_tokens > 0,
                ProviderCall.created_at >= t_from,
                ProviderCall.created_at < t_to,
            )
        )
    ).scalar() or 0

    alert_rules = (
        await db.execute(
            select(func.count(AlertRule.id)).where(
                AlertRule.workspace_id == workspace.id,
                AlertRule.is_active.is_(True),
            )
        )
    ).scalar() or 0

    audit_events_30d = (
        await db.execute(
            select(func.count(AuditEvent.id)).where(
                AuditEvent.workspace_id == workspace.id,
                AuditEvent.created_at >= t_from,
                AuditEvent.created_at < t_to,
            )
        )
    ).scalar() or 0

    tags = (
        await db.execute(
            select(func.count(Tag.id)).where(
                Tag.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    chargeback_rules = (
        await db.execute(
            select(func.count(ChargebackRule.id)).where(
                ChargebackRule.workspace_id == workspace.id,
                ChargebackRule.status == "active",
            )
        )
    ).scalar() or 0

    total_spend_30d = (
        await db.execute(
            select(func.coalesce(func.sum(ProviderCall.cost_usd), 0)).where(
                ProviderCall.workspace_id == workspace.id,
                ProviderCall.created_at >= t_from,
                ProviderCall.created_at < t_to,
            )
        )
    ).scalar() or 0

    return ChargebackAttributionPosture(
        workspace_id=workspace_id,
        period_days=30,
        identity_context={
            "workspace_users": workspace_users,
            "api_keys": api_keys,
            "access_groups": access_groups,
        },
        runtime_context={
            "cache_configs": cache_configs,
            "cache_hit_savings_usd": float(cache_hit_savings),
            "chargeback_rules": chargeback_rules,
        },
        monitoring_context={
            "alert_rules": alert_rules,
            "audit_events_30d": audit_events_30d,
            "tags": tags,
        },
        optimization_context={
            "chargeback_rules": chargeback_rules,
            "cache_savings_usd": float(cache_hit_savings),
        },
        spend_context={
            "total_spend_30d": float(total_spend_30d),
        },
    )


@router.get("/playground-org-gateway-posture")
async def playground_org_gateway_posture(
    request: Request,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    workspace_id = str(workspace.id)
    since = datetime.now(UTC) - timedelta(days=30)

    workspace_users = (
        await db.execute(
            select(func.count(WorkspaceUser.id)).where(
                WorkspaceUser.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    api_keys = (
        await db.execute(
            select(func.count(ApiKey.id)).where(ApiKey.workspace_id == workspace.id)
        )
    ).scalar() or 0

    active_api_key_row = await db.execute(
        select(ApiKey.name, ApiKey.key_prefix).where(
            ApiKey.workspace_id == workspace.id
        ).limit(1)
    )
    active_key = active_api_key_row.first()
    api_key_name = active_key.name if active_key else ""
    api_key_prefix = active_key.key_prefix if active_key else ""

    hub_models = (
        await db.execute(
            select(func.count(HubModel.id)).where(HubModel.workspace_id == workspace.id)
        )
    ).scalar() or 0

    hub_active = (
        await db.execute(
            select(func.count(HubModel.id)).where(
                HubModel.workspace_id == workspace.id,
                HubModel.is_active.is_(True),
            )
        )
    ).scalar() or 0

    distinct_providers_row = await db.execute(
        select(func.count(func.distinct(GatewayRoute.provider))).where(
            GatewayRoute.workspace_id == workspace.id,
            GatewayRoute.is_active.is_(True),
        )
    )
    distinct_providers = distinct_providers_row.scalar() or 0

    active_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
            )
        )
    ).scalar() or 0

    guardrail_rules = (
        await db.execute(
            select(func.count(GuardrailRule.id)).where(
                GuardrailRule.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    active_guardrails = (
        await db.execute(
            select(func.count(GuardrailRule.id)).where(
                GuardrailRule.workspace_id == workspace.id,
                GuardrailRule.status == "active",
            )
        )
    ).scalar() or 0

    cache_configs = (
        await db.execute(
            select(func.count(ResponseCacheConfig.id)).where(
                ResponseCacheConfig.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    cache_enabled = (
        await db.execute(
            select(func.count(ResponseCacheConfig.id)).where(
                ResponseCacheConfig.workspace_id == workspace.id,
                ResponseCacheConfig.is_enabled.is_(True),
            )
        )
    ).scalar() or 0

    cache_hit_savings = (
        await db.execute(
            select(func.coalesce(func.sum(ProviderCall.cost_usd), 0)).where(
                ProviderCall.workspace_id == workspace.id,
                ProviderCall.created_at >= since,
                ProviderCall.cache_hit.is_(True),
            )
        )
    ).scalar() or 0

    rate_limited_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
                GatewayRoute.rpm_limit.isnot(None),
            )
        )
    ).scalar() or 0

    passthrough_count = (
        await db.execute(
            select(func.count(GatewayPassThroughEndpoint.id)).where(
                GatewayPassThroughEndpoint.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    return PlaygroundOrgGatewayPosture(
        workspace_id=workspace_id,
        period_days=30,
        workspace_context={
            "workspace_name": workspace.name,
            "workspace_users": workspace_users,
        },
        api_key_context={
            "total_api_keys": api_keys,
            "active_key_name": api_key_name,
            "active_key_prefix": api_key_prefix,
        },
        ai_hub_context={
            "hub_models": hub_models,
            "hub_active_models": hub_active,
        },
        provider_context={
            "distinct_providers": distinct_providers,
            "active_routes": active_routes,
        },
        guardrail_context={
            "guardrail_rules": guardrail_rules,
            "active_guardrails": active_guardrails,
        },
        cache_context={
            "cache_configs": cache_configs,
            "cache_enabled": cache_enabled,
            "cache_savings_30d": float(cache_hit_savings),
        },
        rate_limit_context={
            "rate_limited_routes": rate_limited_routes,
            "passthrough_endpoints": passthrough_count,
        },
    )


@router.get("/prompts-org-gateway-posture")
async def prompts_org_gateway_posture(
    request: Request,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    workspace_id = str(workspace.id)

    workspace_users = (
        await db.execute(
            select(func.count(WorkspaceUser.id)).where(
                WorkspaceUser.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    hub_models = (
        await db.execute(
            select(func.count(HubModel.id)).where(HubModel.workspace_id == workspace.id)
        )
    ).scalar() or 0

    hub_active = (
        await db.execute(
            select(func.count(HubModel.id)).where(
                HubModel.workspace_id == workspace.id,
                HubModel.is_active.is_(True),
            )
        )
    ).scalar() or 0

    distinct_providers_row = await db.execute(
        select(func.count(func.distinct(GatewayRoute.provider))).where(
            GatewayRoute.workspace_id == workspace.id,
            GatewayRoute.is_active.is_(True),
        )
    )
    distinct_providers = distinct_providers_row.scalar() or 0

    active_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
            )
        )
    ).scalar() or 0

    routing_policies = (
        await db.execute(
            select(func.count(RoutingPolicy.id)).where(
                RoutingPolicy.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    prompt_count = (
        await db.execute(
            select(func.count(Prompt.id)).where(Prompt.workspace_id == workspace.id)
        )
    ).scalar() or 0

    prompts_with_model_hint = (
        await db.execute(
            select(func.count(Prompt.id)).where(
                Prompt.workspace_id == workspace.id,
                Prompt.model_hint.isnot(None),
            )
        )
    ).scalar() or 0

    return PromptsOrgGatewayPosture(
        workspace_id=workspace_id,
        period_days=30,
        workspace_context={
            "workspace_name": workspace.name,
            "workspace_users": workspace_users,
        },
        ai_hub_context={
            "hub_models": hub_models,
            "hub_active_models": hub_active,
        },
        provider_context={
            "distinct_providers": distinct_providers,
            "active_routes": active_routes,
        },
        gateway_context={
            "routing_policies": routing_policies,
            "active_routes": active_routes,
        },
        prompt_model_context={
            "total_prompts": prompt_count,
            "prompts_with_model_hint": prompts_with_model_hint,
        },
    )


# ---------------------------------------------------------------------------
# WU-002: Playground Observe Posture
# ---------------------------------------------------------------------------


@router.get("/playground-observe-posture")
async def playground_observe_posture(
    user: TenantUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> PlaygroundObservePosture:
    workspace_id = str(workspace.id)
    cutoff = datetime.utcnow() - timedelta(days=30)

    runs_30d = (
        await db.execute(
            select(func.count(AgentRun.id)).where(
                AgentRun.workspace_id == workspace.id,
                AgentRun.started_at >= cutoff,
            )
        )
    ).scalar() or 0

    total_runs = (
        await db.execute(
            select(func.count(AgentRun.id)).where(AgentRun.workspace_id == workspace.id)
        )
    ).scalar() or 0

    provider_calls_30d = (
        await db.execute(
            select(func.count(ProviderCall.id)).where(
                ProviderCall.workspace_id == workspace.id,
                ProviderCall.created_at >= cutoff,
            )
        )
    ).scalar() or 0

    distinct_models_30d = (
        await db.execute(
            select(func.count(func.distinct(ProviderCall.model))).where(
                ProviderCall.workspace_id == workspace.id,
                ProviderCall.created_at >= cutoff,
            )
        )
    ).scalar() or 0

    total_cost_row = await db.execute(
        select(func.sum(ProviderCall.cost_usd)).where(
            ProviderCall.workspace_id == workspace.id,
            ProviderCall.created_at >= cutoff,
        )
    )
    total_cost_30d = float(total_cost_row.scalar() or 0)

    total_tokens_row = await db.execute(
        select(
            func.sum(ProviderCall.input_tokens),
            func.sum(ProviderCall.output_tokens),
        ).where(
            ProviderCall.workspace_id == workspace.id,
            ProviderCall.created_at >= cutoff,
        )
    )
    tokens_row = total_tokens_row.one()
    total_input_tokens = int(tokens_row[0] or 0)
    total_output_tokens = int(tokens_row[1] or 0)

    cache_configs = (
        await db.execute(
            select(func.count(ResponseCacheConfig.id)).where(
                ResponseCacheConfig.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    cache_enabled = (
        await db.execute(
            select(func.count(ResponseCacheConfig.id)).where(
                ResponseCacheConfig.workspace_id == workspace.id,
                ResponseCacheConfig.is_enabled.is_(True),
            )
        )
    ).scalar() or 0

    cache_savings = float(cache_configs * 0.12) if cache_enabled > 0 else 0.0

    return PlaygroundObservePosture(
        workspace_id=workspace_id,
        period_days=30,
        runs_context={
            "runs_30d": runs_30d,
            "total_runs": total_runs,
        },
        request_flow_context={
            "provider_calls_30d": provider_calls_30d,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
        },
        model_usage_context={
            "distinct_models_30d": distinct_models_30d,
            "provider_calls_30d": provider_calls_30d,
        },
        cost_savings_context={
            "total_cost_30d": total_cost_30d,
            "cache_configs": cache_configs,
            "estimated_savings": cache_savings,
        },
    )


# ---------------------------------------------------------------------------
# WU-002: Prompt Detail Observe Posture
# ---------------------------------------------------------------------------


@router.get("/prompt-detail-observe-posture")
async def prompt_detail_observe_posture(
    user: TenantUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    prompt_name: str | None = None,
) -> PromptDetailObservePosture:
    workspace_id = str(workspace.id)
    cutoff = datetime.utcnow() - timedelta(days=30)

    prompt_count = (
        await db.execute(
            select(func.count(Prompt.id)).where(Prompt.workspace_id == workspace.id)
        )
    ).scalar() or 0

    versions_count = 0
    resolved_name = prompt_name or ""
    if prompt_name:
        prompt_row = await db.execute(
            select(Prompt).where(
                Prompt.workspace_id == workspace.id,
                Prompt.name == prompt_name,
            )
        )
        prompt_obj = prompt_row.scalar_one_or_none()
        if prompt_obj:
            resolved_name = prompt_obj.name
            versions_count = prompt_obj.version

    runs_30d = (
        await db.execute(
            select(func.count(AgentRun.id)).where(
                AgentRun.workspace_id == workspace.id,
                AgentRun.started_at >= cutoff,
            )
        )
    ).scalar() or 0

    provider_calls_30d = (
        await db.execute(
            select(func.count(ProviderCall.id)).where(
                ProviderCall.workspace_id == workspace.id,
                ProviderCall.created_at >= cutoff,
            )
        )
    ).scalar() or 0

    distinct_models = (
        await db.execute(
            select(func.count(func.distinct(ProviderCall.model))).where(
                ProviderCall.workspace_id == workspace.id,
                ProviderCall.created_at >= cutoff,
            )
        )
    ).scalar() or 0

    total_cost_row = await db.execute(
        select(func.sum(ProviderCall.cost_usd)).where(
            ProviderCall.workspace_id == workspace.id,
            ProviderCall.created_at >= cutoff,
        )
    )
    total_cost_30d = float(total_cost_row.scalar() or 0)

    avg_cost_per_call = total_cost_30d / provider_calls_30d if provider_calls_30d > 0 else 0.0

    return PromptDetailObservePosture(
        workspace_id=workspace_id,
        period_days=30,
        prompt_name=resolved_name,
        analytics_context={
            "total_prompts": prompt_count,
            "prompt_versions": versions_count,
            "runs_30d": runs_30d,
        },
        model_usage_context={
            "distinct_models_30d": distinct_models,
            "provider_calls_30d": provider_calls_30d,
        },
        cost_context={
            "total_cost_30d": total_cost_30d,
            "avg_cost_per_call": round(avg_cost_per_call, 6),
        },
        request_context={
            "provider_calls_30d": provider_calls_30d,
            "runs_30d": runs_30d,
        },
    )


# ---------------------------------------------------------------------------
# WU-003: Workflow Detail Cross-Feature Posture
# ---------------------------------------------------------------------------


@router.get("/workflow-detail-cross-feature-posture")
async def workflow_detail_cross_feature_posture(
    user: TenantUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> WorkflowDetailCrossFeaturePosture:
    workspace_id = str(workspace.id)
    cutoff = datetime.utcnow() - timedelta(days=30)

    # Org context
    workspace_users = (
        await db.execute(
            select(func.count(WorkspaceUser.id)).where(
                WorkspaceUser.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    access_groups = (
        await db.execute(
            select(func.count(AccessGroup.id)).where(
                AccessGroup.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    api_keys = (
        await db.execute(
            select(func.count(ApiKey.id)).where(ApiKey.workspace_id == workspace.id)
        )
    ).scalar() or 0

    hub_models = (
        await db.execute(
            select(func.count(HubModel.id)).where(HubModel.workspace_id == workspace.id)
        )
    ).scalar() or 0

    # Gateway context
    distinct_providers = (
        await db.execute(
            select(func.count(func.distinct(GatewayRoute.provider))).where(
                GatewayRoute.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    active_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
            )
        )
    ).scalar() or 0

    guardrail_rules = (
        await db.execute(
            select(func.count(GuardrailRule.id)).where(
                GuardrailRule.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    cache_configs = (
        await db.execute(
            select(func.count(ResponseCacheConfig.id)).where(
                ResponseCacheConfig.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    rate_limited_routes = (
        await db.execute(
            select(func.count(GatewayPassThroughEndpoint.id)).where(
                GatewayPassThroughEndpoint.workspace_id == workspace.id,
                GatewayPassThroughEndpoint.rate_limit_rpm.isnot(None),
            )
        )
    ).scalar() or 0

    # Observe context
    runs_30d = (
        await db.execute(
            select(func.count(AgentRun.id)).where(
                AgentRun.workspace_id == workspace.id,
                AgentRun.started_at >= cutoff,
            )
        )
    ).scalar() or 0

    provider_calls_30d = (
        await db.execute(
            select(func.count(ProviderCall.id)).where(
                ProviderCall.workspace_id == workspace.id,
                ProviderCall.created_at >= cutoff,
            )
        )
    ).scalar() or 0

    distinct_models_30d = (
        await db.execute(
            select(func.count(func.distinct(ProviderCall.model))).where(
                ProviderCall.workspace_id == workspace.id,
                ProviderCall.created_at >= cutoff,
            )
        )
    ).scalar() or 0

    total_cost_row = await db.execute(
        select(func.sum(ProviderCall.cost_usd)).where(
            ProviderCall.workspace_id == workspace.id,
            ProviderCall.created_at >= cutoff,
        )
    )
    total_cost_30d = float(total_cost_row.scalar() or 0)

    # FinOps context
    active_budgets = (
        await db.execute(
            select(func.count(Budget.id)).where(
                Budget.workspace_id == workspace.id,
                Budget.is_active.is_(True),
            )
        )
    ).scalar() or 0

    billing_periods = (
        await db.execute(
            select(func.count(BillingPeriod.id)).where(
                BillingPeriod.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    budget_limit_row = await db.execute(
        select(func.sum(Budget.limit_usd)).where(
            Budget.workspace_id == workspace.id,
            Budget.is_active.is_(True),
        )
    )
    total_budget_limit = float(budget_limit_row.scalar() or 0)

    return WorkflowDetailCrossFeaturePosture(
        workspace_id=workspace_id,
        period_days=30,
        org_context={
            "workspace_name": workspace.name,
            "workspace_users": workspace_users,
            "access_groups": access_groups,
            "api_keys": api_keys,
            "hub_models": hub_models,
        },
        gateway_context={
            "distinct_providers": distinct_providers,
            "active_routes": active_routes,
            "guardrail_rules": guardrail_rules,
            "cache_configs": cache_configs,
            "rate_limited_routes": rate_limited_routes,
        },
        observe_context={
            "runs_30d": runs_30d,
            "provider_calls_30d": provider_calls_30d,
            "distinct_models_30d": distinct_models_30d,
            "total_cost_30d": total_cost_30d,
        },
        finops_context={
            "active_budgets": active_budgets,
            "billing_periods": billing_periods,
            "total_budget_limit": total_budget_limit,
            "total_spend_30d": total_cost_30d,
        },
    )


@router.get("/eval-replay-org-gateway-posture")
async def get_eval_replay_org_gateway_posture(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> EvalReplayOrgGatewayPosture:
    workspace_id = str(workspace.id)

    workspace_users = (
        await db.execute(
            select(func.count(WorkspaceUser.id)).where(
                WorkspaceUser.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    access_groups = (
        await db.execute(
            select(func.count(AccessGroup.id)).where(
                AccessGroup.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    api_keys = (
        await db.execute(
            select(func.count(ApiKey.id)).where(
                ApiKey.workspace_id == workspace.id,
                ApiKey.revoked_at.is_(None),
            )
        )
    ).scalar() or 0

    hub_models = (
        await db.execute(
            select(func.count(HubModel.id)).where(
                HubModel.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    hub_active_models = (
        await db.execute(
            select(func.count(HubModel.id)).where(
                HubModel.workspace_id == workspace.id,
                HubModel.is_active.is_(True),
            )
        )
    ).scalar() or 0

    distinct_providers = (
        await db.execute(
            select(func.count(func.distinct(GatewayRoute.provider))).where(
                GatewayRoute.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    active_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
            )
        )
    ).scalar() or 0

    guardrail_rules = (
        await db.execute(
            select(func.count(GuardrailRule.id)).where(
                GuardrailRule.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    cache_configs = (
        await db.execute(
            select(func.count(ResponseCacheConfig.id)).where(
                ResponseCacheConfig.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    routing_policies = (
        await db.execute(
            select(func.count(RoutingPolicy.id)).where(
                RoutingPolicy.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    return EvalReplayOrgGatewayPosture(
        workspace_id=workspace_id,
        period_days=30,
        workspace_context={
            "workspace_name": workspace.name,
            "workspace_users": workspace_users,
        },
        access_group_context={
            "access_groups": access_groups,
        },
        api_key_context={
            "api_keys": api_keys,
        },
        ai_hub_context={
            "hub_models": hub_models,
            "hub_active_models": hub_active_models,
        },
        provider_context={
            "distinct_providers": distinct_providers,
            "active_routes": active_routes,
        },
        gateway_context={
            "guardrail_rules": guardrail_rules,
            "cache_configs": cache_configs,
            "routing_policies": routing_policies,
        },
        guardrail_context={
            "guardrail_rules": guardrail_rules,
        },
    )


@router.get("/eval-replay-observe-posture")
async def get_eval_replay_observe_posture(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> EvalReplayObservePosture:
    workspace_id = str(workspace.id)
    cutoff = datetime.now(UTC) - timedelta(days=30)

    runs_30d = (
        await db.execute(
            select(func.count(AgentRun.id)).where(
                AgentRun.workspace_id == workspace.id,
                AgentRun.started_at >= cutoff,
            )
        )
    ).scalar() or 0

    total_runs = (
        await db.execute(
            select(func.count(AgentRun.id)).where(
                AgentRun.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    provider_calls_30d = (
        await db.execute(
            select(func.count(ProviderCall.id)).where(
                ProviderCall.workspace_id == workspace.id,
                ProviderCall.created_at >= cutoff,
            )
        )
    ).scalar() or 0

    token_row = await db.execute(
        select(
            func.sum(ProviderCall.input_tokens),
            func.sum(ProviderCall.output_tokens),
        ).where(
            ProviderCall.workspace_id == workspace.id,
            ProviderCall.created_at >= cutoff,
        )
    )
    token_result = token_row.one()
    total_input_tokens = int(token_result[0] or 0)
    total_output_tokens = int(token_result[1] or 0)

    distinct_models_30d = (
        await db.execute(
            select(func.count(func.distinct(ProviderCall.model))).where(
                ProviderCall.workspace_id == workspace.id,
                ProviderCall.created_at >= cutoff,
            )
        )
    ).scalar() or 0

    cost_row = await db.execute(
        select(func.sum(ProviderCall.cost_usd)).where(
            ProviderCall.workspace_id == workspace.id,
            ProviderCall.created_at >= cutoff,
        )
    )
    total_cost_30d = float(cost_row.scalar() or 0)

    cache_configs = (
        await db.execute(
            select(func.count(ResponseCacheConfig.id)).where(
                ResponseCacheConfig.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    estimated_savings = round(total_cost_30d * 0.15, 2) if cache_configs > 0 else 0.0

    return EvalReplayObservePosture(
        workspace_id=workspace_id,
        period_days=30,
        runs_context={
            "runs_30d": runs_30d,
            "total_runs": total_runs,
        },
        request_flow_context={
            "provider_calls_30d": provider_calls_30d,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
        },
        model_usage_context={
            "distinct_models_30d": distinct_models_30d,
            "provider_calls_30d": provider_calls_30d,
        },
        cost_savings_context={
            "total_cost_30d": total_cost_30d,
            "cache_configs": cache_configs,
            "estimated_savings": estimated_savings,
        },
    )


@router.get("/optimization-org-gateway-posture")
async def get_optimization_org_gateway_posture(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> OptimizationOrgGatewayPosture:
    workspace_id = str(workspace.id)

    workspace_users = (
        await db.execute(
            select(func.count(WorkspaceUser.id)).where(
                WorkspaceUser.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    api_keys = (
        await db.execute(
            select(func.count(ApiKey.id)).where(
                ApiKey.workspace_id == workspace.id,
                ApiKey.revoked_at.is_(None),
            )
        )
    ).scalar() or 0

    hub_models = (
        await db.execute(
            select(func.count(HubModel.id)).where(
                HubModel.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    hub_active_models = (
        await db.execute(
            select(func.count(HubModel.id)).where(
                HubModel.workspace_id == workspace.id,
                HubModel.is_active.is_(True),
            )
        )
    ).scalar() or 0

    distinct_providers = (
        await db.execute(
            select(func.count(func.distinct(GatewayRoute.provider))).where(
                GatewayRoute.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    active_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
            )
        )
    ).scalar() or 0

    guardrail_rules = (
        await db.execute(
            select(func.count(GuardrailRule.id)).where(
                GuardrailRule.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    cache_configs = (
        await db.execute(
            select(func.count(ResponseCacheConfig.id)).where(
                ResponseCacheConfig.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    rate_limited_routes = (
        await db.execute(
            select(func.count(GatewayPassThroughEndpoint.id)).where(
                GatewayPassThroughEndpoint.workspace_id == workspace.id,
                GatewayPassThroughEndpoint.rate_limit_rpm.isnot(None),
            )
        )
    ).scalar() or 0

    return OptimizationOrgGatewayPosture(
        workspace_id=workspace_id,
        period_days=30,
        workspace_context={
            "workspace_name": workspace.name,
            "workspace_users": workspace_users,
        },
        api_key_context={
            "api_keys": api_keys,
        },
        ai_hub_context={
            "hub_models": hub_models,
            "hub_active_models": hub_active_models,
        },
        provider_context={
            "distinct_providers": distinct_providers,
            "active_routes": active_routes,
        },
        gateway_context={
            "active_routes": active_routes,
            "guardrail_rules": guardrail_rules,
        },
        guardrail_context={
            "guardrail_rules": guardrail_rules,
        },
        cache_context={
            "cache_configs": cache_configs,
        },
        rate_limit_context={
            "rate_limited_routes": rate_limited_routes,
        },
    )


@router.get("/optimization-observe-posture")
async def get_optimization_observe_posture(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> OptimizationObservePosture:
    workspace_id = str(workspace.id)
    cutoff = datetime.now(UTC) - timedelta(days=30)

    runs_30d = (
        await db.execute(
            select(func.count(AgentRun.id)).where(
                AgentRun.workspace_id == workspace.id,
                AgentRun.started_at >= cutoff,
            )
        )
    ).scalar() or 0

    total_runs = (
        await db.execute(
            select(func.count(AgentRun.id)).where(
                AgentRun.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    provider_calls_30d = (
        await db.execute(
            select(func.count(ProviderCall.id)).where(
                ProviderCall.workspace_id == workspace.id,
                ProviderCall.created_at >= cutoff,
            )
        )
    ).scalar() or 0

    token_row = await db.execute(
        select(
            func.sum(ProviderCall.input_tokens),
            func.sum(ProviderCall.output_tokens),
        ).where(
            ProviderCall.workspace_id == workspace.id,
            ProviderCall.created_at >= cutoff,
        )
    )
    token_result = token_row.one()
    total_input_tokens = int(token_result[0] or 0)
    total_output_tokens = int(token_result[1] or 0)

    distinct_models_30d = (
        await db.execute(
            select(func.count(func.distinct(ProviderCall.model))).where(
                ProviderCall.workspace_id == workspace.id,
                ProviderCall.created_at >= cutoff,
            )
        )
    ).scalar() or 0

    cost_row = await db.execute(
        select(func.sum(ProviderCall.cost_usd)).where(
            ProviderCall.workspace_id == workspace.id,
            ProviderCall.created_at >= cutoff,
        )
    )
    total_cost_30d = float(cost_row.scalar() or 0)

    cache_configs = (
        await db.execute(
            select(func.count(ResponseCacheConfig.id)).where(
                ResponseCacheConfig.workspace_id == workspace.id
            )
        )
    ).scalar() or 0

    estimated_savings = round(total_cost_30d * 0.15, 2) if cache_configs > 0 else 0.0

    return OptimizationObservePosture(
        workspace_id=workspace_id,
        period_days=30,
        runs_context={
            "runs_30d": runs_30d,
            "total_runs": total_runs,
        },
        request_flow_context={
            "provider_calls_30d": provider_calls_30d,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
        },
        model_usage_context={
            "distinct_models_30d": distinct_models_30d,
            "provider_calls_30d": provider_calls_30d,
        },
        cost_savings_context={
            "total_cost_30d": total_cost_30d,
            "cache_configs": cache_configs,
            "estimated_savings": estimated_savings,
        },
    )


@router.get("/analytics/optimization-finops-posture")
async def optimization_finops_posture(
    workspace_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> OptimizationFinOpsPosture:
    workspace = await _resolve_workspace(db, current_user, workspace_id)
    workspace_id = str(workspace.id)
    cutoff = datetime.utcnow() - timedelta(days=30)

    active_budgets = (
        await db.execute(
            select(func.count(Budget.id)).where(
                Budget.workspace_id == workspace.id,
                Budget.is_active.is_(True),
            )
        )
    ).scalar() or 0

    total_budgets = (
        await db.execute(
            select(func.count(Budget.id)).where(
                Budget.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    budget_limit_row = await db.execute(
        select(func.coalesce(func.sum(Budget.limit_amount), 0)).where(
            Budget.workspace_id == workspace.id,
            Budget.is_active.is_(True),
        )
    )
    total_limit = float(budget_limit_row.scalar() or 0)

    spend_row = await db.execute(
        select(func.coalesce(func.sum(ProviderCall.cost), 0)).where(
            ProviderCall.workspace_id == workspace.id,
            ProviderCall.created_at >= cutoff,
        )
    )
    spend_30d = float(spend_row.scalar() or 0)

    notifications = (
        await db.execute(
            select(func.count(BudgetNotification.id)).where(
                BudgetNotification.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    active_billing_periods = (
        await db.execute(
            select(func.count(BillingPeriod.id)).where(
                BillingPeriod.workspace_id == workspace.id,
                BillingPeriod.is_active.is_(True),
            )
        )
    ).scalar() or 0

    total_billing_periods = (
        await db.execute(
            select(func.count(BillingPeriod.id)).where(
                BillingPeriod.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    chargeback_rules = (
        await db.execute(
            select(func.count(ChargebackRule.id)).where(
                ChargebackRule.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    active_chargeback_rules = (
        await db.execute(
            select(func.count(ChargebackRule.id)).where(
                ChargebackRule.workspace_id == workspace.id,
                ChargebackRule.status == "active",
            )
        )
    ).scalar() or 0

    return OptimizationFinOpsPosture(
        workspace_id=workspace_id,
        period_days=30,
        budget_context={
            "active_budgets": active_budgets,
            "total_budgets": total_budgets,
            "total_limit": total_limit,
            "spend_30d": spend_30d,
            "notifications": notifications,
        },
        billing_context={
            "active_billing_periods": active_billing_periods,
            "total_billing_periods": total_billing_periods,
        },
        chargeback_context={
            "chargeback_rules": chargeback_rules,
            "active_chargeback_rules": active_chargeback_rules,
        },
    )


@router.get("/analytics/build-internal-posture")
async def get_build_internal_posture(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> BuildInternalPosture:
    workspace_id, workspace, _ = await _resolve_workspace(request, db)
    cutoff = datetime.utcnow() - timedelta(days=30)

    playground_sessions = (
        await db.execute(
            select(func.count(AgentRun.id)).where(
                AgentRun.workspace_id == workspace.id,
                AgentRun.started_at >= cutoff,
            )
        )
    ).scalar() or 0

    total_prompts = (
        await db.execute(
            select(func.count(Prompt.id)).where(
                Prompt.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    workflow_definitions = (
        await db.execute(
            select(func.count(WorkflowDefinition.id)).where(
                WorkflowDefinition.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    workflow_runs_30d = (
        await db.execute(
            select(func.count(WorkflowRun.id)).where(
                WorkflowRun.workspace_id == workspace.id,
                WorkflowRun.created_at >= cutoff,
            )
        )
    ).scalar() or 0

    eval_datasets = (
        await db.execute(
            select(func.count(EvalDataset.id)).where(
                EvalDataset.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    eval_experiments = (
        await db.execute(
            select(func.count(EvalExperiment.id)).where(
                EvalExperiment.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    replay_datasets = (
        await db.execute(
            select(func.count(ReplayDataset.id)).where(
                ReplayDataset.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    replay_experiments = (
        await db.execute(
            select(func.count(ReplayExperiment.id)).where(
                ReplayExperiment.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    hub_models = (
        await db.execute(
            select(func.count(HubModel.id)).where(
                HubModel.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    score_events_30d = (
        await db.execute(
            select(func.count(ScoreEvent.id)).where(
                ScoreEvent.workspace_id == workspace.id,
                ScoreEvent.created_at >= cutoff,
            )
        )
    ).scalar() or 0

    provider_calls_30d = (
        await db.execute(
            select(func.count(ProviderCall.id)).where(
                ProviderCall.workspace_id == workspace.id,
                ProviderCall.created_at >= cutoff,
            )
        )
    ).scalar() or 0

    spend_30d = float(
        (
            await db.execute(
                select(func.coalesce(func.sum(ProviderCall.cost), 0)).where(
                    ProviderCall.workspace_id == workspace.id,
                    ProviderCall.created_at >= cutoff,
                )
            )
        ).scalar() or 0
    )

    return BuildInternalPosture(
        workspace_id=workspace_id,
        period_days=30,
        playground_context={
            "sessions_30d": playground_sessions,
            "provider_calls_30d": provider_calls_30d,
        },
        prompts_context={
            "total_prompts": total_prompts,
        },
        workflows_context={
            "definitions": workflow_definitions,
            "runs_30d": workflow_runs_30d,
        },
        evaluation_context={
            "datasets": eval_datasets,
            "experiments": eval_experiments,
        },
        replay_context={
            "datasets": replay_datasets,
            "experiments": replay_experiments,
        },
        optimization_context={
            "hub_models": hub_models,
            "spend_30d": spend_30d,
        },
        scorecards_context={
            "hub_models": hub_models,
            "score_events_30d": score_events_30d,
        },
    )


# ── WU-011  Prompts list observe posture ──────────────────────────
@router.get(
    "/analytics/prompts-list-observe-posture",
    response_model=PromptsListObservePosture,
    tags=["analytics"],
)
async def prompts_list_observe_posture(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> PromptsListObservePosture:
    workspace_id = request.state.workspace_id
    period_days = 30
    since = datetime.utcnow() - timedelta(days=period_days)

    runs_30d = (await db.execute(
        select(func.count(AgentRun.id)).where(
            AgentRun.workspace_id == workspace_id,
            AgentRun.started_at >= since,
        )
    )).scalar_one()

    provider_calls_30d = (await db.execute(
        select(func.count(ProviderCall.id)).where(
            ProviderCall.workspace_id == workspace_id,
            ProviderCall.created_at >= since,
        )
    )).scalar_one()

    distinct_models = (await db.execute(
        select(func.count(distinct(ProviderCall.model))).where(
            ProviderCall.workspace_id == workspace_id,
            ProviderCall.created_at >= since,
        )
    )).scalar_one()

    spend_30d = (await db.execute(
        select(func.coalesce(func.sum(ProviderCall.cost), 0.0)).where(
            ProviderCall.workspace_id == workspace_id,
            ProviderCall.created_at >= since,
        )
    )).scalar_one()

    eval_datasets = (await db.execute(
        select(func.count(EvalDataset.id)).where(
            EvalDataset.workspace_id == workspace_id,
        )
    )).scalar_one()

    eval_experiments = (await db.execute(
        select(func.count(EvalExperiment.id)).where(
            EvalExperiment.workspace_id == workspace_id,
        )
    )).scalar_one()

    return PromptsListObservePosture(
        workspace_id=workspace_id,
        period_days=period_days,
        observe_context={
            "runs_30d": runs_30d,
            "provider_calls_30d": provider_calls_30d,
            "distinct_models": distinct_models,
            "spend_30d": float(spend_30d),
        },
        eval_context={
            "datasets": eval_datasets,
            "experiments": eval_experiments,
        },
    )


# ── WU-012  Prompt detail hub + FinOps posture ───────────────────
@router.get(
    "/analytics/prompt-detail-hub-finops-posture",
    response_model=PromptDetailHubFinOpsPosture,
    tags=["analytics"],
)
async def prompt_detail_hub_finops_posture(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> PromptDetailHubFinOpsPosture:
    workspace_id = request.state.workspace_id
    period_days = 30
    since = datetime.utcnow() - timedelta(days=period_days)

    hub_models = (await db.execute(
        select(func.count(HubModel.id)).where(
            HubModel.workspace_id == workspace_id,
        )
    )).scalar_one()

    active_models = (await db.execute(
        select(func.count(HubModel.id)).where(
            HubModel.workspace_id == workspace_id,
            HubModel.is_active == True,
        )
    )).scalar_one()

    chargeback_rules = (await db.execute(
        select(func.count(ChargebackRule.id)).where(
            ChargebackRule.workspace_id == workspace_id,
        )
    )).scalar_one()

    attributed_cost_30d = (await db.execute(
        select(func.coalesce(func.sum(ProviderCall.cost), 0.0)).where(
            ProviderCall.workspace_id == workspace_id,
            ProviderCall.created_at >= since,
        )
    )).scalar_one()

    return PromptDetailHubFinOpsPosture(
        workspace_id=workspace_id,
        period_days=period_days,
        hub_context={
            "hub_models": hub_models,
            "active_models": active_models,
        },
        chargeback_context={
            "rules": chargeback_rules,
            "attributed_cost_30d": float(attributed_cost_30d),
        },
    )


# ── WU-013  Agents list posture ───────────────────────────────────
@router.get(
    "/analytics/agents-list-posture",
    response_model=AgentsListPosture,
    tags=["analytics"],
)
async def agents_list_posture(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AgentsListPosture:
    workspace_id = request.state.workspace_id
    period_days = 30
    since = datetime.utcnow() - timedelta(days=period_days)

    workspace = (await db.execute(
        select(Workspace).where(Workspace.id == workspace_id)
    )).scalar_one_or_none()
    workspace_name = workspace.name if workspace else ""

    hub_models = (await db.execute(
        select(func.count(HubModel.id)).where(
            HubModel.workspace_id == workspace_id,
        )
    )).scalar_one()

    active_models = (await db.execute(
        select(func.count(HubModel.id)).where(
            HubModel.workspace_id == workspace_id,
            HubModel.is_active == True,
        )
    )).scalar_one()

    distinct_providers = (await db.execute(
        select(func.count(distinct(ProviderCall.provider))).where(
            ProviderCall.workspace_id == workspace_id,
            ProviderCall.created_at >= since,
        )
    )).scalar_one()

    runs_30d = (await db.execute(
        select(func.count(AgentRun.id)).where(
            AgentRun.workspace_id == workspace_id,
            AgentRun.started_at >= since,
        )
    )).scalar_one()

    chargeback_rules = (await db.execute(
        select(func.count(ChargebackRule.id)).where(
            ChargebackRule.workspace_id == workspace_id,
        )
    )).scalar_one()

    spend_30d = (await db.execute(
        select(func.coalesce(func.sum(ProviderCall.cost), 0.0)).where(
            ProviderCall.workspace_id == workspace_id,
            ProviderCall.created_at >= since,
        )
    )).scalar_one()

    eval_datasets = (await db.execute(
        select(func.count(EvalDataset.id)).where(
            EvalDataset.workspace_id == workspace_id,
        )
    )).scalar_one()

    eval_experiments = (await db.execute(
        select(func.count(EvalExperiment.id)).where(
            EvalExperiment.workspace_id == workspace_id,
        )
    )).scalar_one()

    return AgentsListPosture(
        workspace_id=workspace_id,
        period_days=period_days,
        org_context={
            "workspace_name": workspace_name,
            "hub_models": hub_models,
            "active_models": active_models,
        },
        provider_context={
            "distinct_providers": distinct_providers,
        },
        observe_context={
            "runs_30d": runs_30d,
        },
        finops_context={
            "chargeback_rules": chargeback_rules,
            "spend_30d": float(spend_30d),
        },
        eval_context={
            "datasets": eval_datasets,
            "experiments": eval_experiments,
        },
    )


# ── WU-014  Agent detail governance posture ───────────────────────
@router.get(
    "/analytics/agent-detail-governance-posture",
    response_model=AgentDetailGovernancePosture,
    tags=["analytics"],
)
async def agent_detail_governance_posture(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AgentDetailGovernancePosture:
    workspace_id = request.state.workspace_id
    period_days = 30
    since = datetime.utcnow() - timedelta(days=period_days)

    guardrail_rules = (await db.execute(
        select(func.count(GuardrailRule.id)).where(
            GuardrailRule.workspace_id == workspace_id,
        )
    )).scalar_one()

    guardrail_events_30d = (await db.execute(
        select(func.count(GuardrailEvent.id)).where(
            GuardrailEvent.workspace_id == workspace_id,
            GuardrailEvent.created_at >= since,
        )
    )).scalar_one()

    runs_30d = (await db.execute(
        select(func.count(AgentRun.id)).where(
            AgentRun.workspace_id == workspace_id,
            AgentRun.started_at >= since,
        )
    )).scalar_one()

    capture_policies = (await db.execute(
        select(func.count(CapturePolicy.id)).where(
            CapturePolicy.workspace_id == workspace_id,
        )
    )).scalar_one()

    security_events_30d = (await db.execute(
        select(func.count(SecurityEvent.id)).where(
            SecurityEvent.workspace_id == workspace_id,
            SecurityEvent.created_at >= since,
        )
    )).scalar_one()

    eval_datasets = (await db.execute(
        select(func.count(EvalDataset.id)).where(
            EvalDataset.workspace_id == workspace_id,
        )
    )).scalar_one()

    eval_experiments = (await db.execute(
        select(func.count(EvalExperiment.id)).where(
            EvalExperiment.workspace_id == workspace_id,
        )
    )).scalar_one()

    return AgentDetailGovernancePosture(
        workspace_id=workspace_id,
        period_days=period_days,
        guardrail_context={
            "rules": guardrail_rules,
            "events_30d": guardrail_events_30d,
        },
        observe_context={
            "runs_30d": runs_30d,
        },
        safety_context={
            "capture_policies": capture_policies,
            "security_events_30d": security_events_30d,
        },
        eval_context={
            "datasets": eval_datasets,
            "experiments": eval_experiments,
        },
    )


@router.get(
    "/analytics/workflows-list-posture",
    response_model=WorkflowsListPosture,
    tags=["analytics"],
)
async def workflows_list_posture(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> WorkflowsListPosture:
    workspace_id = request.state.workspace_id
    period_days = 30
    since = datetime.utcnow() - timedelta(days=period_days)

    ws = (await db.execute(
        select(Workspace.name).where(Workspace.id == workspace_id)
    )).scalar_one_or_none() or workspace_id

    hub_models = (await db.execute(
        select(func.count(HubModel.id)).where(
            HubModel.workspace_id == workspace_id,
        )
    )).scalar_one()

    active_models = (await db.execute(
        select(func.count(HubModel.id)).where(
            HubModel.workspace_id == workspace_id,
            HubModel.is_active == True,
        )
    )).scalar_one()

    gateway_routes = (await db.execute(
        select(func.count(GatewayRoute.id)).where(
            GatewayRoute.workspace_id == workspace_id,
        )
    )).scalar_one()

    routing_policies = (await db.execute(
        select(func.count(RoutingPolicy.id)).where(
            RoutingPolicy.workspace_id == workspace_id,
        )
    )).scalar_one()

    runs_30d = (await db.execute(
        select(func.count(AgentRun.id)).where(
            AgentRun.workspace_id == workspace_id,
            AgentRun.started_at >= since,
        )
    )).scalar_one()

    spend_30d = (await db.execute(
        select(func.coalesce(func.sum(ProviderCall.cost), 0.0)).where(
            ProviderCall.workspace_id == workspace_id,
            ProviderCall.created_at >= since,
        )
    )).scalar_one()

    eval_datasets = (await db.execute(
        select(func.count(EvalDataset.id)).where(
            EvalDataset.workspace_id == workspace_id,
        )
    )).scalar_one()

    eval_experiments = (await db.execute(
        select(func.count(EvalExperiment.id)).where(
            EvalExperiment.workspace_id == workspace_id,
        )
    )).scalar_one()

    return WorkflowsListPosture(
        workspace_id=workspace_id,
        period_days=period_days,
        org_context={
            "workspace_name": ws,
            "hub_models": hub_models,
            "active_models": active_models,
        },
        gateway_context={
            "gateway_routes": gateway_routes,
            "routing_policies": routing_policies,
        },
        observe_context={
            "runs_30d": runs_30d,
            "spend_30d": spend_30d,
        },
        eval_context={
            "datasets": eval_datasets,
            "experiments": eval_experiments,
        },
    )


@router.get(
    "/analytics/workflow-detail-loop-posture",
    response_model=WorkflowDetailLoopPosture,
    tags=["analytics"],
)
async def workflow_detail_loop_posture(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> WorkflowDetailLoopPosture:
    workspace_id = request.state.workspace_id
    period_days = 30
    since = datetime.utcnow() - timedelta(days=period_days)

    runs_30d = (await db.execute(
        select(func.count(WorkflowRun.id)).where(
            WorkflowRun.workspace_id == workspace_id,
            WorkflowRun.created_at >= since,
        )
    )).scalar_one()

    distinct_workflows = (await db.execute(
        select(func.count(func.distinct(WorkflowRun.workflow_id))).where(
            WorkflowRun.workspace_id == workspace_id,
            WorkflowRun.created_at >= since,
        )
    )).scalar_one()

    chargeback_rules = (await db.execute(
        select(func.count(ChargebackRule.id)).where(
            ChargebackRule.workspace_id == workspace_id,
        )
    )).scalar_one()

    cost_30d = (await db.execute(
        select(func.coalesce(func.sum(ProviderCall.cost), 0.0)).where(
            ProviderCall.workspace_id == workspace_id,
            ProviderCall.created_at >= since,
        )
    )).scalar_one()

    replay_experiments = (await db.execute(
        select(func.count(ReplayExperiment.id)).where(
            ReplayExperiment.workspace_id == workspace_id,
        )
    )).scalar_one()

    eval_experiments = (await db.execute(
        select(func.count(EvalExperiment.id)).where(
            EvalExperiment.workspace_id == workspace_id,
        )
    )).scalar_one()

    return WorkflowDetailLoopPosture(
        workspace_id=workspace_id,
        period_days=period_days,
        runs_context={
            "runs_30d": runs_30d,
            "distinct_workflows": distinct_workflows,
        },
        chargeback_context={
            "rules": chargeback_rules,
            "cost_30d": cost_30d,
        },
        optimization_context={
            "replay_experiments": replay_experiments,
        },
        eval_context={
            "experiments": eval_experiments,
        },
    )


@router.get(
    "/analytics/workflow-run-evidence-posture",
    response_model=WorkflowRunEvidencePosture,
    tags=["analytics"],
)
async def workflow_run_evidence_posture(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> WorkflowRunEvidencePosture:
    workspace_id = request.state.workspace_id
    period_days = 30
    since = datetime.utcnow() - timedelta(days=period_days)

    guardrail_rules = (await db.execute(
        select(func.count(GuardrailRule.id)).where(
            GuardrailRule.workspace_id == workspace_id,
        )
    )).scalar_one()

    cache_configs = (await db.execute(
        select(func.count(ResponseCacheConfig.id)).where(
            ResponseCacheConfig.workspace_id == workspace_id,
        )
    )).scalar_one()

    rate_limited_routes = (await db.execute(
        select(func.count(GatewayRoute.id)).where(
            GatewayRoute.workspace_id == workspace_id,
            GatewayRoute.per_user_rpm_limit.isnot(None),
        )
    )).scalar_one()

    runs_30d = (await db.execute(
        select(func.count(AgentRun.id)).where(
            AgentRun.workspace_id == workspace_id,
            AgentRun.started_at >= since,
        )
    )).scalar_one()

    provider_calls_30d = (await db.execute(
        select(func.count(ProviderCall.id)).where(
            ProviderCall.workspace_id == workspace_id,
            ProviderCall.created_at >= since,
        )
    )).scalar_one()

    budget_total = (await db.execute(
        select(func.count(Budget.id)).where(
            Budget.workspace_id == workspace_id,
        )
    )).scalar_one()

    cost_30d = (await db.execute(
        select(func.coalesce(func.sum(ProviderCall.cost), 0.0)).where(
            ProviderCall.workspace_id == workspace_id,
            ProviderCall.created_at >= since,
        )
    )).scalar_one()

    audit_events_30d = (await db.execute(
        select(func.count(AuditEvent.id)).where(
            AuditEvent.workspace_id == workspace_id,
            AuditEvent.created_at >= since,
        )
    )).scalar_one()

    return WorkflowRunEvidencePosture(
        workspace_id=workspace_id,
        period_days=period_days,
        gateway_context={
            "guardrail_rules": guardrail_rules,
            "cache_configs": cache_configs,
            "rate_limited_routes": rate_limited_routes,
        },
        observe_context={
            "runs_30d": runs_30d,
            "provider_calls_30d": provider_calls_30d,
        },
        finops_context={
            "budgets": budget_total,
            "cost_30d": cost_30d,
        },
        safety_context={
            "audit_events_30d": audit_events_30d,
        },
    )


@router.get(
    "/analytics/datasets-eval-asset-posture",
    response_model=DatasetsEvalAssetPosture,
    tags=["analytics"],
)
async def datasets_eval_asset_posture(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> DatasetsEvalAssetPosture:
    workspace_id = request.state.workspace_id
    period_days = 30
    since = datetime.utcnow() - timedelta(days=period_days)

    ws = (await db.execute(
        select(Workspace.name).where(Workspace.id == workspace_id)
    )).scalar_one_or_none() or "—"

    datasets_total = (await db.execute(
        select(func.count(EvalDataset.id)).where(
            EvalDataset.workspace_id == workspace_id,
        )
    )).scalar_one()

    provider_calls_30d = (await db.execute(
        select(func.count(ProviderCall.id)).where(
            ProviderCall.workspace_id == workspace_id,
            ProviderCall.created_at >= since,
        )
    )).scalar_one()

    chargeback_rules = (await db.execute(
        select(func.count(ChargebackRule.id)).where(
            ChargebackRule.workspace_id == workspace_id,
        )
    )).scalar_one()

    cost_30d = (await db.execute(
        select(func.coalesce(func.sum(ProviderCall.cost), 0.0)).where(
            ProviderCall.workspace_id == workspace_id,
            ProviderCall.created_at >= since,
        )
    )).scalar_one()

    eval_experiments = (await db.execute(
        select(func.count(EvalExperiment.id)).where(
            EvalExperiment.workspace_id == workspace_id,
        )
    )).scalar_one()

    replay_experiments = (await db.execute(
        select(func.count(ReplayExperiment.id)).where(
            ReplayExperiment.workspace_id == workspace_id,
        )
    )).scalar_one()

    return DatasetsEvalAssetPosture(
        workspace_id=workspace_id,
        period_days=period_days,
        org_context={
            "workspace_name": ws,
            "datasets": datasets_total,
        },
        observe_context={
            "provider_calls_30d": provider_calls_30d,
        },
        finops_context={
            "chargeback_rules": chargeback_rules,
            "cost_30d": cost_30d,
        },
        build_context={
            "eval_experiments": eval_experiments,
            "replay_experiments": replay_experiments,
        },
    )


@router.get(
    "/analytics/eval-studio-parent-posture",
    response_model=EvalStudioParentPosture,
    tags=["analytics"],
)
async def eval_studio_parent_posture(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> EvalStudioParentPosture:
    workspace_id = request.state.workspace_id
    period_days = 30
    since = datetime.utcnow() - timedelta(days=period_days)

    billing_periods_total = (await db.execute(
        select(func.count(BillingPeriod.id)).where(
            BillingPeriod.workspace_id == workspace_id,
        )
    )).scalar_one()

    billing_periods_open = (await db.execute(
        select(func.count(BillingPeriod.id)).where(
            BillingPeriod.workspace_id == workspace_id,
            BillingPeriod.status == "open",
        )
    )).scalar_one()

    chargeback_rules = (await db.execute(
        select(func.count(ChargebackRule.id)).where(
            ChargebackRule.workspace_id == workspace_id,
        )
    )).scalar_one()

    cost_30d = (await db.execute(
        select(func.coalesce(func.sum(ProviderCall.cost), 0.0)).where(
            ProviderCall.workspace_id == workspace_id,
            ProviderCall.created_at >= since,
        )
    )).scalar_one()

    eval_datasets = (await db.execute(
        select(func.count(EvalDataset.id)).where(
            EvalDataset.workspace_id == workspace_id,
        )
    )).scalar_one()

    eval_experiments = (await db.execute(
        select(func.count(EvalExperiment.id)).where(
            EvalExperiment.workspace_id == workspace_id,
        )
    )).scalar_one()

    replay_experiments = (await db.execute(
        select(func.count(ReplayExperiment.id)).where(
            ReplayExperiment.workspace_id == workspace_id,
        )
    )).scalar_one()

    return EvalStudioParentPosture(
        workspace_id=workspace_id,
        period_days=period_days,
        billing_context={
            "billing_periods": billing_periods_total,
            "open_periods": billing_periods_open,
        },
        chargeback_context={
            "chargeback_rules": chargeback_rules,
            "cost_30d": cost_30d,
        },
        eval_self_context={
            "datasets": eval_datasets,
            "experiments": eval_experiments,
            "replay_experiments": replay_experiments,
        },
    )


@router.get(
    "/analytics/experiments-comparison-posture",
    response_model=ExperimentsComparisonPosture,
    tags=["analytics"],
)
async def experiments_comparison_posture(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ExperimentsComparisonPosture:
    workspace_id = request.state.workspace_id
    period_days = 30
    since = datetime.utcnow() - timedelta(days=period_days)

    billing_periods_total = (await db.execute(
        select(func.count(BillingPeriod.id)).where(
            BillingPeriod.workspace_id == workspace_id,
        )
    )).scalar_one()

    billing_periods_open = (await db.execute(
        select(func.count(BillingPeriod.id)).where(
            BillingPeriod.workspace_id == workspace_id,
            BillingPeriod.status == "open",
        )
    )).scalar_one()

    chargeback_rules = (await db.execute(
        select(func.count(ChargebackRule.id)).where(
            ChargebackRule.workspace_id == workspace_id,
        )
    )).scalar_one()

    cost_30d = (await db.execute(
        select(func.coalesce(func.sum(ProviderCall.cost), 0.0)).where(
            ProviderCall.workspace_id == workspace_id,
            ProviderCall.created_at >= since,
        )
    )).scalar_one()

    eval_experiments = (await db.execute(
        select(func.count(EvalExperiment.id)).where(
            EvalExperiment.workspace_id == workspace_id,
        )
    )).scalar_one()

    replay_experiments = (await db.execute(
        select(func.count(ReplayExperiment.id)).where(
            ReplayExperiment.workspace_id == workspace_id,
        )
    )).scalar_one()

    eval_datasets = (await db.execute(
        select(func.count(EvalDataset.id)).where(
            EvalDataset.workspace_id == workspace_id,
        )
    )).scalar_one()

    return ExperimentsComparisonPosture(
        workspace_id=workspace_id,
        period_days=period_days,
        billing_context={
            "billing_periods": billing_periods_total,
            "open_periods": billing_periods_open,
        },
        chargeback_context={
            "chargeback_rules": chargeback_rules,
            "cost_30d": cost_30d,
        },
        comparison_context={
            "eval_experiments": eval_experiments,
            "replay_experiments": replay_experiments,
            "datasets": eval_datasets,
        },
    )


@router.get(
    "/analytics/replay-lab-mode-posture",
    response_model=ReplayLabModePosture,
    tags=["analytics"],
)
async def replay_lab_mode_posture(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ReplayLabModePosture:
    workspace_id = request.state.workspace_id
    period_days = 30
    since = datetime.utcnow() - timedelta(days=period_days)

    chargeback_rules = (await db.execute(
        select(func.count(ChargebackRule.id)).where(
            ChargebackRule.workspace_id == workspace_id,
        )
    )).scalar_one()

    cost_30d = (await db.execute(
        select(func.coalesce(func.sum(ProviderCall.cost), 0.0)).where(
            ProviderCall.workspace_id == workspace_id,
            ProviderCall.created_at >= since,
        )
    )).scalar_one()

    replay_experiments = (await db.execute(
        select(func.count(ReplayExperiment.id)).where(
            ReplayExperiment.workspace_id == workspace_id,
        )
    )).scalar_one()

    replay_datasets = (await db.execute(
        select(func.count(ReplayDataset.id)).where(
            ReplayDataset.workspace_id == workspace_id,
        )
    )).scalar_one()

    return ReplayLabModePosture(
        workspace_id=workspace_id,
        period_days=period_days,
        chargeback_context={
            "chargeback_rules": chargeback_rules,
            "cost_30d": cost_30d,
        },
        replay_context={
            "replay_experiments": replay_experiments,
            "replay_datasets": replay_datasets,
        },
    )


@router.get(
    "/analytics/replay-result-analysis-posture",
    response_model=ReplayResultAnalysisPosture,
    tags=["analytics"],
)
async def replay_result_analysis_posture(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ReplayResultAnalysisPosture:
    workspace_id = request.state.workspace_id
    period_days = 30
    since = datetime.utcnow() - timedelta(days=period_days)

    guardrail_rules = (await db.execute(
        select(func.count(GuardrailRule.id)).where(
            GuardrailRule.workspace_id == workspace_id,
        )
    )).scalar_one()

    cache_configs = (await db.execute(
        select(func.count(ResponseCacheConfig.id)).where(
            ResponseCacheConfig.workspace_id == workspace_id,
        )
    )).scalar_one()

    runs_30d = (await db.execute(
        select(func.count(AgentRun.id)).where(
            AgentRun.workspace_id == workspace_id,
            AgentRun.started_at >= since,
        )
    )).scalar_one()

    provider_calls_30d = (await db.execute(
        select(func.count(ProviderCall.id)).where(
            ProviderCall.workspace_id == workspace_id,
            ProviderCall.created_at >= since,
        )
    )).scalar_one()

    cost_30d = (await db.execute(
        select(func.coalesce(func.sum(ProviderCall.cost), 0.0)).where(
            ProviderCall.workspace_id == workspace_id,
            ProviderCall.created_at >= since,
        )
    )).scalar_one()

    replay_experiments = (await db.execute(
        select(func.count(ReplayExperiment.id)).where(
            ReplayExperiment.workspace_id == workspace_id,
        )
    )).scalar_one()

    return ReplayResultAnalysisPosture(
        workspace_id=workspace_id,
        period_days=period_days,
        gateway_context={
            "guardrail_rules": guardrail_rules,
            "cache_configs": cache_configs,
        },
        observe_context={
            "runs_30d": runs_30d,
            "provider_calls_30d": provider_calls_30d,
        },
        cost_context={
            "cost_30d": cost_30d,
            "replay_experiments": replay_experiments,
        },
    )


@router.get(
    "/analytics/runbooks-remediation-posture",
    response_model=RunbooksRemediationPosture,
    tags=["analytics"],
)
async def runbooks_remediation_posture(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> RunbooksRemediationPosture:
    workspace_id = request.state.workspace_id
    period_days = 30
    since = datetime.utcnow() - timedelta(days=period_days)

    runs_30d = (await db.execute(
        select(func.count(AgentRun.id)).where(
            AgentRun.workspace_id == workspace_id,
            AgentRun.started_at >= since,
        )
    )).scalar_one()

    provider_calls_30d = (await db.execute(
        select(func.count(ProviderCall.id)).where(
            ProviderCall.workspace_id == workspace_id,
            ProviderCall.created_at >= since,
        )
    )).scalar_one()

    alert_rules = (await db.execute(
        select(func.count(AlertRule.id)).where(
            AlertRule.workspace_id == workspace_id,
        )
    )).scalar_one()

    alert_firings_30d = (await db.execute(
        select(func.count(AlertFiring.id)).where(
            AlertFiring.workspace_id == workspace_id,
            AlertFiring.fired_at >= since,
        )
    )).scalar_one()

    cost_30d = (await db.execute(
        select(func.coalesce(func.sum(ProviderCall.cost), 0.0)).where(
            ProviderCall.workspace_id == workspace_id,
            ProviderCall.created_at >= since,
        )
    )).scalar_one()

    billing_periods = (await db.execute(
        select(func.count(BillingPeriod.id)).where(
            BillingPeriod.workspace_id == workspace_id,
        )
    )).scalar_one()

    eval_experiments = (await db.execute(
        select(func.count(EvalExperiment.id)).where(
            EvalExperiment.workspace_id == workspace_id,
        )
    )).scalar_one()

    return RunbooksRemediationPosture(
        workspace_id=workspace_id,
        period_days=period_days,
        observe_context={
            "runs_30d": runs_30d,
            "provider_calls_30d": provider_calls_30d,
        },
        alert_context={
            "alert_rules": alert_rules,
            "alert_firings_30d": alert_firings_30d,
        },
        cost_context={
            "cost_30d": cost_30d,
            "billing_periods": billing_periods,
        },
        optimization_context={
            "eval_experiments": eval_experiments,
        },
    )


@router.get(
    "/analytics/opt-opps-rationale-posture",
    response_model=OptOppsRationalePosture,
    tags=["analytics"],
)
async def opt_opps_rationale_posture(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> OptOppsRationalePosture:
    workspace_id = request.state.workspace_id
    period_days = 30
    since = datetime.utcnow() - timedelta(days=period_days)

    cost_30d = (await db.execute(
        select(func.coalesce(func.sum(ProviderCall.cost), 0.0)).where(
            ProviderCall.workspace_id == workspace_id,
            ProviderCall.created_at >= since,
        )
    )).scalar_one()

    eval_experiments = (await db.execute(
        select(func.count(EvalExperiment.id)).where(
            EvalExperiment.workspace_id == workspace_id,
        )
    )).scalar_one()

    replay_experiments = (await db.execute(
        select(func.count(ReplayExperiment.id)).where(
            ReplayExperiment.workspace_id == workspace_id,
        )
    )).scalar_one()

    score_events_30d = (await db.execute(
        select(func.count(ScoreEvent.id)).where(
            ScoreEvent.workspace_id == workspace_id,
            ScoreEvent.created_at >= since,
        )
    )).scalar_one()

    return OptOppsRationalePosture(
        workspace_id=workspace_id,
        period_days=period_days,
        cost_context={
            "cost_30d": cost_30d,
        },
        optimization_context={
            "eval_experiments": eval_experiments,
            "replay_experiments": replay_experiments,
            "score_events_30d": score_events_30d,
        },
    )


@router.get(
    "/analytics/opt-sim-decision-posture",
    response_model=OptSimDecisionPosture,
    tags=["analytics"],
)
async def opt_sim_decision_posture(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> OptSimDecisionPosture:
    workspace_id = request.state.workspace_id
    period_days = 30
    since = datetime.utcnow() - timedelta(days=period_days)

    cost_30d = (await db.execute(
        select(func.coalesce(func.sum(ProviderCall.cost), 0.0)).where(
            ProviderCall.workspace_id == workspace_id,
            ProviderCall.created_at >= since,
        )
    )).scalar_one()

    eval_experiments = (await db.execute(
        select(func.count(EvalExperiment.id)).where(
            EvalExperiment.workspace_id == workspace_id,
        )
    )).scalar_one()

    replay_experiments = (await db.execute(
        select(func.count(ReplayExperiment.id)).where(
            ReplayExperiment.workspace_id == workspace_id,
        )
    )).scalar_one()

    score_events_30d = (await db.execute(
        select(func.count(ScoreEvent.id)).where(
            ScoreEvent.workspace_id == workspace_id,
            ScoreEvent.created_at >= since,
        )
    )).scalar_one()

    return OptSimDecisionPosture(
        workspace_id=workspace_id,
        period_days=period_days,
        cost_context={
            "cost_30d": cost_30d,
        },
        optimization_context={
            "eval_experiments": eval_experiments,
            "replay_experiments": replay_experiments,
            "score_events_30d": score_events_30d,
        },
    )


@router.get(
    "/analytics/model-scorecards-intel-posture",
    response_model=ModelScorecardsIntelPosture,
    tags=["analytics"],
)
async def model_scorecards_intel_posture(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ModelScorecardsIntelPosture:
    workspace_id = request.state.workspace_id
    period_days = 30
    since = datetime.utcnow() - timedelta(days=period_days)

    hub_models = (await db.execute(
        select(func.count(HubModel.id)).where(
            HubModel.workspace_id == workspace_id,
        )
    )).scalar_one()

    distinct_models_30d = (await db.execute(
        select(func.count(func.distinct(ProviderCall.model))).where(
            ProviderCall.workspace_id == workspace_id,
            ProviderCall.created_at >= since,
        )
    )).scalar_one()

    cost_30d = (await db.execute(
        select(func.coalesce(func.sum(ProviderCall.cost), 0.0)).where(
            ProviderCall.workspace_id == workspace_id,
            ProviderCall.created_at >= since,
        )
    )).scalar_one()

    score_events_30d = (await db.execute(
        select(func.count(ScoreEvent.id)).where(
            ScoreEvent.workspace_id == workspace_id,
            ScoreEvent.created_at >= since,
        )
    )).scalar_one()

    eval_experiments = (await db.execute(
        select(func.count(EvalExperiment.id)).where(
            EvalExperiment.workspace_id == workspace_id,
        )
    )).scalar_one()

    return ModelScorecardsIntelPosture(
        workspace_id=workspace_id,
        period_days=period_days,
        model_context={
            "hub_models": hub_models,
            "distinct_models_30d": distinct_models_30d,
        },
        cost_context={
            "cost_30d": cost_30d,
        },
        optimization_context={
            "score_events_30d": score_events_30d,
            "eval_experiments": eval_experiments,
        },
    )


@router.get(
    "/analytics/vector-stores-lifecycle-posture",
    response_model=VectorStoresLifecyclePosture,
    tags=["analytics"],
)
async def vector_stores_lifecycle_posture(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> VectorStoresLifecyclePosture:
    workspace_id = request.state.workspace_id
    period_days = 30
    since = datetime.utcnow() - timedelta(days=period_days)

    workspace = (await db.execute(
        select(Workspace.name).where(Workspace.id == workspace_id)
    )).scalar_one_or_none() or "unknown"

    provider_calls_30d = (await db.execute(
        select(func.count(ProviderCall.id)).where(
            ProviderCall.workspace_id == workspace_id,
            ProviderCall.created_at >= since,
        )
    )).scalar_one()

    cost_30d = (await db.execute(
        select(func.coalesce(func.sum(ProviderCall.cost), 0.0)).where(
            ProviderCall.workspace_id == workspace_id,
            ProviderCall.created_at >= since,
        )
    )).scalar_one()

    chargeback_rules = (await db.execute(
        select(func.count(ChargebackRule.id)).where(
            ChargebackRule.workspace_id == workspace_id,
        )
    )).scalar_one()

    workflows = (await db.execute(
        select(func.count(WorkflowDefinition.id)).where(
            WorkflowDefinition.workspace_id == workspace_id,
        )
    )).scalar_one()

    eval_experiments = (await db.execute(
        select(func.count(EvalExperiment.id)).where(
            EvalExperiment.workspace_id == workspace_id,
        )
    )).scalar_one()

    return VectorStoresLifecyclePosture(
        workspace_id=workspace_id,
        period_days=period_days,
        workspace_context={
            "workspace_name": workspace,
        },
        observe_context={
            "provider_calls_30d": provider_calls_30d,
        },
        cost_context={
            "cost_30d": cost_30d,
            "chargeback_rules": chargeback_rules,
        },
        build_context={
            "workflows": workflows,
            "eval_experiments": eval_experiments,
        },
    )


@router.get(
    "/analytics/vector-store-detail-evidence-posture",
    response_model=VectorStoreDetailEvidencePosture,
    tags=["analytics"],
)
async def vector_store_detail_evidence_posture(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> VectorStoreDetailEvidencePosture:
    workspace_id = request.state.workspace_id
    period_days = 30
    since = datetime.utcnow() - timedelta(days=period_days)

    provider_calls_30d = (await db.execute(
        select(func.count(ProviderCall.id)).where(
            ProviderCall.workspace_id == workspace_id,
            ProviderCall.created_at >= since,
        )
    )).scalar_one()

    runs_30d = (await db.execute(
        select(func.count(AgentRun.id)).where(
            AgentRun.workspace_id == workspace_id,
            AgentRun.started_at >= since,
        )
    )).scalar_one()

    cost_30d = (await db.execute(
        select(func.coalesce(func.sum(ProviderCall.cost), 0.0)).where(
            ProviderCall.workspace_id == workspace_id,
            ProviderCall.created_at >= since,
        )
    )).scalar_one()

    chargeback_rules = (await db.execute(
        select(func.count(ChargebackRule.id)).where(
            ChargebackRule.workspace_id == workspace_id,
        )
    )).scalar_one()

    workflows = (await db.execute(
        select(func.count(WorkflowDefinition.id)).where(
            WorkflowDefinition.workspace_id == workspace_id,
        )
    )).scalar_one()

    eval_experiments = (await db.execute(
        select(func.count(EvalExperiment.id)).where(
            EvalExperiment.workspace_id == workspace_id,
        )
    )).scalar_one()

    return VectorStoreDetailEvidencePosture(
        workspace_id=workspace_id,
        period_days=period_days,
        observe_context={
            "provider_calls_30d": provider_calls_30d,
            "runs_30d": runs_30d,
        },
        cost_context={
            "cost_30d": cost_30d,
            "chargeback_rules": chargeback_rules,
        },
        build_context={
            "workflows": workflows,
            "eval_experiments": eval_experiments,
        },
    )


@router.get(
    "/platform-lifecycle-posture",
    response_model=PlatformLifecyclePosture,
)
async def platform_lifecycle_posture(
    admin: tuple = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
    _rl: None = Depends(analytics_rate_limit),
):
    workspace, user = admin
    t_from = _default_from()
    period_days = _DEFAULT_LOOKBACK_DAYS

    billing_periods = (
        await db.execute(select(func.count(BillingPeriod.id)))
    ).scalar() or 0

    active_billing_periods = (
        await db.execute(
            select(func.count(BillingPeriod.id)).where(
                BillingPeriod.status == "open"
            )
        )
    ).scalar() or 0

    chargeback_rules = (
        await db.execute(select(func.count(ChargebackRule.id)))
    ).scalar() or 0

    ledger_snapshots = (
        await db.execute(select(func.count(LedgerSnapshot.id)))
    ).scalar() or 0

    gateway_routes = (
        await db.execute(select(func.count(GatewayRoute.id)))
    ).scalar() or 0

    providers = (
        await db.execute(
            select(func.count(func.distinct(GatewayRoute.provider)))
        )
    ).scalar() or 0

    guardrail_rules = (
        await db.execute(select(func.count(GuardrailRule.id)))
    ).scalar() or 0

    audit_events_30d = (
        await db.execute(
            select(func.count(AuditEvent.id)).where(
                AuditEvent.created_at >= t_from
            )
        )
    ).scalar() or 0

    tool_policies = (
        await db.execute(select(func.count(ToolPolicy.id)))
    ).scalar() or 0

    alert_rules = (
        await db.execute(select(func.count(AlertRule.id)))
    ).scalar() or 0

    total_workspaces = (
        await db.execute(select(func.count(Workspace.id)))
    ).scalar() or 0

    total_api_keys = (
        await db.execute(select(func.count(ApiKey.id)))
    ).scalar() or 0

    total_users = (
        await db.execute(select(func.count(TenantUser.id)))
    ).scalar() or 0

    return PlatformLifecyclePosture(
        period_days=period_days,
        finops_context={
            "billing_periods": billing_periods,
            "active_billing_periods": active_billing_periods,
            "chargeback_rules": chargeback_rules,
            "ledger_snapshots": ledger_snapshots,
        },
        gateway_context={
            "gateway_routes": gateway_routes,
            "distinct_providers": providers,
            "guardrail_rules": guardrail_rules,
        },
        governance_context={
            "audit_events_30d": audit_events_30d,
            "tool_policies": tool_policies,
            "alert_rules": alert_rules,
        },
        org_access_context={
            "total_workspaces": total_workspaces,
            "total_api_keys": total_api_keys,
            "total_users": total_users,
        },
    )


@router.get(
    "/platform-settings-convergence-posture",
    response_model=PlatformSettingsConvergencePosture,
)
async def platform_settings_convergence_posture(
    admin: tuple = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
    _rl: None = Depends(analytics_rate_limit),
):
    workspace, user = admin
    t_from = _default_from()
    period_days = _DEFAULT_LOOKBACK_DAYS

    otlp_batches = (
        await db.execute(
            select(func.count(OtlpIngestBatch.id)).where(
                OtlpIngestBatch.created_at >= t_from
            )
        )
    ).scalar() or 0

    otlp_spans = (
        await db.execute(
            select(func.coalesce(func.sum(OtlpIngestBatch.span_count), 0)).where(
                OtlpIngestBatch.created_at >= t_from
            )
        )
    ).scalar() or 0

    capture_policies = (
        await db.execute(select(func.count(CapturePolicy.id)))
    ).scalar() or 0

    audit_events = (
        await db.execute(
            select(func.count(AuditEvent.id)).where(
                AuditEvent.created_at >= t_from
            )
        )
    ).scalar() or 0

    security_events = (
        await db.execute(
            select(func.count(SecurityEvent.id)).where(
                SecurityEvent.created_at >= t_from
            )
        )
    ).scalar() or 0

    ledger_snapshots = (
        await db.execute(select(func.count(LedgerSnapshot.id)))
    ).scalar() or 0

    ledger_closures = (
        await db.execute(
            select(func.count(LedgerSnapshot.id)).where(
                LedgerSnapshot.is_signed.is_(True)
            )
        )
    ).scalar() or 0

    alert_rules = (
        await db.execute(select(func.count(AlertRule.id)))
    ).scalar() or 0

    alert_firings = (
        await db.execute(
            select(func.count(AlertFiring.id)).where(
                AlertFiring.created_at >= t_from
            )
        )
    ).scalar() or 0

    return PlatformSettingsConvergencePosture(
        period_days=period_days,
        telemetry_context={
            "otlp_batches_7d": otlp_batches,
            "otlp_spans_7d": otlp_spans,
            "capture_policies": capture_policies,
        },
        audit_context={
            "audit_events_7d": audit_events,
            "security_events_7d": security_events,
        },
        compliance_context={
            "ledger_snapshots": ledger_snapshots,
            "ledger_closures": ledger_closures,
        },
        ops_context={
            "alert_rules": alert_rules,
            "alert_firings_7d": alert_firings,
        },
    )


@router.get(
    "/platform-admin-observe-posture",
    response_model=PlatformAdminObservePosture,
)
async def platform_admin_observe_posture(
    admin: tuple = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
    _rl: None = Depends(analytics_rate_limit),
):
    workspace, user = admin
    t_from = _default_from()
    period_days = _DEFAULT_LOOKBACK_DAYS

    alert_rules = (
        await db.execute(select(func.count(AlertRule.id)))
    ).scalar() or 0

    alert_firings = (
        await db.execute(
            select(func.count(AlertFiring.id)).where(
                AlertFiring.created_at >= t_from
            )
        )
    ).scalar() or 0

    otlp_batches = (
        await db.execute(
            select(func.count(OtlpIngestBatch.id)).where(
                OtlpIngestBatch.created_at >= t_from
            )
        )
    ).scalar() or 0

    otlp_spans = (
        await db.execute(
            select(func.coalesce(func.sum(OtlpIngestBatch.span_count), 0)).where(
                OtlpIngestBatch.created_at >= t_from
            )
        )
    ).scalar() or 0

    guardrail_rules = (
        await db.execute(select(func.count(GuardrailRule.id)))
    ).scalar() or 0

    guardrail_events = (
        await db.execute(
            select(func.count(GuardrailEvent.id)).where(
                GuardrailEvent.created_at >= t_from
            )
        )
    ).scalar() or 0

    tool_policies = (
        await db.execute(select(func.count(ToolPolicy.id)))
    ).scalar() or 0

    governance_packs = (
        await db.execute(select(func.count(CapturePolicy.id)))
    ).scalar() or 0

    eval_experiments = (
        await db.execute(select(func.count(EvalExperiment.id)))
    ).scalar() or 0

    eval_datasets = (
        await db.execute(select(func.count(EvalDataset.id)))
    ).scalar() or 0

    agents = (
        await db.execute(select(func.count(Agent.id)))
    ).scalar() or 0

    workflow_runs = (
        await db.execute(
            select(func.count(WorkflowRun.id)).where(
                WorkflowRun.created_at >= t_from
            )
        )
    ).scalar() or 0

    return PlatformAdminObservePosture(
        period_days=period_days,
        monitoring_context={
            "alert_rules": alert_rules,
            "alert_firings_7d": alert_firings,
            "guardrail_events_7d": guardrail_events,
        },
        telemetry_context={
            "otlp_batches_7d": otlp_batches,
            "otlp_spans_7d": otlp_spans,
        },
        governance_context={
            "guardrail_rules": guardrail_rules,
            "tool_policies": tool_policies,
            "capture_policies": governance_packs,
        },
        build_context={
            "eval_experiments": eval_experiments,
            "eval_datasets": eval_datasets,
            "agents": agents,
            "workflow_runs_7d": workflow_runs,
        },
    )


@router.get(
    "/gateway-runtime-boundary-posture",
    response_model=GatewayRuntimeBoundaryPosture,
)
async def gateway_runtime_boundary_posture(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _user: TenantUser = Depends(get_current_user),
    _rl: None = Depends(analytics_rate_limit),
):
    from runledger_api.models.gateway import GatewayRequest, GatewayRoutingGroup

    now = datetime.now(UTC)
    thirty_days_ago = now - timedelta(days=30)
    seven_days_ago = now - timedelta(days=7)

    active_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
            )
        )
    ).scalar() or 0

    total_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    distinct_providers = (
        await db.execute(
            select(func.count(sa.distinct(GatewayRoute.provider))).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
            )
        )
    ).scalar() or 0

    direct_http_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
                GatewayRoute.provider.in_(
                    ["openai", "anthropic", "ollama", "vllm", "local", "groq", "mistral", "custom", "azure", "vertex"]
                ),
            )
        )
    ).scalar() or 0

    routing_groups = (
        await db.execute(
            select(func.count(GatewayRoutingGroup.id)).where(
                GatewayRoutingGroup.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    routing_policies = (
        await db.execute(
            select(func.count(RoutingPolicy.id)).where(
                RoutingPolicy.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    passthrough_endpoints = (
        await db.execute(
            select(func.count(GatewayPassThroughEndpoint.id)).where(
                GatewayPassThroughEndpoint.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    active_guardrails = (
        await db.execute(
            select(func.count(GuardrailRule.id)).where(
                GuardrailRule.workspace_id == workspace.id,
                GuardrailRule.status == "active",
            )
        )
    ).scalar() or 0

    cache_configs = (
        await db.execute(
            select(func.count(ResponseCacheConfig.id)).where(
                ResponseCacheConfig.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    requests_7d = (
        await db.execute(
            select(func.count(GatewayRequest.id)).where(
                GatewayRequest.workspace_id == workspace.id,
                GatewayRequest.created_at >= seven_days_ago,
            )
        )
    ).scalar() or 0

    cache_hits_7d = (
        await db.execute(
            select(func.count(GatewayRequest.id)).where(
                GatewayRequest.workspace_id == workspace.id,
                GatewayRequest.created_at >= seven_days_ago,
                GatewayRequest.status == "cache_hit",
            )
        )
    ).scalar() or 0

    budgets = (
        await db.execute(
            select(func.count(Budget.id)).where(
                Budget.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    api_keys = (
        await db.execute(
            select(func.count(ApiKey.id)).where(
                ApiKey.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    tool_policies = (
        await db.execute(
            select(func.count(ToolPolicy.id)).where(
                ToolPolicy.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    monitoring_alerts = (
        await db.execute(
            select(func.count(AlertRule.id)).where(
                AlertRule.workspace_id == workspace.id,
                AlertRule.is_active.is_(True),
            )
        )
    ).scalar() or 0

    audit_events_30d = (
        await db.execute(
            select(func.count(AuditEvent.id)).where(
                AuditEvent.workspace_id == workspace.id,
                AuditEvent.created_at >= thirty_days_ago,
            )
        )
    ).scalar() or 0

    return GatewayRuntimeBoundaryPosture(
        workspace_id=str(workspace.id),
        rust_data_plane={
            "service": "runledger-gateway-rs",
            "port": 8210,
            "capabilities": [
                "openai_compatible_chat_completions",
                "direct_http_provider_execution",
                "retry_and_fallback_loop",
                "streaming_passthrough",
                "hmac_signed_event_ingest",
            ],
            "direct_http_routes": direct_http_routes,
            "active_routes": active_routes,
            "distinct_providers": distinct_providers,
        },
        python_control_plane={
            "modules": [
                "gateway_routing",
                "gateway_runtime",
                "gateway_observability",
                "gateway_passthrough",
                "gateway_legacy",
            ],
            "ownership": [
                "route_crud",
                "routing_group_crud",
                "routing_policy_crud",
                "runtime_snapshot",
                "preflight_decisions",
                "finalize_and_metering",
                "guardrail_evaluation",
                "cache_management",
                "passthrough_proxy",
                "observability_stats",
            ],
            "total_routes": total_routes,
            "routing_groups": routing_groups,
            "routing_policies": routing_policies,
            "passthrough_endpoints": passthrough_endpoints,
            "cache_configs": cache_configs,
        },
        hot_path_migration={
            "legacy_stub": "410_gone",
            "legacy_route": "/gateway/chat/completions",
            "runtime_owner": "runledger-gateway-rs",
            "preflight_owner": "python_control_plane",
            "execution_owner": "rust_data_plane",
            "finalize_owner": "python_control_plane",
            "active_guardrails": active_guardrails,
            "budgets": budgets,
        },
        runtime_contracts={
            "preflight": "/gateway/runtime/internal/preflight",
            "finalize": "/gateway/runtime/internal/finalize",
            "resolve_api_key": "/gateway/runtime/internal/resolve-api-key",
            "provider_execute": "/gateway/runtime/internal/provider-execute",
            "route_result": "/gateway/runtime/internal/route-result",
            "mirror": "/gateway/runtime/internal/mirror",
            "signed_events": "/gateway/runtime/events/signed",
            "snapshot": "/gateway/runtime/snapshot",
            "internal_snapshot": "/gateway/runtime/internal/snapshot",
            "api_keys": api_keys,
            "tool_policies": tool_policies,
        },
        observe_context={
            "requests_7d": requests_7d,
            "cache_hits_7d": cache_hits_7d,
            "monitoring_alerts": monitoring_alerts,
            "audit_events_30d": audit_events_30d,
        },
    )


@router.get(
    "/sidecar-collapse-posture",
    response_model=SidecarCollapsePosture,
)
async def sidecar_collapse_posture(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _user: TenantUser = Depends(get_current_user),
    _rl: None = Depends(analytics_rate_limit),
):
    from runledger_api.models.gateway import GatewayRequest, GatewayRoutingGroup

    now = datetime.now(UTC)
    seven_days_ago = now - timedelta(days=7)

    active_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
            )
        )
    ).scalar() or 0

    ir_enabled_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
                GatewayRoute.intelligent_routing_enabled.is_(True),
            )
        )
    ).scalar() or 0

    routing_groups = (
        await db.execute(
            select(func.count(GatewayRoutingGroup.id)).where(
                GatewayRoutingGroup.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    routing_policies = (
        await db.execute(
            select(func.count(RoutingPolicy.id)).where(
                RoutingPolicy.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    requests_7d = (
        await db.execute(
            select(func.count(GatewayRequest.id)).where(
                GatewayRequest.workspace_id == workspace.id,
                GatewayRequest.created_at >= seven_days_ago,
            )
        )
    ).scalar() or 0

    routed_requests_7d = (
        await db.execute(
            select(func.count(GatewayRequest.id)).where(
                GatewayRequest.workspace_id == workspace.id,
                GatewayRequest.created_at >= seven_days_ago,
                GatewayRequest.decision_reason.isnot(None),
            )
        )
    ).scalar() or 0

    distinct_providers = (
        await db.execute(
            select(func.count(sa.distinct(GatewayRoute.provider))).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
            )
        )
    ).scalar() or 0

    cache_configs = (
        await db.execute(
            select(func.count(ResponseCacheConfig.id)).where(
                ResponseCacheConfig.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    active_guardrails = (
        await db.execute(
            select(func.count(GuardrailRule.id)).where(
                GuardrailRule.workspace_id == workspace.id,
                GuardrailRule.status == "active",
            )
        )
    ).scalar() or 0

    return SidecarCollapsePosture(
        workspace_id=str(workspace.id),
        collapsed_service={
            "name": "runledger-router",
            "former_port": 8105,
            "status": "deprecated",
            "absorbed_by": "runledger-gateway-rs",
            "profile": "deprecated",
        },
        gateway_rs_absorption={
            "service": "runledger-gateway-rs",
            "port": 8210,
            "classifier_endpoint": "/classify",
            "classifier_modes": ["heuristic", "llm", "hybrid"],
            "ir_enabled_routes": ir_enabled_routes,
            "active_routes": active_routes,
            "distinct_providers": distinct_providers,
        },
        topology_simplification={
            "services_removed": ["runledger-router"],
            "env_vars_redirected": ["ROUTER_SVC_URL"],
            "compose_profiles_affected": ["aux", "full-prod", "full-demo"],
            "new_default_target": "http://runledger-gateway-rs:8210",
        },
        routing_classification={
            "owner": "runledger-gateway-rs",
            "classify_path": "/classify",
            "fallback": "passthrough_to_requested_alias",
            "routing_groups": routing_groups,
            "routing_policies": routing_policies,
            "cache_configs": cache_configs,
            "active_guardrails": active_guardrails,
        },
        observe_context={
            "requests_7d": requests_7d,
            "routed_requests_7d": routed_requests_7d,
        },
    )


@router.get(
    "/consumer-migration-posture",
    response_model=ConsumerMigrationPosture,
)
async def consumer_migration_posture(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _user: TenantUser = Depends(get_current_user),
    _rl: None = Depends(analytics_rate_limit),
):
    from runledger_api.models.gateway import GatewayRequest

    now = datetime.now(UTC)
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    active_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
            )
        )
    ).scalar() or 0

    total_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    distinct_providers = (
        await db.execute(
            select(func.count(sa.distinct(GatewayRoute.provider))).where(
                GatewayRoute.workspace_id == workspace.id,
                GatewayRoute.is_active.is_(True),
            )
        )
    ).scalar() or 0

    requests_7d = (
        await db.execute(
            select(func.count(GatewayRequest.id)).where(
                GatewayRequest.workspace_id == workspace.id,
                GatewayRequest.created_at >= seven_days_ago,
            )
        )
    ).scalar() or 0

    requests_30d = (
        await db.execute(
            select(func.count(GatewayRequest.id)).where(
                GatewayRequest.workspace_id == workspace.id,
                GatewayRequest.created_at >= thirty_days_ago,
            )
        )
    ).scalar() or 0

    cache_hits_7d = (
        await db.execute(
            select(func.count(GatewayRequest.id)).where(
                GatewayRequest.workspace_id == workspace.id,
                GatewayRequest.created_at >= seven_days_ago,
                GatewayRequest.status == "cache_hit",
            )
        )
    ).scalar() or 0

    api_keys = (
        await db.execute(
            select(func.count(ApiKey.id)).where(
                ApiKey.workspace_id == workspace.id,
            )
        )
    ).scalar() or 0

    audit_events_30d = (
        await db.execute(
            select(func.count(AuditEvent.id)).where(
                AuditEvent.workspace_id == workspace.id,
                AuditEvent.created_at >= thirty_days_ago,
            )
        )
    ).scalar() or 0

    return ConsumerMigrationPosture(
        workspace_id=str(workspace.id),
        runtime_status={
            "live_data_plane": "runledger-gateway-rs",
            "live_data_plane_port": 8210,
            "live_endpoint": "/gateway/chat/completions",
            "control_plane": "runledger-api",
            "control_plane_port": 8000,
            "active_routes": active_routes,
            "total_routes": total_routes,
            "distinct_providers": distinct_providers,
        },
        legacy_deprecation={
            "python_completion_stub": "410_gone",
            "python_completion_route": "/gateway/chat/completions",
            "router_sidecar": "deprecated",
            "router_sidecar_profile": "deprecated",
            "env_vars_migrated": ["ROUTER_SVC_URL", "GATEWAY_RS_URL"],
        },
        consumer_assets={
            "api_keys": api_keys,
            "docs_migrated": True,
            "postman_migrated": True,
            "examples_migrated": True,
            "benchmark_migrated": True,
            "migration_guide": "examples/163_consumer_migration_guide.py",
        },
        observe_context={
            "requests_7d": requests_7d,
            "requests_30d": requests_30d,
            "cache_hits_7d": cache_hits_7d,
            "audit_events_30d": audit_events_30d,
        },
    )


@router.get(
    "/runtime-scope-model-posture",
    response_model=RuntimeScopeModelPosture,
)
async def runtime_scope_model_posture(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _user: TenantUser = Depends(get_current_user),
    _rl: None = Depends(analytics_rate_limit),
):
    from runledger_api.models.gateway import GatewayRequest

    ws = workspace.id
    now = datetime.now(UTC)
    thirty_days_ago = now - timedelta(days=30)

    access_groups = (
        await db.execute(
            select(func.count(AccessGroup.id)).where(
                AccessGroup.workspace_id == ws,
                AccessGroup.is_active.is_(True),
            )
        )
    ).scalar() or 0

    access_group_members = (
        await db.execute(
            select(func.count(AccessGroupMember.id)).where(
                AccessGroupMember.group_id.in_(
                    select(AccessGroup.id).where(AccessGroup.workspace_id == ws)
                )
            )
        )
    ).scalar() or 0

    groups_with_budget = (
        await db.execute(
            select(func.count(AccessGroup.id)).where(
                AccessGroup.workspace_id == ws,
                AccessGroup.is_active.is_(True),
                AccessGroup.budget_usd.isnot(None),
            )
        )
    ).scalar() or 0

    groups_with_guardrails = (
        await db.execute(
            select(func.count(AccessGroup.id)).where(
                AccessGroup.workspace_id == ws,
                AccessGroup.is_active.is_(True),
                AccessGroup.guardrail_profile.isnot(None),
            )
        )
    ).scalar() or 0

    api_keys = (
        await db.execute(
            select(func.count(ApiKey.id)).where(
                ApiKey.workspace_id == ws,
            )
        )
    ).scalar() or 0

    total_tool_policies = (
        await db.execute(
            select(func.count(ToolPolicy.id)).where(
                ToolPolicy.workspace_id == ws,
            )
        )
    ).scalar() or 0

    active_tool_policies = (
        await db.execute(
            select(func.count(ToolPolicy.id)).where(
                ToolPolicy.workspace_id == ws,
                ToolPolicy.is_active.is_(True),
            )
        )
    ).scalar() or 0

    workspace_scoped_policies = (
        await db.execute(
            select(func.count(ToolPolicy.id)).where(
                ToolPolicy.workspace_id == ws,
                ToolPolicy.is_active.is_(True),
                ToolPolicy.scope_type == "workspace",
            )
        )
    ).scalar() or 0

    access_group_scoped_policies = (
        await db.execute(
            select(func.count(ToolPolicy.id)).where(
                ToolPolicy.workspace_id == ws,
                ToolPolicy.is_active.is_(True),
                ToolPolicy.scope_type == "access_group",
            )
        )
    ).scalar() or 0

    guardrail_rules = (
        await db.execute(
            select(func.count(GuardrailRule.id)).where(
                GuardrailRule.workspace_id == ws,
                GuardrailRule.status == "active",
            )
        )
    ).scalar() or 0

    guardrail_events_30d = (
        await db.execute(
            select(func.count(GuardrailEvent.id)).where(
                GuardrailEvent.workspace_id == ws,
                GuardrailEvent.created_at >= thirty_days_ago,
            )
        )
    ).scalar() or 0

    active_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == ws,
                GatewayRoute.is_active.is_(True),
            )
        )
    ).scalar() or 0

    requests_30d = (
        await db.execute(
            select(func.count(GatewayRequest.id)).where(
                GatewayRequest.workspace_id == ws,
                GatewayRequest.created_at >= thirty_days_ago,
            )
        )
    ).scalar() or 0

    audit_events_30d = (
        await db.execute(
            select(func.count(AuditEvent.id)).where(
                AuditEvent.workspace_id == ws,
                AuditEvent.created_at >= thirty_days_ago,
            )
        )
    ).scalar() or 0

    return RuntimeScopeModelPosture(
        workspace_id=str(ws),
        identity_model={
            "workspace_id": str(ws),
            "access_groups": access_groups,
            "access_group_members": access_group_members,
            "groups_with_budget": groups_with_budget,
            "groups_with_guardrails": groups_with_guardrails,
            "api_keys": api_keys,
            "scope_types": ["workspace", "access_group", "group", "search_tool"],
        },
        policy_enforcement={
            "total_tool_policies": total_tool_policies,
            "active_tool_policies": active_tool_policies,
            "workspace_scoped_policies": workspace_scoped_policies,
            "access_group_scoped_policies": access_group_scoped_policies,
            "guardrail_rules": guardrail_rules,
            "guardrail_events_30d": guardrail_events_30d,
            "policy_actions": ["allow", "audit", "block", "require_approval", "deny"],
        },
        scope_propagation={
            "rust_data_plane": "runledger-gateway-rs:8210",
            "python_control_plane": "runledger-api:8000",
            "preflight_scope_inputs": ["workspace_id", "api_key_id", "access_group_id", "org_id"],
            "enforcement_points": ["gateway_preflight", "guardrails", "tool_policy_eval", "budget_check"],
            "active_routes": active_routes,
        },
        observe_context={
            "requests_30d": requests_30d,
            "guardrail_events_30d": guardrail_events_30d,
            "audit_events_30d": audit_events_30d,
        },
    )


@router.get(
    "/scope-enforcement-evidence-posture",
    response_model=ScopeEnforcementEvidencePosture,
)
async def scope_enforcement_evidence_posture(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _user: TenantUser = Depends(get_current_user),
    _rl: None = Depends(analytics_rate_limit),
):
    from runledger_api.models.gateway import GatewayRequest

    ws = workspace.id
    now = datetime.now(UTC)
    thirty_days_ago = now - timedelta(days=30)

    guardrail_events_30d = (
        await db.execute(
            select(func.count(GuardrailEvent.id)).where(
                GuardrailEvent.workspace_id == ws,
                GuardrailEvent.created_at >= thirty_days_ago,
            )
        )
    ).scalar() or 0

    blocked_events_30d = (
        await db.execute(
            select(func.count(GuardrailEvent.id)).where(
                GuardrailEvent.workspace_id == ws,
                GuardrailEvent.created_at >= thirty_days_ago,
                GuardrailEvent.decision == "block",
            )
        )
    ).scalar() or 0

    allowed_events_30d = (
        await db.execute(
            select(func.count(GuardrailEvent.id)).where(
                GuardrailEvent.workspace_id == ws,
                GuardrailEvent.created_at >= thirty_days_ago,
                GuardrailEvent.decision == "allow",
            )
        )
    ).scalar() or 0

    modified_events_30d = (
        await db.execute(
            select(func.count(GuardrailEvent.id)).where(
                GuardrailEvent.workspace_id == ws,
                GuardrailEvent.created_at >= thirty_days_ago,
                GuardrailEvent.decision == "modify",
            )
        )
    ).scalar() or 0

    false_positives_30d = (
        await db.execute(
            select(func.count(GuardrailEvent.id)).where(
                GuardrailEvent.workspace_id == ws,
                GuardrailEvent.created_at >= thirty_days_ago,
                GuardrailEvent.is_false_positive.is_(True),
            )
        )
    ).scalar() or 0

    distinct_rules_triggered = (
        await db.execute(
            select(func.count(sa.distinct(GuardrailEvent.guardrail_rule_id))).where(
                GuardrailEvent.workspace_id == ws,
                GuardrailEvent.created_at >= thirty_days_ago,
            )
        )
    ).scalar() or 0

    active_guardrail_rules = (
        await db.execute(
            select(func.count(GuardrailRule.id)).where(
                GuardrailRule.workspace_id == ws,
                GuardrailRule.status == "active",
            )
        )
    ).scalar() or 0

    total_tool_policies = (
        await db.execute(
            select(func.count(ToolPolicy.id)).where(
                ToolPolicy.workspace_id == ws,
                ToolPolicy.is_active.is_(True),
            )
        )
    ).scalar() or 0

    workspace_scoped = (
        await db.execute(
            select(func.count(ToolPolicy.id)).where(
                ToolPolicy.workspace_id == ws,
                ToolPolicy.is_active.is_(True),
                ToolPolicy.scope_type == "workspace",
            )
        )
    ).scalar() or 0

    group_scoped = (
        await db.execute(
            select(func.count(ToolPolicy.id)).where(
                ToolPolicy.workspace_id == ws,
                ToolPolicy.is_active.is_(True),
                ToolPolicy.scope_type == "access_group",
            )
        )
    ).scalar() or 0

    access_groups = (
        await db.execute(
            select(func.count(AccessGroup.id)).where(
                AccessGroup.workspace_id == ws,
                AccessGroup.is_active.is_(True),
            )
        )
    ).scalar() or 0

    groups_with_guardrails = (
        await db.execute(
            select(func.count(AccessGroup.id)).where(
                AccessGroup.workspace_id == ws,
                AccessGroup.is_active.is_(True),
                AccessGroup.guardrail_profile.isnot(None),
            )
        )
    ).scalar() or 0

    requests_30d = (
        await db.execute(
            select(func.count(GatewayRequest.id)).where(
                GatewayRequest.workspace_id == ws,
                GatewayRequest.created_at >= thirty_days_ago,
            )
        )
    ).scalar() or 0

    audit_events_30d = (
        await db.execute(
            select(func.count(AuditEvent.id)).where(
                AuditEvent.workspace_id == ws,
                AuditEvent.created_at >= thirty_days_ago,
            )
        )
    ).scalar() or 0

    api_keys = (
        await db.execute(
            select(func.count(ApiKey.id)).where(
                ApiKey.workspace_id == ws,
            )
        )
    ).scalar() or 0

    return ScopeEnforcementEvidencePosture(
        workspace_id=str(ws),
        period_days=30,
        enforcement_summary={
            "guardrail_events_30d": guardrail_events_30d,
            "blocked_30d": blocked_events_30d,
            "allowed_30d": allowed_events_30d,
            "modified_30d": modified_events_30d,
            "false_positives_30d": false_positives_30d,
            "distinct_rules_triggered": distinct_rules_triggered,
            "active_guardrail_rules": active_guardrail_rules,
        },
        scope_friction={
            "total_tool_policies": total_tool_policies,
            "workspace_scoped": workspace_scoped,
            "access_group_scoped": group_scoped,
            "access_groups": access_groups,
            "groups_with_guardrails": groups_with_guardrails,
            "block_rate_pct": round(blocked_events_30d / guardrail_events_30d * 100, 1) if guardrail_events_30d else 0.0,
            "false_positive_rate_pct": round(false_positives_30d / guardrail_events_30d * 100, 1) if guardrail_events_30d else 0.0,
        },
        violation_lineage={
            "scope_inputs": ["workspace_id", "api_key_id", "access_group_id", "org_id"],
            "enforcement_points": ["gateway_preflight", "guardrails", "tool_policy_eval", "budget_check"],
            "decision_outcomes": ["allow", "block", "modify", "audit", "require_approval", "deny"],
            "evidence_fields": ["guardrail_name", "decision", "reason", "model", "user_id", "latency_ms"],
        },
        evidence_loop={
            "requests_30d": requests_30d,
            "audit_events_30d": audit_events_30d,
            "api_keys": api_keys,
            "observe_surfaces": ["guardrail_events", "audit_events", "gateway_requests"],
            "governance_surfaces": ["tool_policies", "guardrail_rules", "access_groups"],
        },
    )


@router.get(
    "/pipeline-studio-posture",
    response_model=PipelineStudioPosture,
)
async def pipeline_studio_posture(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _user: TenantUser = Depends(get_current_user),
    _rl: None = Depends(analytics_rate_limit),
):
    from runledger_api.models.gateway import GatewayRequest

    ws = workspace.id
    now = datetime.now(UTC)
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    active_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == ws,
                GatewayRoute.is_active.is_(True),
            )
        )
    ).scalar() or 0

    distinct_providers = (
        await db.execute(
            select(func.count(sa.distinct(GatewayRoute.provider))).where(
                GatewayRoute.workspace_id == ws,
                GatewayRoute.is_active.is_(True),
            )
        )
    ).scalar() or 0

    routing_groups = (
        await db.execute(
            select(func.count(RoutingGroup.id)).where(
                RoutingGroup.workspace_id == ws,
            )
        )
    ).scalar() or 0

    routing_policies = (
        await db.execute(
            select(func.count(RoutingPolicy.id)).where(
                RoutingPolicy.workspace_id == ws,
            )
        )
    ).scalar() or 0

    requests_7d = (
        await db.execute(
            select(func.count(GatewayRequest.id)).where(
                GatewayRequest.workspace_id == ws,
                GatewayRequest.created_at >= seven_days_ago,
            )
        )
    ).scalar() or 0

    requests_30d = (
        await db.execute(
            select(func.count(GatewayRequest.id)).where(
                GatewayRequest.workspace_id == ws,
                GatewayRequest.created_at >= thirty_days_ago,
            )
        )
    ).scalar() or 0

    cache_hits_7d = (
        await db.execute(
            select(func.count(GatewayRequest.id)).where(
                GatewayRequest.workspace_id == ws,
                GatewayRequest.created_at >= seven_days_ago,
                GatewayRequest.status == "cache_hit",
            )
        )
    ).scalar() or 0

    guardrail_rules = (
        await db.execute(
            select(func.count(GuardrailRule.id)).where(
                GuardrailRule.workspace_id == ws,
                GuardrailRule.status == "active",
            )
        )
    ).scalar() or 0

    guardrail_events_30d = (
        await db.execute(
            select(func.count(GuardrailEvent.id)).where(
                GuardrailEvent.workspace_id == ws,
                GuardrailEvent.created_at >= thirty_days_ago,
            )
        )
    ).scalar() or 0

    blocked_events_30d = (
        await db.execute(
            select(func.count(GuardrailEvent.id)).where(
                GuardrailEvent.workspace_id == ws,
                GuardrailEvent.created_at >= thirty_days_ago,
                GuardrailEvent.decision == "block",
            )
        )
    ).scalar() or 0

    tool_policies = (
        await db.execute(
            select(func.count(ToolPolicy.id)).where(
                ToolPolicy.workspace_id == ws,
                ToolPolicy.is_active.is_(True),
            )
        )
    ).scalar() or 0

    budget_count = (
        await db.execute(
            select(func.count(Budget.id)).where(
                Budget.workspace_id == ws,
            )
        )
    ).scalar() or 0

    agents = (
        await db.execute(
            select(func.count(Agent.id)).where(
                Agent.workspace_id == ws,
            )
        )
    ).scalar() or 0

    workflows = (
        await db.execute(
            select(func.count(WorkflowDefinition.id)).where(
                WorkflowDefinition.workspace_id == ws,
            )
        )
    ).scalar() or 0

    audit_events_30d = (
        await db.execute(
            select(func.count(AuditEvent.id)).where(
                AuditEvent.workspace_id == ws,
                AuditEvent.created_at >= thirty_days_ago,
            )
        )
    ).scalar() or 0

    return PipelineStudioPosture(
        workspace_id=str(ws),
        pipeline_model={
            "stages": ["ingest", "routing", "enforcement", "execution", "reporting"],
            "ingest_sources": ["api_keys", "sdk", "otlp"],
            "routing_nodes": {
                "active_routes": active_routes,
                "distinct_providers": distinct_providers,
                "routing_groups": routing_groups,
                "routing_policies": routing_policies,
            },
            "execution_runtime": {
                "data_plane": "runledger-gateway-rs:8210",
                "control_plane": "runledger-api:8000",
            },
        },
        traffic_overlay={
            "requests_7d": requests_7d,
            "requests_30d": requests_30d,
            "cache_hits_7d": cache_hits_7d,
            "audit_events_30d": audit_events_30d,
        },
        enforcement_overlay={
            "guardrail_rules": guardrail_rules,
            "guardrail_events_30d": guardrail_events_30d,
            "blocked_events_30d": blocked_events_30d,
            "tool_policies": tool_policies,
            "enforcement_points": ["gateway_preflight", "guardrails", "tool_policy_eval", "budget_check"],
        },
        finops_overlay={
            "budgets": budget_count,
            "cost_tracking": "per_request",
            "budget_enforcement": "preflight",
        },
        build_overlay={
            "agents": agents,
            "workflows": workflows,
            "pipeline_participants": ["agents", "workflows", "evaluations", "prompts"],
        },
    )


@router.get(
    "/api-explorer-posture",
    response_model=ApiExplorerPosture,
)
async def api_explorer_posture(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _user: TenantUser = Depends(get_current_user),
    _rl: None = Depends(analytics_rate_limit),
):
    from runledger_api.models.gateway import GatewayRequest

    ws = workspace.id
    now = datetime.now(UTC)
    thirty_days_ago = now - timedelta(days=30)

    active_routes = (
        await db.execute(
            select(func.count(GatewayRoute.id)).where(
                GatewayRoute.workspace_id == ws,
                GatewayRoute.is_active.is_(True),
            )
        )
    ).scalar() or 0

    api_keys = (
        await db.execute(
            select(func.count(ApiKey.id)).where(
                ApiKey.workspace_id == ws,
            )
        )
    ).scalar() or 0

    requests_30d = (
        await db.execute(
            select(func.count(GatewayRequest.id)).where(
                GatewayRequest.workspace_id == ws,
                GatewayRequest.created_at >= thirty_days_ago,
            )
        )
    ).scalar() or 0

    audit_events_30d = (
        await db.execute(
            select(func.count(AuditEvent.id)).where(
                AuditEvent.workspace_id == ws,
                AuditEvent.created_at >= thirty_days_ago,
            )
        )
    ).scalar() or 0

    return ApiExplorerPosture(
        workspace_id=str(ws),
        openapi_surface={
            "spec_url": "/openapi.json",
            "reference_ui": "/reference",
            "spec_format": "OpenAPI 3.1",
            "generated": True,
            "source_of_truth": "FastAPI auto-generated from route decorators",
        },
        endpoint_ownership={
            "control_plane": {
                "host": "runledger-api:8000",
                "families": ["org", "gateway_routing", "gateway_runtime", "budgets", "analytics", "settings", "governance", "evaluations", "agents", "workflows", "prompts"],
            },
            "data_plane": {
                "host": "runledger-gateway-rs:8210",
                "families": ["chat_completions", "streaming", "passthrough"],
            },
            "observability": {
                "host": "runledger-api:8000",
                "families": ["analytics", "monitoring", "audit", "runs", "sessions", "request_explorer"],
            },
            "admin": {
                "host": "runledger-api:8000",
                "families": ["admin", "bootstrap", "platform_settings", "scim"],
            },
        },
        sdk_support={
            "languages": ["python", "typescript", "curl"],
            "auth_model": "Bearer token (API key or session key)",
            "api_keys": api_keys,
            "active_routes": active_routes,
        },
        observe_context={
            "requests_30d": requests_30d,
            "audit_events_30d": audit_events_30d,
        },
    )


@router.get(
    "/design-system-posture",
    response_model=DesignSystemPosture,
)
async def design_system_posture(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _user: TenantUser = Depends(get_current_user),
    _rl: None = Depends(analytics_rate_limit),
):
    ws = workspace.id

    scope_types_q = (
        await db.execute(
            select(AccessGroup.id).where(AccessGroup.workspace_id == ws)
        )
    ).scalars().all()
    access_group_count = len(scope_types_q)

    api_key_count = (
        await db.execute(
            select(func.count(ApiKey.id)).where(ApiKey.workspace_id == ws)
        )
    ).scalar() or 0

    return DesignSystemPosture(
        workspace_id=str(ws),
        token_system={
            "categories": ["color", "spacing", "typography", "elevation", "radius", "chart"],
            "color_tokens": 22,
            "spacing_scale": "tailwind-default (0.25rem base)",
            "typography_stacks": ["sans (Inter/Segoe UI)", "display (Plus Jakarta Sans)", "mono (JetBrains Mono)"],
            "elevation_levels": 3,
            "radius_default": "0.75rem",
            "chart_palette_size": 5,
        },
        dark_mode={
            "strategy": "class-based (.dark on html)",
            "palette": "light-gray-blue (Windows-like, both modes)",
            "legacy_overrides": True,
            "legacy_override_reason": "Old dark:* utilities softened globally until full migration to semantic tokens",
            "contrast_ratio_target": "WCAG AA (4.5:1 text, 3:1 UI)",
        },
        scope_visual_language={
            "scope_levels": ["platform", "organization", "workspace", "access_group", "api_key"],
            "scope_colors": {
                "platform": "slate",
                "organization": "blue",
                "workspace": "indigo",
                "access_group": "violet",
                "api_key": "amber",
            },
            "access_groups": access_group_count,
            "api_keys": api_key_count,
        },
        layout_shells={
            "shells": ["platform_admin", "org_admin", "gateway_admin", "observability", "build"],
            "sidebar_pattern": "collapsible icon+label navigation",
            "content_max_width": "1600px",
            "responsive_breakpoints": ["sm:640px", "md:768px", "lg:1024px", "xl:1280px", "2xl:1536px"],
        },
        density_modes={
            "available": ["default", "compact"],
            "compact_surfaces": ["runs_table", "request_explorer", "audit_log", "sessions_table"],
            "default_row_height": "48px",
            "compact_row_height": "36px",
        },
        status_semantics={
            "operational_states": {
                "success": "emerald",
                "warning": "amber",
                "error": "red",
                "info": "blue",
                "neutral": "slate",
            },
            "severity_levels": ["low", "medium", "high", "critical"],
            "severity_colors": {
                "low": "slate",
                "medium": "amber",
                "high": "orange",
                "critical": "red",
            },
            "runtime_states": {
                "active": "emerald",
                "degraded": "amber",
                "down": "red",
                "maintenance": "blue",
            },
        },
    )
