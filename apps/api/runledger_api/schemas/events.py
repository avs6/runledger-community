from __future__ import annotations

import json
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, field_validator

from runledger_api.core.config import settings
from runledger_api.models.events import RunStatusEnum, SpanStatusEnum, SpanTypeEnum, ToolTypeEnum

# Field limits match the columns events are stored in (models/events.py).
Str255 = Annotated[str, Field(max_length=255)]
_MAX_JSON_BYTES = 256 * 1024  # metadata / labels per event


def _bounded_json(value: dict[str, Any] | None) -> dict[str, Any] | None:
    if value is not None and len(json.dumps(value, default=str)) > _MAX_JSON_BYTES:
        raise ValueError(f"must be at most {_MAX_JSON_BYTES // 1024} KB when serialized")
    return value


class RunStartEvent(BaseModel):
    event_type: Literal["run_start"]
    run_id: uuid.UUID
    application_id: uuid.UUID | None = None
    api_key_id: uuid.UUID | None = None
    end_user_id: Str255 | None = None
    session_id: Str255 | None = None
    feature_tag: Str255 | None = None
    deployment_version: Str255 | None = None
    started_at: datetime
    metadata: dict[str, Any] | None = None
    intent: Annotated[str, Field(max_length=64)] | None = None

    _check_metadata = field_validator("metadata")(classmethod(lambda cls, v: _bounded_json(v)))


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
    name: Str255
    started_at: datetime


class SpanEndEvent(BaseModel):
    event_type: Literal["span_end"]
    span_id: uuid.UUID
    run_id: uuid.UUID
    status: SpanStatusEnum
    ended_at: datetime
    cost_usd: Decimal | None = None
    metadata: dict[str, Any] | None = None

    _check_metadata = field_validator("metadata")(classmethod(lambda cls, v: _bounded_json(v)))


class ProviderCallEvent(BaseModel):
    event_type: Literal["provider_call"]
    run_id: uuid.UUID
    span_id: uuid.UUID | None = None
    api_key_id: uuid.UUID | None = None
    end_user_id: Str255 | None = None
    provider: Annotated[str, Field(max_length=64)]
    model: Annotated[str, Field(max_length=128)]
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_input_tokens: int | None = None
    latency_ms: int | None = None
    cost_usd: Decimal | None = None
    status: Annotated[str, Field(max_length=32)]
    error_type: Annotated[str, Field(max_length=128)] | None = None
    savings_usd: Decimal | None = None
    savings_category: Annotated[str, Field(max_length=64)] | None = None
    savings_reason: str | None = None
    baseline_cost_usd: Decimal | None = None
    optimization_applied: Annotated[str, Field(max_length=64)] | None = None


class ToolCallEvent(BaseModel):
    event_type: Literal["tool_call"]
    run_id: uuid.UUID
    span_id: uuid.UUID | None = None
    # Optional client id; retries with the same id are applied once.
    tool_call_id: uuid.UUID | None = None
    tool_name: Str255
    tool_type: ToolTypeEnum = ToolTypeEnum.read
    risk_score: int | None = None
    duration_ms: int | None = None
    status: Annotated[str, Field(max_length=32)]


class OutcomeEventPayload(BaseModel):
    event_type: Literal["outcome"]
    run_id: uuid.UUID
    # Optional client id; retries with the same id are applied once.
    event_id: uuid.UUID | None = None
    outcome_type: Annotated[str, Field(max_length=128)]
    success: bool
    labels: dict[str, Any] | None = None

    _check_labels = field_validator("labels")(classmethod(lambda cls, v: _bounded_json(v)))


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
    events: Annotated[list[IngestEvent], Field(max_length=settings.ingest_max_batch_events)]


class WebhookIngestRequest(BaseModel):
    workspace_id: uuid.UUID
    events: Annotated[list[IngestEvent], Field(max_length=settings.ingest_max_batch_events)]


# ── Dead letters ───────────────────────────────────────────────────────────────


class DeadLetterResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    event_type: str | None
    run_id: str | None
    event: dict[str, Any]
    error: str
    attempts: int
    status: str
    created_at: datetime
    last_attempt_at: datetime

    model_config = {"from_attributes": True}


class DeadLetterList(BaseModel):
    items: list[DeadLetterResponse]
    total: int


class DeadLetterReplayResult(BaseModel):
    requeued: int


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
