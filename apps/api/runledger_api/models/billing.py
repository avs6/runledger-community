"""
ORM models for billing: billing_periods, chargeback_rules, usage_snapshots,
cost_centers, billing_adjustments.
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


class BillingPeriodStatusEnum(enum.StrEnum):
    open = "open"
    closing = "closing"
    closed = "closed"


class AllocationTypeEnum(enum.StrEnum):
    cost_center = "cost_center"
    team = "team"
    env = "env"


class AdjustmentTypeEnum(enum.StrEnum):
    credit = "credit"
    refund = "refund"
    prepaid_deduction = "prepaid_deduction"
    surcharge = "surcharge"


class CostCenter(Base):
    __tablename__ = "cost_centers"
    __table_args__ = (
        sa.Index("ix_cost_centers_workspace", "workspace_id"),
        sa.Index("ix_cost_centers_parent", "workspace_id", "parent_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    code: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("cost_centers.id", ondelete="SET NULL"),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class BillingAdjustment(Base):
    __tablename__ = "billing_adjustments"
    __table_args__ = (
        sa.Index("ix_billing_adjustments_period", "billing_period_id"),
        sa.Index("ix_billing_adjustments_workspace", "workspace_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    billing_period_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("billing_periods.id", ondelete="CASCADE"),
        nullable=False,
    )
    adjustment_type: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    amount_usd: Mapped[Decimal] = mapped_column(sa.Numeric(14, 6), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    reference_id: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


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
    net_cost_usd: Mapped[Decimal | None] = mapped_column(sa.Numeric(14, 6), nullable=True)
    currency: Mapped[str] = mapped_column(
        sa.String(3), nullable=False, server_default=sa.text("'USD'")
    )
    exchange_rate_to_usd: Mapped[Decimal] = mapped_column(
        sa.Numeric(12, 6), nullable=False, server_default=sa.text("1.0")
    )
    snapshot_hash: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class ChargebackRule(Base):
    __tablename__ = "chargeback_rules"
    __table_args__ = (sa.Index("ix_chargeback_rules_workspace", "workspace_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    allocation_type: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    dimension: Mapped[str] = mapped_column(sa.Text, nullable=False)
    weight: Mapped[Decimal] = mapped_column(sa.Numeric(6, 4), nullable=False)
    cost_center_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("cost_centers.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class UsageSnapshot(Base):
    __tablename__ = "usage_snapshots"
    __table_args__ = (sa.Index("ix_usage_snapshots_period", "billing_period_id"),)

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
