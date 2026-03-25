"""ORM models for billing webhook configs and delivery log."""

from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from runledger_api.core.db import Base


class BillingWebhookConfig(Base):
    """
    A workspace-scoped webhook endpoint that receives HMAC-signed
    billing.period.closed events.
    """

    __tablename__ = "billing_webhook_configs"
    __table_args__ = (sa.Index("ix_billing_webhook_configs_workspace", "workspace_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    url: Mapped[str] = mapped_column(sa.Text, nullable=False)
    secret: Mapped[str] = mapped_column(sa.Text, nullable=False)
    label: Mapped[str] = mapped_column(
        sa.String(128), nullable=False, server_default="'billing webhook'"
    )
    enabled: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class BillingWebhookDelivery(Base):
    """
    Log entry for each webhook delivery attempt.
    status: pending | success | failed
    """

    __tablename__ = "billing_webhook_deliveries"
    __table_args__ = (
        sa.Index("ix_billing_webhook_deliveries_config", "webhook_config_id", "created_at"),
        sa.Index("ix_billing_webhook_deliveries_period", "billing_period_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    webhook_config_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("billing_webhook_configs.id", ondelete="CASCADE"),
        nullable=False,
    )
    billing_period_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    attempt: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default="1")
    status: Mapped[str] = mapped_column(sa.String(16), nullable=False, server_default="'pending'")
    response_status: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    response_body: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
