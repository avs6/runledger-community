"""ORM models for OTLP raw-ingest staging tables."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from runledger_api.core.db import Base


class OtlpIngestBatch(Base):
    """One HTTP request to POST /v1/traces — metadata + optional raw payload."""

    __tablename__ = "otlp_ingest_batches"
    __table_args__ = (sa.Index("ix_otlp_batches_workspace", "workspace_id", "received_at"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
    content_type: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    encoding: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    trace_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    span_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(sa.Text, nullable=False, default="pending")
    error: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    raw_payload: Mapped[bytes | None] = mapped_column(sa.LargeBinary, nullable=True)


class OtlpSpanRaw(Base):
    """One normalized-raw span from an OTLP trace, before canonical event synthesis."""

    __tablename__ = "otlp_spans_raw"
    __table_args__ = (
        sa.Index("ix_otlp_spans_raw_batch", "batch_id"),
        sa.Index("ix_otlp_spans_raw_trace", "workspace_id", "external_trace_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("otlp_ingest_batches.id", ondelete="CASCADE"),
        nullable=True,
    )
    external_trace_id: Mapped[str] = mapped_column(sa.Text, nullable=False)
    external_span_id: Mapped[str] = mapped_column(sa.Text, nullable=False)
    external_parent_span_id: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    span_name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    start_time: Mapped[datetime | None] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=True)
    status_code: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    resource_attributes: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    scope_attributes: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    span_attributes: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    events: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    links: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    normalized: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
