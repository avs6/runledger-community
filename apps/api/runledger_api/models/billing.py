"""
ORM models for billing: billing_periods, chargeback_rules, usage_snapshots,
cost_centers, billing_adjustments, shared_cost_policies, cost_allocations.
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
    # direct: the whole cost of the dimension value goes to one cost center (weight 1).
    # shared_weight: the value's cost is split across cost centers by weight.
    direct = "direct"
    shared_weight = "shared_weight"


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
    closed_by: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    reopened_at: Mapped[datetime | None] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=True)
    reopen_reason: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class ChargebackRule(Base):
    """Maps one dimension value to a cost center with a weight.

    Example: dimension="feature_tag", dimension_value="support-triage",
    cost_center_id=<Support>, weight=0.6. The chargeback report's cost-center view
    applies active rules; the sum of active weights for one value is at most 1 and
    any remainder is reported as unassigned.

    status: active | inactive | pending_approval | denied. Approval-gated rules move
    to active only through the approvals flow, decided by someone other than the
    requester.
    """

    __tablename__ = "chargeback_rules"
    __table_args__ = (
        sa.Index("ix_chargeback_rules_workspace", "workspace_id"),
        sa.Index(
            "ix_chargeback_rules_lookup", "workspace_id", "dimension", "dimension_value", "status"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    allocation_type: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    dimension: Mapped[str] = mapped_column(sa.Text, nullable=False)
    dimension_value: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    weight: Mapped[Decimal] = mapped_column(sa.Numeric(6, 4), nullable=False)
    cost_center_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        sa.String(32), nullable=False, server_default=sa.text("'active'")
    )
    approval_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    created_by: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class CostAllocation(Base):
    """One cost center's share of a shared-cost pool applied to a month."""

    __tablename__ = "cost_allocations"
    __table_args__ = (sa.Index("ix_cost_allocations_period", "workspace_id", "period"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    period: Mapped[str] = mapped_column(sa.String(7), nullable=False)  # YYYY-MM
    policy_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("shared_cost_policies.id", ondelete="CASCADE"),
        nullable=False,
    )
    cost_center_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("cost_centers.id", ondelete="SET NULL"),
        nullable=True,
    )
    label: Mapped[str] = mapped_column(sa.Text, nullable=False)
    pool_usd: Mapped[Decimal] = mapped_column(sa.Numeric(14, 6), nullable=False)
    amount_usd: Mapped[Decimal] = mapped_column(sa.Numeric(14, 6), nullable=False)
    created_by: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class SharedCostPolicyFormulaEnum(enum.StrEnum):
    equal_split = "equal_split"
    proportional = "proportional"
    fixed_weight = "fixed_weight"


class SharedCostPolicy(Base):
    """
    Shared-cost policy: defines how a cost pool is split across cost centers.

    formula_type:
      equal_split   — pool / N (equal share for each allocation)
      fixed_weight  — pool * allocation.weight (weights must sum to 1.0)
      proportional  — pool * (allocation.denominator_value / sum_of_all)

    allocations JSONB structure (list):
      [{"cost_center_id": "<uuid>", "label": "...", "weight": 0.4,
        "denominator_value": 1200.0}]
    """

    __tablename__ = "shared_cost_policies"
    __table_args__ = (sa.Index("ix_shared_cost_policies_workspace", "workspace_id", "is_active"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    formula_type: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    allocations: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")
    )
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
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
