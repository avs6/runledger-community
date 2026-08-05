"""
ORM models for budget enforcement: budgets, breaches, notification channels.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from runledger_api.core.db import Base


class ScopeTypeEnum(enum.StrEnum):
    workspace = "workspace"
    end_user = "end_user"
    feature_tag = "feature_tag"
    app = "app"


class PeriodTypeEnum(enum.StrEnum):
    daily = "daily"
    monthly = "monthly"
    total = "total"


class ActionEnum(enum.StrEnum):
    notify = "notify"
    block = "block"
    downgrade = "downgrade"
    throttle = "throttle"
    fallback = "fallback"


class ChannelEnum(enum.StrEnum):
    webhook = "webhook"
    slack = "slack"


class Budget(Base):
    """
    A spend limit with an enforcement action.

    scope_type / scope_id determine which traffic the budget applies to:
      - workspace: all traffic for the workspace
      - end_user:  traffic where provider_call.end_user_id == scope_id
      - feature_tag: traffic where agent_run.feature_tag == scope_id
      - app: reserved for future app-level scoping
    """

    __tablename__ = "budgets"
    __table_args__ = (sa.Index("ix_budgets_workspace", "workspace_id", "is_active"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    scope_type: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    scope_id: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    period_type: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    limit_usd: Mapped[Decimal] = mapped_column(sa.Numeric(14, 6), nullable=False)
    action: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    downgrade_to_model: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class BudgetBreach(Base):
    """
    Records each time a budget limit is crossed.
    """

    __tablename__ = "budget_breaches"
    __table_args__ = (sa.Index("ix_budget_breaches_budget", "budget_id", "occurred_at"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    budget_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
    spend_at_breach_usd: Mapped[Decimal | None] = mapped_column(sa.Numeric(14, 6), nullable=True)
    action_taken: Mapped[str | None] = mapped_column(sa.String(16), nullable=True)
    notified_at: Mapped[datetime | None] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=True)


class BudgetNotification(Base):
    """
    Webhook / Slack endpoint that receives budget event payloads.
    """

    __tablename__ = "budget_notifications"
    __table_args__ = (sa.Index("ix_budget_notifications_workspace", "workspace_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    channel: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    destination_url: Mapped[str] = mapped_column(sa.Text, nullable=False)
    events: Mapped[list[str]] = mapped_column(
        ARRAY(sa.Text), nullable=False, server_default=sa.text("'{}'")
    )
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )
    email_enabled: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
