from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from runledger_api.core.db import Base


class KafkaExportConfig(Base):
    __tablename__ = "kafka_export_configs"
    __table_args__ = (
        sa.Index("ix_kafka_export_configs_workspace", "workspace_id"),
        sa.Index("ix_kafka_export_configs_enabled", "workspace_id", "enabled"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    label: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    bootstrap_servers: Mapped[str] = mapped_column(sa.Text, nullable=False)
    topic_prefix: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    security_protocol: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    sasl_mechanism: Mapped[str | None] = mapped_column(sa.String(32), nullable=True)
    sasl_username: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    sasl_password_secret: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    ssl_ca_cert: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    event_types: Mapped[list[str]] = mapped_column(
        ARRAY(sa.String), nullable=False, server_default=sa.text("'{}'::varchar[]")
    )
    enabled: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=sa.text("NOW()"),
        onupdate=sa.text("NOW()"),
    )


class KafkaExportDelivery(Base):
    __tablename__ = "kafka_export_deliveries"
    __table_args__ = (
        sa.Index("ix_kafka_export_deliveries_config_created", "config_id", "created_at"),
        sa.Index("ix_kafka_export_deliveries_workspace_created", "workspace_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    config_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("kafka_export_configs.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    topic: Mapped[str] = mapped_column(sa.String(512), nullable=False)
    status: Mapped[str] = mapped_column(sa.String(32), nullable=False, server_default="pending")
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error_detail: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    attempt: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default="1")
    delivered_at: Mapped[datetime | None] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")
    )
