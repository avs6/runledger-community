from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

from runledger_api.models.events import RunStatusEnum, SpanStatusEnum, SpanTypeEnum, ToolTypeEnum


class RunStartEvent(BaseModel):
    event_type: Literal["run_start"]
    run_id: uuid.UUID
    application_id: uuid.UUID | None = None
    end_user_id: str | None = None
    session_id: str | None = None
    feature_tag: str | None = None
    deployment_version: str | None = None
    started_at: datetime
    metadata: dict[str, Any] | None = None
    intent: str | None = None


class RunEndEvent(BaseModel):
    event_type: Literal["run_end"]
    run_id: uuid.UUID
    status: RunStatusEnum
    ended_at: datetime
    total_cost_usd: Decimal | None = None
    total_input_tokens: int | None = None
    total_output_tokens: int | None = None


class SpanStartEvent(BaseModel):
    event_type: Literal["span_start"]
    span_id: uuid.UUID
    run_id: uuid.UUID
    parent_span_id: uuid.UUID | None = None
    span_type: SpanTypeEnum
    name: str
    started_at: datetime


class SpanEndEvent(BaseModel):
    event_type: Literal["span_end"]
    span_id: uuid.UUID
    run_id: uuid.UUID
    status: SpanStatusEnum
    ended_at: datetime
    cost_usd: Decimal | None = None
    metadata: dict[str, Any] | None = None


class ProviderCallEvent(BaseModel):
    event_type: Literal["provider_call"]
    run_id: uuid.UUID
    span_id: uuid.UUID | None = None
    provider: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_input_tokens: int | None = None
    latency_ms: int | None = None
    cost_usd: Decimal | None = None
    status: str
    error_type: str | None = None
    savings_usd: Decimal | None = None
    savings_category: str | None = None
    savings_reason: str | None = None
    baseline_cost_usd: Decimal | None = None
    optimization_applied: str | None = None


class ToolCallEvent(BaseModel):
    event_type: Literal["tool_call"]
    run_id: uuid.UUID
    span_id: uuid.UUID | None = None
    tool_name: str
    tool_type: ToolTypeEnum = ToolTypeEnum.read
    risk_score: int | None = None
    duration_ms: int | None = None
    status: str


class OutcomeEventPayload(BaseModel):
    event_type: Literal["outcome"]
    run_id: uuid.UUID
    outcome_type: str
    success: bool
    labels: dict[str, Any] | None = None


IngestEvent = Annotated[
    RunStartEvent
    | RunEndEvent
    | SpanStartEvent
    | SpanEndEvent
    | ProviderCallEvent
    | ToolCallEvent
    | OutcomeEventPayload,
    Field(discriminator="event_type"),
]


class BatchIngestRequest(BaseModel):
    events: list[IngestEvent]


# ── Response schemas ───────────────────────────────────────────────────────────


class AgentRunResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    application_id: uuid.UUID | None
    end_user_id: str | None
    session_id: str | None
    feature_tag: str | None
    deployment_version: str | None
    status: RunStatusEnum
    started_at: datetime
    ended_at: datetime | None
    total_cost_usd: Decimal | None
    total_input_tokens: int | None
    total_output_tokens: int | None

    model_config = {"from_attributes": True}
