"""ORM models for business outcomes and daily rollups."""

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


class Outcome(Base):
    """A business outcome linked to an agent run/session/end-user."""

    __tablename__ = "outcomes"
    __table_args__ = (
        sa.Index("ix_outcomes_workspace", "workspace_id", "created_at"),
        sa.Index("ix_outcomes_run", "run_id"),
        sa.Index("ix_outcomes_type", "workspace_id", "outcome_type"),
        sa.Index("ix_outcomes_end_user", "workspace_id", "end_user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    run_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    session_id: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    end_user_id: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    outcome_type: Mapped[str] = mapped_column(sa.Text, nullable=False)
    success: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    value_usd: Mapped[Decimal | None] = mapped_column(sa.Numeric(14, 4), nullable=True)
    labels: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'{}'")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class OutcomeRollupDaily(Base):
    """Daily aggregated outcome metrics per workspace and outcome type."""

    __tablename__ = "outcome_rollups_daily"
    __table_args__ = (
        sa.PrimaryKeyConstraint("workspace_id", "day", "outcome_type"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    day: Mapped[date] = mapped_column(sa.Date, nullable=False)
    outcome_type: Mapped[str] = mapped_column(sa.Text, nullable=False)
    success_rate: Mapped[Decimal] = mapped_column(sa.Numeric(6, 4), nullable=False)
    count: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    total_cost_usd: Mapped[Decimal] = mapped_column(sa.Numeric(14, 6), nullable=False)
    cost_per_success_usd: Mapped[Decimal] = mapped_column(sa.Numeric(14, 6), nullable=False)
    total_value_usd: Mapped[Decimal | None] = mapped_column(sa.Numeric(14, 4), nullable=True)
    roi: Mapped[Decimal | None] = mapped_column(sa.Numeric(10, 4), nullable=True)
