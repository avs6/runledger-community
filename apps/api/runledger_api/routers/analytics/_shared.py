"""Shared imports, router and helpers for the analytics routes (split from analytics.py)."""

from __future__ import annotations

import csv
import io
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any

import sqlalchemy as sa
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi import status as http_status
from fastapi.responses import StreamingResponse
from sqlalchemy import String, case, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import (
    get_current_user,
    get_current_workspace,
    require_workspace_writer,
)
from runledger_api.core.pagination import PageDep, paginate, paginate_list
from runledger_api.core.ratelimit import analytics_rate_limit
from runledger_api.models.access_groups import AccessGroup, AccessGroupMember
from runledger_api.models.annotations import Annotation
from runledger_api.models.billing import BillingPeriod, ChargebackRule
from runledger_api.models.events import AgentRun, ProviderCall, Span, ToolCall
from runledger_api.models.ledger import SecurityEvent
from runledger_api.models.metering import UsageDaily
from runledger_api.models.replay import UserAnomaly
from runledger_api.models.scores import ScoreEvent
from runledger_api.models.tenant import ApiKey, TenantUser, Workspace
from runledger_api.schemas.analytics import (
    AnalyticsSummary,
    AnomalyItem,
    AnomalyList,
    CohortList,
    CohortSummary,
    CostByDimension,
    EngineeringMetrics,
    FeatureSpend,
    IntentCount,
    LifecycleStage,
    ModelBudgetUtilization,
    ModelScorecard,
    ModelScorecardList,
    ModelSpend,
    OptimizationOpportunitiesResponse,
    OptimizationOpportunity,
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
    TrendMetric,
    TrendPoint,
    TrendsResponse,
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
from runledger_api.services.billable import billable_cost_sum
from runledger_api.services.observe import (
    AccessGroupFilters,
    resolve_access_group,
    resolve_scope_workspace_ids,
)

# Provider calls carry no tool reference: spend "on tools" is the model spend of runs
# that made at least one tool call.

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
) -> AccessGroupFilters:
    """Access-group dashboard filters (shared with runs and sessions: services.observe)."""
    filters = await resolve_access_group(db, workspace_id, access_group_id)
    assert filters is not None
    return filters


def _successful_run_filter(
    workspace_id: uuid.UUID, period_from: datetime, period_to: datetime
) -> list[Any]:
    return [
        AgentRun.workspace_id == workspace_id,
        AgentRun.started_at >= period_from,
        AgentRun.started_at < period_to,
        AgentRun.status == "succeeded",
    ]


# ── /analytics/users/cohorts ─────────────────────────────────────────────────


_DEFAULT_COHORT_DAYS = 30


# ── /analytics/regressions ────────────────────────────────────────────────────

_REGRESSION_THRESHOLD = Decimal("0.20")
_REGRESSION_MIN_RUNS = 3


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


# ── /analytics/scores/summary ─────────────────────────────────────────────────

_SCORE_REGRESSION_THRESHOLD = Decimal("0.20")
_SCORE_REGRESSION_MIN_SAMPLES = 3


# ── Phase 3: Scoped scope helpers ────────────────────────────────────────────


async def _resolve_scoped_workspace_ids(
    scope: str,
    workspace: Workspace,
    user: Any,
    db: AsyncSession,
) -> list[uuid.UUID]:
    """One scope rule for every Observe endpoint (org admins/managers for org scope)."""
    return await resolve_scope_workspace_ids(scope, workspace, user, db)


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


__all__ = [
    "APIRouter",
    "AccessGroup",
    "AccessGroupMember",
    "AgentRun",
    "AnalyticsSummary",
    "Annotated",
    "Annotation",
    "AnnotationCreate",
    "AnnotationList",
    "AnnotationResponse",
    "AnomalyItem",
    "AnomalyList",
    "Any",
    "ApiKey",
    "AsyncSession",
    "BestValueModel",
    "BestValueResponse",
    "BillingPeriod",
    "ChargebackRule",
    "CohortList",
    "CohortSummary",
    "CostByDimension",
    "CostQualityPoint",
    "CostQualityResponse",
    "Decimal",
    "Depends",
    "EngineeringMetrics",
    "FeatureSpend",
    "HTTPException",
    "IntentCount",
    "LifecycleStage",
    "MODEL_COST_RATIOS",
    "MODEL_LATENCY_MS",
    "ModelBudgetUtilization",
    "ModelCost",
    "ModelScorecard",
    "ModelScorecardList",
    "ModelSpend",
    "OptimizationOpportunitiesResponse",
    "OptimizationOpportunity",
    "PageDep",
    "ProviderCall",
    "QUALITY_RISK_MAP",
    "QualityFunnel",
    "Query",
    "RegressionItem",
    "RegressionList",
    "RequestExplorerResponse",
    "RequestRecord",
    "Response",
    "RunEconomics",
    "SavingsByCategory",
    "SavingsResponse",
    "SavingsTimeline",
    "ScopedSummary",
    "ScoreEvent",
    "ScoreRegressionItem",
    "ScoreSummary",
    "ScoreSummaryItem",
    "SecurityEvent",
    "SimulationImpact",
    "SimulationRequest",
    "SimulationResult",
    "Span",
    "SpanTypeCost",
    "SpanTypeDelta",
    "SpendByFeature",
    "SpendByModel",
    "SpendByUser",
    "SpendOverTime",
    "SpendPoint",
    "StreamingResponse",
    "String",
    "TenantUser",
    "ToolCall",
    "TrendMetric",
    "TrendPoint",
    "TrendsResponse",
    "UTC",
    "UsageDaily",
    "UserAnomaly",
    "UserSpend",
    "UserSpendDetail",
    "VersionCompareResult",
    "VersionSummary",
    "WorkflowSummary",
    "WorkflowTopList",
    "Workspace",
    "_DEFAULT_COHORT_DAYS",
    "_DEFAULT_LOOKBACK_DAYS",
    "_EXPORT_COLUMNS",
    "_REGRESSION_MIN_RUNS",
    "_REGRESSION_THRESHOLD",
    "_SCORE_REGRESSION_MIN_SAMPLES",
    "_SCORE_REGRESSION_THRESHOLD",
    "_default_from",
    "_default_to",
    "_match_model_key",
    "_parse_dt",
    "_resolve_access_group_observe_filters",
    "_resolve_scoped_workspace_ids",
    "_successful_run_filter",
    "analytics_rate_limit",
    "billable_cost_sum",
    "case",
    "cast",
    "csv",
    "datetime",
    "func",
    "get_current_user",
    "get_current_workspace",
    "get_db",
    "http_status",
    "io",
    "log",
    "or_",
    "paginate",
    "paginate_list",
    "require_workspace_writer",
    "router",
    "sa",
    "select",
    "structlog",
    "timedelta",
    "uuid",
]
