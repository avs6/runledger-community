"""ORM models for replay harness and user anomaly detection."""

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


class UserAnomaly(Base):
    """Nightly anomaly flag: a user whose daily spend exceeds 3σ above their 30d mean."""

    __tablename__ = "user_anomalies"
    __table_args__ = (sa.Index("ix_user_anomalies_workspace_date", "workspace_id", "detected_at"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    end_user_id: Mapped[str] = mapped_column(sa.Text, nullable=False)
    detected_at: Mapped[date] = mapped_column(sa.Date, nullable=False)
    daily_spend: Mapped[Decimal] = mapped_column(sa.Numeric(14, 8), nullable=False)
    mean_spend: Mapped[Decimal] = mapped_column(sa.Numeric(14, 8), nullable=False)
    zscore: Mapped[Decimal] = mapped_column(sa.Numeric(8, 4), nullable=False)
    reason: Mapped[str] = mapped_column(sa.Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class ReplayDataset(Base):
    """Named collection of run IDs used as input for cost-projection experiments."""

    __tablename__ = "replay_datasets"
    __table_args__ = (sa.Index("ix_replay_datasets_workspace", "workspace_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    source: Mapped[str] = mapped_column(sa.Text, nullable=False, default="live_runs")
    run_ids: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class ReplayExperiment(Base):
    """
    Cost-projection experiment: compares a list of model configs against a dataset.

    The worker projects cost using actual token counts × ProviderPricing rates —
    no real LLM calls are made.
    """

    __tablename__ = "replay_experiments"
    __table_args__ = (sa.Index("ix_replay_experiments_workspace", "workspace_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    dataset_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    configs: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(sa.Text, nullable=False, default="pending")
    results: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    estimated_cost_usd: Mapped[Decimal | None] = mapped_column(sa.Numeric(14, 8), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
