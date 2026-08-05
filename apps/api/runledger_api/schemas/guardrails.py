"""Pydantic schemas for guardrails, content safety, and policy engine."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

GuardrailMode = Literal["pre_call", "post_call", "both"]
GuardrailRuleType = Literal["custom", "template", "builtin_filter", "partner"]
GuardrailStatus = Literal["active", "disabled", "draft"]
GuardrailSeverity = Literal["off", "low", "medium", "high", "strict"]
GuardrailDecision = Literal["allow", "block", "modify"]
PartnerProvider = Literal[
    "presidio", "bedrock", "lakera", "openai_moderation",
    "google_model_armor", "guardrails_ai", "prompt_security", "lasso",
]
FallbackAction = Literal["allow", "block"]


# ── Guardrail Rules ──────────────────────────────────────────────────────────


class GuardrailRuleCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: str | None = Field(None, max_length=2000)
    mode: GuardrailMode = "pre_call"
    rule_type: GuardrailRuleType = "custom"
    logic: str | None = Field(
        None,
        description=(
            "Python-like logic for custom guardrails. Available inputs: "
            "texts, images, tools, tool_calls, structured_messages, model. "
            "Return: allow(), block(reason), modify(texts=[], images=[], tool_calls=[])."
        ),
    )
    config: dict[str, Any] = Field(default_factory=dict)
    severity: GuardrailSeverity = "medium"
    priority: int = Field(100, ge=0, le=10000)
    status: GuardrailStatus = "active"
    template_id: str | None = None


class GuardrailRuleUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    description: str | None = Field(None, max_length=2000)
    mode: GuardrailMode | None = None
    logic: str | None = None
    config: dict[str, Any] | None = None
    severity: GuardrailSeverity | None = None
    priority: int | None = Field(None, ge=0, le=10000)
    status: GuardrailStatus | None = None


class GuardrailRuleResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str | None
    mode: str
    rule_type: str
    logic: str | None
    config: dict[str, Any]
    severity: str
    priority: int
    status: str
    template_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GuardrailRuleList(BaseModel):
    items: list[GuardrailRuleResponse]
    total: int


# ── Guardrail Test ───────────────────────────────────────────────────────────


class GuardrailTestInput(BaseModel):
    texts: list[str] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)
    tools: list[dict[str, Any]] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    structured_messages: list[dict[str, Any]] = Field(default_factory=list)
    model: str | None = None
    user_id: str | None = None
    team_id: str | None = None
    end_user_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GuardrailTestResult(BaseModel):
    guardrail_id: uuid.UUID
    guardrail_name: str
    decision: str
    reason: str | None = None
    latency_ms: float
    modified_texts: list[str] | None = None
    modified_images: list[str] | None = None
    modified_tool_calls: list[dict[str, Any]] | None = None
    error: str | None = None


class GuardrailTestResponse(BaseModel):
    results: list[GuardrailTestResult]
    overall_decision: str
    total_latency_ms: float


# ── Guardrail Events (monitoring) ────────────────────────────────────────────


class GuardrailEventResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    guardrail_rule_id: uuid.UUID
    guardrail_name: str
    mode: str
    decision: str
    reason: str | None
    latency_ms: float
    request_metadata: dict[str, Any]
    gateway_request_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class GuardrailEventList(BaseModel):
    items: list[GuardrailEventResponse]
    total: int


class GuardrailStats(BaseModel):
    total_evaluations: int
    total_blocks: int
    total_modifications: int
    total_allows: int
    block_rate: float
    avg_latency_ms: float
    top_triggered: list[dict[str, Any]]
    by_decision: dict[str, int]


# ── Partner Guardrails ───────────────────────────────────────────────────────


class PartnerGuardrailCreate(BaseModel):
    provider: PartnerProvider
    name: str = Field(..., max_length=200)
    mode: GuardrailMode = "pre_call"
    endpoint_url: str | None = None
    credentials: dict[str, Any] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)
    timeout_ms: int = Field(2000, ge=100, le=30000)
    fallback_action: FallbackAction = "allow"
    priority: int = Field(200, ge=0, le=10000)


class PartnerGuardrailUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    mode: GuardrailMode | None = None
    endpoint_url: str | None = None
    credentials: dict[str, Any] | None = None
    config: dict[str, Any] | None = None
    timeout_ms: int | None = Field(None, ge=100, le=30000)
    fallback_action: FallbackAction | None = None
    priority: int | None = Field(None, ge=0, le=10000)
    status: Literal["active", "disabled"] | None = None


class PartnerGuardrailResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    provider: str
    name: str
    mode: str
    endpoint_url: str | None
    config: dict[str, Any]
    timeout_ms: int
    fallback_action: str
    priority: int
    status: str
    last_health_check: datetime | None
    health_status: str | None
    total_calls: int
    total_cost_usd: float
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PartnerGuardrailList(BaseModel):
    items: list[PartnerGuardrailResponse]
    total: int


# ── Guardrail Test Cases ─────────────────────────────────────────────────────


class GuardrailTestCaseCreate(BaseModel):
    guardrail_rule_id: uuid.UUID
    name: str = Field(..., max_length=200)
    input_text: str
    input_metadata: dict[str, Any] = Field(default_factory=dict)
    expected_decision: GuardrailDecision


class GuardrailTestCaseResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    guardrail_rule_id: uuid.UUID
    name: str
    input_text: str
    input_metadata: dict[str, Any]
    expected_decision: str
    created_at: datetime

    model_config = {"from_attributes": True}


class GuardrailTestCaseList(BaseModel):
    items: list[GuardrailTestCaseResponse]
    total: int


class GuardrailRegressionResult(BaseModel):
    test_case_id: uuid.UUID
    test_case_name: str
    expected_decision: str
    actual_decision: str
    passed: bool
    latency_ms: float
    reason: str | None = None


class GuardrailRegressionReport(BaseModel):
    guardrail_rule_id: uuid.UUID
    guardrail_name: str
    total_cases: int
    passed: int
    failed: int
    results: list[GuardrailRegressionResult]


# ── Built-in Content Filter Config ───────────────────────────────────────────


class ContentFilterConfig(BaseModel):
    filter_name: str
    severity: GuardrailSeverity = "medium"
    enabled: bool = True


class ContentFilterActivation(BaseModel):
    filters: list[ContentFilterConfig]


class ContentFilterStatus(BaseModel):
    filter_name: str
    description: str
    severity: str
    enabled: bool
    category: str


class ContentFilterListResponse(BaseModel):
    filters: list[ContentFilterStatus]


# ── Batch Test ───────────────────────────────────────────────────────────────


class BatchTestResult(BaseModel):
    row_index: int
    input_text: str
    decisions: list[GuardrailTestResult]
    overall_decision: str


class BatchTestResponse(BaseModel):
    total_rows: int
    total_blocks: int
    total_allows: int
    total_modifications: int
    results: list[BatchTestResult]


# ── Templates ────────────────────────────────────────────────────────────────


class GuardrailTemplate(BaseModel):
    template_id: str
    name: str
    description: str
    mode: str
    default_logic: str
    default_config: dict[str, Any]
    category: str
