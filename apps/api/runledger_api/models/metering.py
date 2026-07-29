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
    source: Mapped[str] = mapped_column(
        sa.String(32), nullable=False, server_default=sa.text("'manual'")
    )
    # Freeform metadata (Phase: pricing import). e.g. ["reasoning", "coding", "embedding"].
    tags: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")
    )
    display_name: Mapped[str | None] = mapped_column(sa.Text, nullable=True)


_SYNC_CONFIG_SINGLETON_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class PricingSyncConfig(Base):
    """
    Singleton row (id = 00000000-0000-0000-0000-000000000001) that controls
    the catalog pricing sync beat task.  Always exactly one row, seeded by
    migration 041.
    """

    __tablename__ = "pricing_sync_config"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    sync_enabled: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )
    excluded_providers: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")
    )
    excluded_models: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")
    )
    force_update: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )
    last_sync_at: Mapped[datetime | None] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True
    )
    last_sync_result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    updated_by: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class PricingContract(Base):
    __tablename__ = "pricing_contracts"
    __table_args__ = (
        sa.Index("ix_pricing_contracts_workspace", "workspace_id", "provider", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    provider: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    model: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)
    discount_pct: Mapped[Decimal | None] = mapped_column(sa.Numeric(6, 4), nullable=True)
    fixed_input_per_1m: Mapped[Decimal | None] = mapped_column(sa.Numeric(14, 8), nullable=True)
    fixed_output_per_1m: Mapped[Decimal | None] = mapped_column(sa.Numeric(14, 8), nullable=True)
    effective_from: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=False)
    effective_until: Mapped[datetime | None] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class PricingCredit(Base):
    __tablename__ = "pricing_credits"
    __table_args__ = (
        sa.Index("ix_pricing_credits_workspace", "workspace_id", "is_active", "priority"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    credit_type: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    amount_usd: Mapped[Decimal] = mapped_column(sa.Numeric(14, 6), nullable=False)
    remaining_usd: Mapped[Decimal] = mapped_column(sa.Numeric(14, 6), nullable=False)
    source: Mapped[str] = mapped_column(
        sa.String(32), nullable=False, server_default=sa.text("'manual'")
    )
    effective_from: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=False)
    effective_until: Mapped[datetime | None] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True
    )
    priority: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("100"))
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )
    created_by: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
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
