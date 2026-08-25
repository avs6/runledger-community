from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict


class RunListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    api_key_id: uuid.UUID | None = None
    status: str
    end_user_id: str | None
    session_id: str | None
    feature_tag: str | None
    deployment_version: str | None
    total_cost_usd: Decimal | None
    total_input_tokens: int | None
    total_output_tokens: int | None
    started_at: datetime
    ended_at: datetime | None
    # Derived
    duration_ms: int | None
    primary_model: str | None  # model from the first/most expensive provider_call


class RunListResponse(BaseModel):
    items: list[RunListItem]
    next_cursor: str | None  # ISO timestamp of last item's started_at
    total: int


class SpanDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    run_id: uuid.UUID
    parent_span_id: uuid.UUID | None
    span_type: str
    name: str
    started_at: datetime
    ended_at: datetime | None
    status: str
    cost_usd: Decimal | None
    metadata: dict[str, Any] | None = None


class ProviderCallDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    span_id: uuid.UUID | None
    run_id: uuid.UUID
    provider: str
    model: str
    input_tokens: int | None
    output_tokens: int | None
    cached_input_tokens: int | None
    latency_ms: int | None
    cost_usd: Decimal | None
    status: str
    error_type: str | None
    created_at: datetime


class ToolCallDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    span_id: uuid.UUID | None
    run_id: uuid.UUID
    tool_name: str
    tool_type: str
    risk_score: int | None
    duration_ms: int | None
    status: str
    created_at: datetime


class RunDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    api_key_id: uuid.UUID | None = None
    status: str
    end_user_id: str | None
    session_id: str | None
    feature_tag: str | None
    deployment_version: str | None
    total_cost_usd: Decimal | None
    total_input_tokens: int | None
    total_output_tokens: int | None
    started_at: datetime
    ended_at: datetime | None
    duration_ms: int | None
    spans: list[SpanDetail]
    provider_calls: list[ProviderCallDetail]
    tool_calls: list[ToolCallDetail]
    # Payload fields — only present when capture policy is SAMPLED or FULL
    input_payload: list[dict[str, Any]] | None = None
    output_payload: Any | None = None
    span_payloads: dict[str, dict[str, Any]] | None = None


class GraphNodeData(BaseModel):
    span_type: str
    status: str
    cost_usd: Decimal | None
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int | None
    model: str | None
    provider: str | None
    error_type: str | None
    started_at: datetime | None
    ended_at: datetime | None
    duration_ms: int | None
    metadata: dict[str, Any] | None


class GraphNode(BaseModel):
    id: str
    label: str
    data: GraphNodeData


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str


class RunGraphResponse(BaseModel):
    run_id: uuid.UUID
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class RunFlowRecord(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    workspace_name: str
    tenant_id: uuid.UUID
    tenant_name: str
    status: str
    end_user_id: str | None
    feature_tag: str | None
    primary_model: str | None
    provider: str | None
    route: str
    outcome: str
    prompt: str
    skill: str
    agent: str
    tool: str
    team: str
    application: str
    cost_band: str
    total_cost_usd: Decimal
    total_input_tokens: int
    total_output_tokens: int
    cached_input_tokens: int
    latency_ms: int | None
    success: bool
    savings_usd: Decimal
    savings_category: str | None = None
    savings_reason: str | None = None
    started_at: datetime


class RunFlowResponse(BaseModel):
    scope: str
    mode: str
    metric: str
    sampled_runs: int
    total_runs: int
    workspace_count: int
    generated_at: datetime
    items: list[RunFlowRecord]


class GovernanceToolEvidence(BaseModel):
    tool_name: str
    tool_type: str
    status: str
    risk_score: int | None = None
    registry_policy: str | None = None
    registry_runtime_enforcement: bool = False
    matched_policy_count: int = 0
    matched_policy_names: list[str] = []
    matched_policy_actions: list[str] = []


class GovernanceSecurityEvidence(BaseModel):
    id: str
    event_type: str
    tool_name: str | None = None
    end_user_id: str | None = None
    detected_at: datetime
    details: dict[str, Any] = {}


class GovernanceAlertEvidence(BaseModel):
    id: str
    rule_id: str
    rule_name: str
    fired_at: datetime
    metric_value: Decimal
    resolved_at: datetime | None = None


class GovernanceAuditEvidence(BaseModel):
    id: str
    action: str
    target_type: str | None = None
    target_id: str | None = None
    created_at: datetime


class RunGovernanceContextResponse(BaseModel):
    run_id: uuid.UUID
    tags: list[str]
    tool_evidence: list[GovernanceToolEvidence]
    security_events: list[GovernanceSecurityEvidence]
    alert_evidence: list[GovernanceAlertEvidence]
    audit_events: list[GovernanceAuditEvidence]
    governance_pack_summary: dict[str, int]


# ── Login ─────────────────────────────────────────────────────────────────────


class RunbookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    run_id: uuid.UUID
    severity: str
    summary: dict[str, Any]
    generated_at: datetime


class RunbookList(BaseModel):
    items: list[RunbookResponse]
    total: int


# ── Login ─────────────────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    email: str
    password: str
    workspace_id: str | None = None


class LoginResponse(BaseModel):
    email: str
    full_name: str | None
    user_id: str
    workspace_id: str
    workspace_name: str
    tenant_id: str
    tenant_name: str
    api_key: str
    is_platform_admin: bool
    tenant_role: str | None
    workspace_role: str | None
    workspace_ids: list[str]
