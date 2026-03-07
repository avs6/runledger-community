"""
ORM models for advanced alerting: alert rules and alert firing history.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from runledger_api.core.db import Base


class AlertRule(Base):
    """
    A threshold rule that fires a notification when a metric crosses a limit.

    metric values: error_rate | p95_latency | avg_score | spend_velocity
    operator values: gt (greater than) | lt (less than)
    """

    __tablename__ = "alert_rules"
    __table_args__ = (
        sa.Index("ix_alert_rules_workspace", "workspace_id", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    metric: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    operator: Mapped[str] = mapped_column(sa.String(4), nullable=False)
    threshold: Mapped[Decimal] = mapped_column(sa.Numeric(14, 6), nullable=False)
    window_minutes: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default="60"
    )
    action: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default="notify"
    )
    channel_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("budget_notifications.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class AlertFiring(Base):
    """
    Records each time an alert rule fires (threshold crossed).
    """

    __tablename__ = "alert_firings"
    __table_args__ = (
        sa.Index("ix_alert_firings_rule", "rule_id", "fired_at"),
        sa.Index("ix_alert_firings_workspace", "workspace_id", "fired_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("alert_rules.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    fired_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
    metric_value: Mapped[Decimal] = mapped_column(sa.Numeric(14, 6), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True
    )
