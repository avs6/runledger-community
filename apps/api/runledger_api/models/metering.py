"""
ORM models for metering tables: provider pricing, usage rollups, data quality.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from runledger_api.core.db import Base


class ProviderPricing(Base):
    """
    Effective-dated pricing for LLM providers.

    ``workspace_id=None`` is a global default; a non-null ``workspace_id``
    is a workspace-specific override (checked first at cost-calculation time).
    """

    __tablename__ = "provider_pricing"
    __table_args__ = (
        sa.Index("ix_provider_pricing_lookup", "provider", "model", "effective_from"),
        sa.Index("ix_provider_pricing_workspace", "workspace_id", "provider", "model"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    provider: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    model: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    input_cost_per_1m: Mapped[Decimal] = mapped_column(sa.Numeric(14, 8), nullable=False)
    output_cost_per_1m: Mapped[Decimal] = mapped_column(sa.Numeric(14, 8), nullable=False)
    # NULL means default to input_cost_per_1m * 0.5 at query time
    cached_input_cost_per_1m: Mapped[Decimal | None] = mapped_column(
        sa.Numeric(14, 8), nullable=True
    )
    effective_from: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True
    )
    # NULL = global; non-null = workspace override
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class UsageHourly(Base):
    """
    Hourly rollup of provider_call aggregates.
    Fully recomputed for any given hour window by rollup_hourly_worker.
    """

    __tablename__ = "usage_hourly"
    __table_args__ = (
        sa.Index("ix_usage_hourly_workspace_hour", "workspace_id", "hour"),
        sa.Index("ix_usage_hourly_model", "workspace_id", "model", "hour"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    model: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    provider: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    feature_tag: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    end_user_id: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    hour: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=False)
    input_tokens: Mapped[int] = mapped_column(sa.BigInteger, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(sa.BigInteger, nullable=False, default=0)
    cost_usd: Mapped[Decimal] = mapped_column(sa.Numeric(18, 8), nullable=False, default=Decimal(0))
    run_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    call_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    computed_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class UsageDaily(Base):
    """
    Daily rollup aggregated from usage_hourly by rollup_daily_worker.
    """

    __tablename__ = "usage_daily"
    __table_args__ = (sa.Index("ix_usage_daily_workspace_day", "workspace_id", "day"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    model: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    provider: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    feature_tag: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    end_user_id: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    day: Mapped[date] = mapped_column(sa.Date, nullable=False)
    input_tokens: Mapped[int] = mapped_column(sa.BigInteger, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(sa.BigInteger, nullable=False, default=0)
    cost_usd: Mapped[Decimal] = mapped_column(sa.Numeric(18, 8), nullable=False, default=Decimal(0))
    run_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    call_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    computed_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class DataQualityIssue(Base):
    """
    Flags provider_calls with missing or suspicious metering data.
    Written by data_quality_worker; cleared (resolved=True) after correction.
    """

    __tablename__ = "data_quality_issues"
    __table_args__ = (
        sa.Index("ix_data_quality_workspace", "workspace_id", "detected_at"),
        sa.Index("ix_data_quality_provider_call", "provider_call_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    provider_call_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    run_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    issue_type: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    resolved: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    detected_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
