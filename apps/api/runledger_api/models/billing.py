"""
ORM models for billing: billing_periods, chargeback_rules, usage_snapshots.
"""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from runledger_api.core.db import Base


class BillingPeriodStatusEnum(str, enum.Enum):
    open = "open"
    closing = "closing"
    closed = "closed"


class AllocationTypeEnum(str, enum.Enum):
    cost_center = "cost_center"
    team = "team"
    env = "env"


class BillingPeriod(Base):
    __tablename__ = "billing_periods"
    __table_args__ = (
        sa.Index("ix_billing_periods_workspace", "workspace_id", "status"),
        sa.Index(
            "ix_billing_periods_dates",
            "workspace_id",
            "period_start",
            "period_end",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    period_start: Mapped[date] = mapped_column(sa.Date, nullable=False)
    period_end: Mapped[date] = mapped_column(sa.Date, nullable=False)
    status: Mapped[str] = mapped_column(
        sa.String(16), nullable=False, server_default=sa.text("'open'")
    )
    total_cost_usd: Mapped[Decimal | None] = mapped_column(sa.Numeric(14, 6), nullable=True)
    snapshot_hash: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class ChargebackRule(Base):
    __tablename__ = "chargeback_rules"
    __table_args__ = (
        sa.Index("ix_chargeback_rules_workspace", "workspace_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    allocation_type: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    dimension: Mapped[str] = mapped_column(sa.Text, nullable=False)
    weight: Mapped[Decimal] = mapped_column(sa.Numeric(6, 4), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class UsageSnapshot(Base):
    __tablename__ = "usage_snapshots"
    __table_args__ = (
        sa.Index("ix_usage_snapshots_period", "billing_period_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    billing_period_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    snapshot_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    signature: Mapped[str] = mapped_column(sa.Text, nullable=False)
    signing_key_id: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default=sa.text("'v1'")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
