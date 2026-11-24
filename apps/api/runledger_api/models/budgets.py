"""
ORM models for budget enforcement: budgets, breaches, notification channels.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from runledger_api.core.db import Base
from runledger_api.core.secrets import EncryptedText


class ScopeTypeEnum(enum.StrEnum):
    workspace = "workspace"
    end_user = "end_user"
    feature_tag = "feature_tag"
    app = "app"
    access_group = "access_group"
    api_key = "api_key"
    provider_profile = "provider_profile"
    model = "model"


class PeriodTypeEnum(enum.StrEnum):
    daily = "daily"
    weekly = "weekly"
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
      - app: traffic where agent_run.app_id == scope_id
      - access_group: traffic from members of the specified access group
      - api_key: traffic authenticated by the specified API key
      - provider_profile: traffic routed through the specified provider profile
      - model: traffic to models matching scope_id (exact, or a trailing ``*``
        prefix pattern such as ``gpt-4*``); ``api_key_id`` optionally narrows it to
        one key. This replaces the old per-key model budgets (review G-01).

    At most one active budget per (scope, key filter, period): a unique partial index
    (``uq_budgets_active_scope``, created in the finops_budget_spend migration).
    """

    __tablename__ = "budgets"
    __table_args__ = (sa.Index("ix_budgets_workspace", "workspace_id", "is_active"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    scope_type: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    scope_id: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
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
    # Slack/webhook URLs carry their token in the path: encrypted at rest (F-15).
    destination_url: Mapped[str] = mapped_column(EncryptedText, nullable=False)
    events: Mapped[list[str]] = mapped_column(
        ARRAY(sa.Text), nullable=False, server_default=sa.text("'{}'")
    )
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )
    email_enabled: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )
    # Version of this destination's webhook signing secret; bumping rotates it.
    signing_version: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default="1", default=1
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class BudgetNotificationDelivery(Base):
    """
    Delivery attempt record for webhook or Slack notification destinations.
    """

    __tablename__ = "budget_notification_deliveries"
    __table_args__ = (
        sa.Index("ix_budget_notification_deliveries_notification", "notification_id", "created_at"),
        sa.Index("ix_budget_notification_deliveries_workspace", "workspace_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    notification_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("budget_notifications.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    attempt: Mapped[int] = mapped_column(sa.Integer(), nullable=False, server_default=sa.text("1"))
    status: Mapped[str] = mapped_column(
        sa.String(16), nullable=False, server_default=sa.text("'pending'")
    )
    response_status: Mapped[int | None] = mapped_column(sa.Integer(), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    # Queued delivery (F-22): the event body, when the next attempt is due, and the
    # breach it reports. ``status`` is pending → success | failed (retries exhausted).
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    next_attempt_at: Mapped[datetime | None] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True
    )
    breach_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class BudgetSpend(Base):
    """Spend of one budget in one period: the source of truth (review cd:B-05).

    Redis holds a short-lived cache of ``spend_usd`` for the hot path; losing it (LRU
    eviction, restart without AOF) only costs a Postgres read. ``threshold_notified_at``
    and ``breached_at`` make the 80% event and the breach fire once per period.
    """

    __tablename__ = "budget_spend"

    budget_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("budgets.id", ondelete="CASCADE"),
        primary_key=True,
    )
    period_key: Mapped[str] = mapped_column(sa.String(16), primary_key=True)
    spend_usd: Mapped[Decimal] = mapped_column(
        sa.Numeric(18, 8), nullable=False, server_default="0", default=Decimal(0)
    )
    call_count: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default="0", default=0
    )
    threshold_notified_at: Mapped[datetime | None] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True
    )
    breached_at: Mapped[datetime | None] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class BudgetSpendCall(Base):
    """A provider call already counted against budgets (idempotency, cd:B-05)."""

    __tablename__ = "budget_spend_calls"
    __table_args__ = (sa.Index("ix_budget_spend_calls_workspace", "workspace_id", "counted_at"),)

    provider_call_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    counted_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class RunawayHold(Base):
    """A run or session the gateway refuses to serve (review cd:B-09).

    Created by the runaway detector (retry storm / token spike) or by an admin;
    active until ``expires_at`` or until released.
    """

    __tablename__ = "budget_runaway_holds"
    __table_args__ = (
        sa.Index("ix_budget_runaway_holds_subject", "workspace_id", "subject_type", "subject_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    subject_type: Mapped[str] = mapped_column(sa.String(16), nullable=False)  # run | session
    subject_id: Mapped[str] = mapped_column(sa.Text, nullable=False)
    reason: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'{}'"), default=dict
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=False)
    released_at: Mapped[datetime | None] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=True)
    released_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
