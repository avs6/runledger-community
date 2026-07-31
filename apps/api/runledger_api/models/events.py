import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from runledger_api.core.db import Base


class RunStatusEnum(StrEnum):
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class SpanTypeEnum(StrEnum):
    chain = "chain"
    llm = "llm"
    tool = "tool"
    agent = "agent"
    retrieval = "retrieval"


class SpanStatusEnum(StrEnum):
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class ToolTypeEnum(StrEnum):
    read = "read"
    write = "write"
    privileged = "privileged"


class AgentRun(Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        sa.Index("ix_agent_runs_workspace_started", "workspace_id", "started_at"),
        sa.Index("ix_agent_runs_end_user", "workspace_id", "end_user_id"),
        sa.Index("ix_agent_runs_feature_tag", "workspace_id", "feature_tag"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    application_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("applications.id", ondelete="SET NULL"),
        nullable=True,
    )
    end_user_id: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    session_id: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    feature_tag: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    deployment_version: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    status: Mapped[RunStatusEnum] = mapped_column(
        sa.Enum(RunStatusEnum, name="run_status_enum"), default=RunStatusEnum.running
    )
    started_at: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=True)
    total_cost_usd: Mapped[Decimal | None] = mapped_column(sa.Numeric(14, 8), nullable=True)
    total_input_tokens: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True)
    total_output_tokens: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True)
    run_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)

    # OTLP source-provenance fields (migration 026)
    source_type: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    external_trace_id: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    external_trace_state: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    resource_attributes: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)


class Span(Base):
    __tablename__ = "spans"
    __table_args__ = (
        sa.Index("ix_spans_run_id", "run_id"),
        sa.Index("ix_spans_parent", "parent_span_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), sa.ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False
    )
    parent_span_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    span_type: Mapped[SpanTypeEnum] = mapped_column(
        sa.Enum(SpanTypeEnum, name="span_type_enum"), nullable=False
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    started_at: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=True)
    status: Mapped[SpanStatusEnum] = mapped_column(
        sa.Enum(SpanStatusEnum, name="span_status_enum"), default=SpanStatusEnum.running
    )
    cost_usd: Mapped[Decimal | None] = mapped_column(sa.Numeric(14, 8), nullable=True)
    span_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)

    # OTLP source-provenance fields (migration 026)
    external_span_id: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    external_parent_span_id: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    trace_flags: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    instrumentation_scope_name: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    instrumentation_scope_version: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    source_span_kind: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    source_attributes: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)


class ProviderCall(Base):
    """
    Stores every LLM API call with token counts and cost.

    Note: This table will be partitioned by RANGE (created_at) in Phase 4
    once metering volume justifies it. For Phase 1 it is a plain table.
    """

    __tablename__ = "provider_calls"
    __table_args__ = (
        sa.Index("ix_provider_calls_run_id", "run_id"),
        sa.Index("ix_provider_calls_workspace_created", "workspace_id", "created_at"),
        sa.Index("ix_provider_calls_end_user", "workspace_id", "end_user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    span_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    run_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), sa.ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    end_user_id: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    provider: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    model: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    input_tokens: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    cached_input_tokens: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    cost_usd: Mapped[Decimal | None] = mapped_column(sa.Numeric(14, 8), nullable=True)
    status: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    error_type: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )

    # OTLP source-provenance fields (migration 026)
    provider_request_id: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    reported_cost_usd: Mapped[Decimal | None] = mapped_column(sa.Numeric(14, 8), nullable=True)
    cost_source: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    model_provider: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    input_tokens_details: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    output_tokens_details: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    savings_usd: Mapped[Decimal | None] = mapped_column(sa.Numeric(14, 8), nullable=True)
    savings_category: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
    savings_reason: Mapped[str | None] = mapped_column(sa.Text, nullable=True)


class ToolCall(Base):
    __tablename__ = "tool_calls"
    __table_args__ = (sa.Index("ix_tool_calls_run_id", "run_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    span_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    run_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), sa.ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    tool_name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    tool_type: Mapped[ToolTypeEnum] = mapped_column(
        sa.Enum(ToolTypeEnum, name="tool_type_enum"), default=ToolTypeEnum.read
    )
    risk_score: Mapped[int | None] = mapped_column(sa.SmallInteger, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    status: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )

    # OTLP source-provenance fields (migration 026)
    external_span_id: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    tool_arguments: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    tool_result_summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)


class OutcomeEvent(Base):
    __tablename__ = "outcome_events"
    __table_args__ = (sa.Index("ix_outcome_events_run_id", "run_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), sa.ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    success: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    labels: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
