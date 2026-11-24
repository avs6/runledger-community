"""Pydantic schemas for the agent registry, workflows and agent memory."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

AgentType = Literal["autonomous", "semi_autonomous", "workflow", "chat"]
AgentStatus = Literal["active", "paused", "retired"]


# ── Agent Registry ──────────────────────────────────────────────────────────


class AgentCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: str | None = Field(None, max_length=2000)
    agent_type: AgentType = "autonomous"
    owner: str | None = Field(None, max_length=200)
    default_model: str | None = Field(None, max_length=200)
    default_tools: list[str] = Field(default_factory=list)
    budget_envelope: Decimal | None = Field(None, ge=0)
    allowed_aliases: list[Annotated[str, Field(min_length=1, max_length=200)]] = Field(
        default_factory=list,
        max_length=50,
        description="Gateway route aliases the agent may call (empty = any). Enforced "
        "by the gateway preflight and the SDK.",
    )
    status: AgentStatus = "active"
    config: dict[str, Any] = Field(default_factory=dict)


class AgentUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    description: str | None = Field(None, max_length=2000)
    agent_type: AgentType | None = None
    owner: str | None = Field(None, max_length=200)
    default_model: str | None = Field(None, max_length=200)
    default_tools: list[str] | None = None
    budget_envelope: Decimal | None = Field(None, ge=0)
    allowed_aliases: list[Annotated[str, Field(min_length=1, max_length=200)]] | None = Field(
        None, max_length=50
    )
    status: AgentStatus | None = None
    config: dict[str, Any] | None = None


class AgentResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str | None = None
    agent_type: str
    owner: str | None = None
    default_model: str | None = None
    default_tools: list[str]
    budget_envelope: Decimal | None = None
    allowed_aliases: list[str] = Field(default_factory=list)
    status: str
    config: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class AgentListResponse(BaseModel):
    agents: list[AgentResponse]
    total: int


class AgentStats(BaseModel):
    """Agent cost/performance from the runs attributed to it (``agent_runs.agent_id``)."""

    agent_id: uuid.UUID
    window_days: int | None = None
    total_runs: int = 0
    completed_runs: int = 0
    failed_runs: int = 0
    total_cost: Decimal = Decimal("0")
    total_tokens: int = 0
    avg_duration_ms: float | None = None
    success_rate: float | None = None
    last_run_at: datetime | None = None
    models_used: list[str] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    envelope: AgentEnvelopeStatus | None = None


class AgentEnvelopeStatus(BaseModel):
    """The agent preflight: status, alias allow-list and monthly budget envelope.

    ``allowed`` is false when the agent is paused/retired, the alias isn't allowed, or
    the month's attributed spend has reached ``budget_envelope``. The gateway refuses
    such requests (403 / 429) and the SDK refuses to start the run.
    """

    agent_id: uuid.UUID
    reason_code: Literal["agent_inactive", "alias_not_allowed", "envelope_exhausted"] | None = None
    allowed_aliases: list[str] = Field(default_factory=list)
    envelope_usd: Decimal | None = None
    spent_usd: Decimal = Decimal("0")
    remaining_usd: Decimal | None = None
    period_start: datetime
    allowed: bool = True
    reason: str | None = None


# ── Workflow Definitions ────────────────────────────────────────────────────

# Same alphabet the gateway and SDK accept for tags (no spaces).
FEATURE_TAG_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,254}$"


class WorkflowDefinitionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(None, max_length=2000)
    feature_tag: str | None = Field(
        None,
        pattern=FEATURE_TAG_PATTERN,
        description="Runs with this feature_tag are attributed to the workflow; "
        "budgets on this tag are the workflow's budgets. Unique per workspace.",
    )
    gateway_alias: str | None = Field(
        None,
        max_length=200,
        description="Gateway route alias whose traffic belongs to this workflow.",
    )
    owner: str | None = Field(None, max_length=200)
    steps_schema: list[dict[str, Any]] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)


class WorkflowDefinitionUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=2000)
    feature_tag: str | None = Field(None, pattern=FEATURE_TAG_PATTERN)
    gateway_alias: str | None = Field(None, max_length=200)
    owner: str | None = Field(None, max_length=200)
    steps_schema: list[dict[str, Any]] | None = None
    status: Literal["active", "archived"] | None = None
    config: dict[str, Any] | None = None


class WorkflowStats(BaseModel):
    window_days: int
    runs: int = 0
    succeeded: int = 0
    failed: int = 0
    success_rate: float | None = None
    total_cost_usd: Decimal = Decimal("0")
    cost_per_success: Decimal | None = None
    p95_latency_ms: float | None = None
    last_run_at: datetime | None = None


class WorkflowDefinitionResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str | None = None
    feature_tag: str | None = None
    gateway_alias: str | None = None
    owner: str | None = None
    steps_schema: list[dict[str, Any]]
    status: str
    config: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    stats: WorkflowStats | None = None
    # Set on create/update when existing unattributed runs were linked.
    linked_runs: int | None = None


class WorkflowDefinitionListResponse(BaseModel):
    workflows: list[WorkflowDefinitionResponse]
    total: int


# ── Workflow runs (a view over agent_runs) ──────────────────────────────────


class RunSummary(BaseModel):
    """One run (``agent_runs`` row) as listed under a workflow or an agent."""

    id: uuid.UUID
    workflow_id: uuid.UUID | None = None
    agent_id: uuid.UUID | None = None
    status: str
    feature_tag: str | None = None
    end_user_id: str | None = None
    api_key_id: uuid.UUID | None = None
    source_type: str | None = None
    total_cost_usd: Decimal = Decimal("0")
    total_tokens: int = 0
    duration_ms: int | None = None
    started_at: datetime
    ended_at: datetime | None = None


class RunSummaryListResponse(BaseModel):
    runs: list[RunSummary]
    total: int


# ── Cost attribution / health ───────────────────────────────────────────────


class StepCostBreakdown(BaseModel):
    """Cost of one step (span name) across the workflow's runs, from provider calls."""

    step_name: str
    step_type: str
    total_cost: Decimal
    avg_cost: Decimal
    invocation_count: int
    total_tokens: int = 0


