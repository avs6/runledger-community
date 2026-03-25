"""ORM models for Kafka export configs and delivery log."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from runledger_api.core.db import Base

_DEFAULT_EVENT_TYPES = (
    '["run.completed","run.failed","alert.fired","budget.breached","score.submitted"]'
)


class KafkaExportConfig(Base):
    """
    Workspace-scoped Kafka producer config.
    Events matching event_types are published to {topic_prefix}.{resource} topics.
    """

    __tablename__ = "kafka_export_configs"
    __table_args__ = (sa.Index("ix_kafka_export_configs_workspace", "workspace_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    label: Mapped[str] = mapped_column(
        sa.String(128), nullable=False, server_default="'kafka export'"
    )
    bootstrap_servers: Mapped[str] = mapped_column(sa.Text, nullable=False)
    topic_prefix: Mapped[str] = mapped_column(
        sa.String(64), nullable=False, server_default="'runledger'"
    )
    # PLAINTEXT | SSL | SASL_PLAINTEXT | SASL_SSL
    security_protocol: Mapped[str] = mapped_column(
        sa.String(32), nullable=False, server_default="'PLAINTEXT'"
    )
    # PLAIN | SCRAM-SHA-256 | SCRAM-SHA-512
    sasl_mechanism: Mapped[str | None] = mapped_column(sa.String(32), nullable=True)
    sasl_username: Mapped[str | None] = mapped_column(sa.String(256), nullable=True)
    sasl_password_encrypted: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    ssl_ca_cert: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    event_types: Mapped[list[str] | None] = mapped_column(
        JSONB, nullable=False, server_default=sa.text(f"'{_DEFAULT_EVENT_TYPES}'::jsonb")
    )
    enabled: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class KafkaExportDelivery(Base):
    """Log entry for each Kafka publish attempt. status: pending | success | failed"""

    __tablename__ = "kafka_export_deliveries"
    __table_args__ = (
        sa.Index("ix_kafka_export_deliveries_config", "config_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    config_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("kafka_export_configs.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    topic: Mapped[str] = mapped_column(sa.String(256), nullable=False)
    status: Mapped[str] = mapped_column(
        sa.String(16), nullable=False, server_default="'pending'"
    )
    error_detail: Mapped[str | None] = mapped_column(sa.String(512), nullable=True)
    attempt: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default="1")
    delivered_at: Mapped[datetime | None] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
