"""Pydantic schemas for agent registry and workflow run tracking."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field

AgentType = Literal["autonomous", "semi_autonomous", "workflow", "chat"]
AgentStatus = Literal["active", "paused", "retired"]
WorkflowRunStatus = Literal["pending", "running", "completed", "failed", "cancelled"]
StepStatus = Literal["pending", "running", "completed", "failed", "skipped"]
StepType = Literal["agent", "model", "tool", "human", "condition", "parallel"]


# ── Agent Registry ──────────────────────────────────────────────────────────


class AgentCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: str | None = Field(None, max_length=2000)
    agent_type: AgentType = "autonomous"
    owner: str | None = Field(None, max_length=200)
    default_model: str | None = Field(None, max_length=200)
    default_tools: list[str] = Field(default_factory=list)
    budget_envelope: Decimal | None = Field(None, ge=0)
    policy_profile: str | None = Field(None, max_length=200)
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
    policy_profile: str | None = Field(None, max_length=200)
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
    policy_profile: str | None = None
    status: str
    config: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class AgentListResponse(BaseModel):
    agents: list[AgentResponse]
    total: int


class AgentStats(BaseModel):
    agent_id: uuid.UUID
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


# ── Workflow Definitions ────────────────────────────────────────────────────


class WorkflowDefinitionCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: str | None = Field(None, max_length=2000)
    steps_schema: list[dict[str, Any]] = Field(default_factory=list)
    status: Literal["active", "archived"] = "active"
    config: dict[str, Any] = Field(default_factory=dict)


class WorkflowDefinitionUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    description: str | None = Field(None, max_length=2000)
    steps_schema: list[dict[str, Any]] | None = None
    status: Literal["active", "archived"] | None = None
    config: dict[str, Any] | None = None


class WorkflowDefinitionResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str | None = None
    steps_schema: list[dict[str, Any]]
    status: str
    config: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class WorkflowDefinitionListResponse(BaseModel):
    workflows: list[WorkflowDefinitionResponse]
    total: int


# ── Workflow Runs ───────────────────────────────────────────────────────────


class WorkflowRunCreate(BaseModel):
    workflow_id: uuid.UUID
    agent_id: uuid.UUID | None = None
    parent_run_id: uuid.UUID | None = None
    trigger: str | None = Field(None, max_length=200)
    input_data: dict[str, Any] = Field(default_factory=dict)


class WorkflowRunUpdate(BaseModel):
    status: WorkflowRunStatus | None = None
    total_cost: Decimal | None = None
    total_tokens: int | None = None
    total_duration_ms: int | None = None
    output_data: dict[str, Any] | None = None
    error: str | None = None


class WorkflowStepResponse(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    step_index: int
    name: str
    step_type: str
    agent_id: uuid.UUID | None = None
    model: str | None = None
    tool: str | None = None
    status: str
    cost: Decimal
    tokens: int
    duration_ms: int | None = None
    input_data: dict[str, Any] | None = None
    output_data: dict[str, Any] | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime


class WorkflowRunResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    workflow_id: uuid.UUID
    agent_id: uuid.UUID | None = None
    parent_run_id: uuid.UUID | None = None
    status: str
    total_cost: Decimal
    total_tokens: int
    total_duration_ms: int | None = None
    trigger: str | None = None
    input_data: dict[str, Any]
    output_data: dict[str, Any] | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    steps: list[WorkflowStepResponse] = Field(default_factory=list)


class WorkflowRunListResponse(BaseModel):
    runs: list[WorkflowRunResponse]
    total: int


class WorkflowRunSummary(BaseModel):
    """Lightweight run response without steps, for list views."""

    id: uuid.UUID
    workspace_id: uuid.UUID
    workflow_id: uuid.UUID
    agent_id: uuid.UUID | None = None
    parent_run_id: uuid.UUID | None = None
    status: str
    total_cost: Decimal
    total_tokens: int
    total_duration_ms: int | None = None
    trigger: str | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime


class WorkflowRunSummaryListResponse(BaseModel):
    runs: list[WorkflowRunSummary]
    total: int


# ── Workflow Steps ──────────────────────────────────────────────────────────


class WorkflowStepCreate(BaseModel):
    step_index: int = Field(..., ge=0)
    name: str = Field(..., max_length=200)
    step_type: StepType = "agent"
    agent_id: uuid.UUID | None = None
    model: str | None = Field(None, max_length=200)
    tool: str | None = Field(None, max_length=200)
    input_data: dict[str, Any] | None = None


class WorkflowStepUpdate(BaseModel):
    status: StepStatus | None = None
    cost: Decimal | None = None
    tokens: int | None = None
    duration_ms: int | None = None
    output_data: dict[str, Any] | None = None
    error: str | None = None


# ── Cost Attribution ────────────────────────────────────────────────────────


class WorkflowCostAttribution(BaseModel):
    workflow_id: uuid.UUID
    workflow_name: str
    total_runs: int
    total_cost: Decimal
    avg_cost_per_run: Decimal
    cost_by_step: list[StepCostBreakdown]


class StepCostBreakdown(BaseModel):
    step_name: str
    step_type: str
    total_cost: Decimal
    avg_cost: Decimal
    invocation_count: int

    model_config = {"from_attributes": True}


# Fix forward reference
WorkflowCostAttribution.model_rebuild()


# ── Agent Memory ────────────────────────────────────────────────────────────

MemoryType = Literal["short_term", "long_term", "shared"]


class AgentMemoryCreate(BaseModel):
    key: str = Field(..., max_length=500)
    value: str = Field(..., max_length=100_000)
    memory_type: MemoryType = "long_term"
    metadata: dict[str, Any] = Field(default_factory=dict)
    retention_days: int | None = Field(None, ge=1, le=3650)


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