class ModelCostBreakdown(BaseModel):
    provider: str
    model: str
    calls: int
    total_cost: Decimal
    total_tokens: int


class WorkflowCostAttribution(BaseModel):
    workflow_id: uuid.UUID
    workflow_name: str
    window_days: int
    total_runs: int
    total_cost: Decimal
    avg_cost_per_run: Decimal
    # Sum of step (provider-call) costs; equals total_cost once metering has priced
    # every call, so steps and runs never disagree (B-18).
    steps_cost: Decimal = Decimal("0")
    cost_by_step: list[StepCostBreakdown]
    cost_by_model: list[ModelCostBreakdown] = Field(default_factory=list)


class TrendPoint(BaseModel):
    day: str
    runs: int = 0
    cost_usd: Decimal = Decimal("0")
    avg_score: float | None = None
    scores: int = 0


class WorkflowHealth(BaseModel):
    """The workflow health card: unit economics joined to quality."""

    window_days: int
    runs: int = 0
    succeeded: int = 0
    failed: int = 0
    success_rate: float | None = None
    total_cost_usd: Decimal = Decimal("0")
    cost_per_success: Decimal | None = None
    p50_latency_ms: float | None = None
    p95_latency_ms: float | None = None
    avg_eval_score: float | None = None
    # Change in average eval score, last half of the window vs the first half.
    eval_score_delta: float | None = None
    trend: list[TrendPoint] = Field(default_factory=list)


class WorkflowBudget(BaseModel):
    id: uuid.UUID
    scope_type: str
    scope_id: str | None = None
    period_type: str
    limit_usd: Decimal
    action: str
    # This workflow's attributed spend in the budget's current period.
    spent_usd: Decimal = Decimal("0")


class WorkflowEval(BaseModel):
    name: str
    avg_score: float
    count: int


class WorkflowPolicy(BaseModel):
    kind: str
    name: str
    detail: str
    href: str | None = None


class WorkflowAgentUsage(BaseModel):
    id: uuid.UUID
    name: str
    runs: int
    total_cost_usd: Decimal


class WorkflowOverview(BaseModel):
    """Everything the Workflow page shows: runs + cost + budgets + evals + policies."""

    workflow: WorkflowDefinitionResponse
    health: WorkflowHealth
    budgets: list[WorkflowBudget] = Field(default_factory=list)
    evals: list[WorkflowEval] = Field(default_factory=list)
    policies: list[WorkflowPolicy] = Field(default_factory=list)
    agents: list[WorkflowAgentUsage] = Field(default_factory=list)


AgentStats.model_rebuild()


# ── Agent Memory ────────────────────────────────────────────────────────────

MemoryType = Literal["short_term", "long_term", "shared"]


class AgentMemoryCreate(BaseModel):
    key: str = Field(..., max_length=500)
    value: str = Field(..., max_length=100_000)
    memory_type: MemoryType = "long_term"
    metadata: dict[str, Any] = Field(default_factory=dict)
    retention_days: int | None = Field(None, ge=1, le=3650)
    # Overwrite an existing key instead of returning 409 (review B-16).
    upsert: bool = False


class AgentMemoryUpdate(BaseModel):
    value: str | None = Field(None, max_length=100_000)
    memory_type: MemoryType | None = None
    metadata: dict[str, Any] | None = None
    retention_days: int | None = Field(None, ge=1, le=3650)


class AgentMemoryResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    agent_id: uuid.UUID
    key: str
    value: str
    memory_type: str
    metadata: dict[str, Any]
    size_bytes: int
    access_count: int
    has_pii: bool
    retention_days: int | None = None
    expires_at: datetime | None = None
    last_accessed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AgentMemoryListResponse(BaseModel):
    memories: list[AgentMemoryResponse]
    total: int


class AgentMemorySearchRequest(BaseModel):
    query: str = Field(..., max_length=1000)
    memory_type: MemoryType | None = None
    limit: int = Field(20, ge=1, le=100)


class AgentMemoryStats(BaseModel):
    agent_id: uuid.UUID
    total_memories: int = 0
    total_size_bytes: int = 0
    by_type: dict[str, int] = Field(default_factory=dict)
    pii_count: int = 0
    expired_count: int = 0
    most_accessed: list[AgentMemoryResponse] = Field(default_factory=list)


class AgentMemoryAuditResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    agent_id: uuid.UUID
    memory_id: uuid.UUID | None = None
    action: str
    key: str | None = None
    details: dict[str, Any]
    actor: str | None = None
    created_at: datetime


class AgentMemoryAuditListResponse(BaseModel):
    events: list[AgentMemoryAuditResponse]
    total: int
