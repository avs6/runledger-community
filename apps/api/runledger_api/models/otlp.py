"""ORM models for OTLP raw-ingest staging tables."""

from __future__ import annotations

import uuid
from datetime import date, datetime
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
    signal_type: Mapped[str] = mapped_column(sa.Text, nullable=False, default="trace")
    trace_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    span_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    metric_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    log_record_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(sa.Text, nullable=False, default="pending")
    error: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    raw_payload: Mapped[bytes | None] = mapped_column(sa.LargeBinary, nullable=True)
    # Ingest health: traces turned into runs vs dropped by LLM-span gating.
    runs_created: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    traces_dropped: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    # Resource-attribute summary computed at ingest (services, attribution hits), so
    # insights never re-parse raw payloads.
    resource_summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)


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


class OtlpMetricRollup(Base):
    """Daily rollup of one OTLP metric series (name + service + bounded attributes).

    Written by ``services.otlp_metrics.record_metric_rollups`` on every /v1/metrics
    batch; read by the metrics API and the GenAI usage reconciliation on Telemetry.
    """

    __tablename__ = "otlp_metric_rollups"
    __table_args__ = (
        sa.UniqueConstraint(
            "workspace_id", "series_key", "day", name="uq_otlp_metric_rollups_series_day"
        ),
        sa.Index("ix_otlp_metric_rollups_ws_day", "workspace_id", "day"),
        sa.Index("ix_otlp_metric_rollups_ws_name", "workspace_id", "name", "day"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    day: Mapped[date] = mapped_column(sa.Date, nullable=False)
    series_key: Mapped[str] = mapped_column(sa.String(40), nullable=False)
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    unit: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
    # sum | gauge | histogram | exponentialHistogram | summary
    kind: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    # delta | cumulative | None (gauge)
    temporality: Mapped[str | None] = mapped_column(sa.String(16), nullable=True)
    service_name: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    points: Mapped[int] = mapped_column(sa.BigInteger, nullable=False, default=0)
    total: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    observations: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True)
    min_value: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    max_value: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    last_value: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    # Last raw cumulative value / count, so the next point's increase can be computed.
    cumulative_value: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    cumulative_count: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True)
    last_seen: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=False)
