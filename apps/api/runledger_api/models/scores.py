"""ORM models for quality score events and daily rollups."""

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


class ScoreEvent(Base):
    """A quality score attached to a run, span, session, or end-user."""

    __tablename__ = "score_events"
    __table_args__ = (
        sa.Index("ix_score_events_workspace", "workspace_id", "created_at"),
        sa.Index("ix_score_events_run", "run_id"),
        sa.Index("ix_score_events_name", "workspace_id", "name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    run_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    span_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    session_id: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    end_user_id: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    value: Mapped[Decimal] = mapped_column(sa.Numeric(8, 4), nullable=False)
    label: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    source: Mapped[str] = mapped_column(sa.Text, nullable=False, server_default="human")
    confidence: Mapped[Decimal | None] = mapped_column(sa.Numeric(4, 3), nullable=True)
    evidence: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class ScoreRollupDaily(Base):
    """Daily aggregated quality score rollup per workspace / score name / dimension."""

    __tablename__ = "score_rollups_daily"
    __table_args__ = (
        sa.PrimaryKeyConstraint(
            "workspace_id", "day", "score_name", "feature_tag", "model", "deployment_version"
        ),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    day: Mapped[date] = mapped_column(sa.Date, nullable=False)
    score_name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    feature_tag: Mapped[str] = mapped_column(sa.Text, nullable=False, server_default="")
    model: Mapped[str] = mapped_column(sa.Text, nullable=False, server_default="")
    deployment_version: Mapped[str] = mapped_column(sa.Text, nullable=False, server_default="")
    avg_value: Mapped[Decimal] = mapped_column(sa.Numeric(8, 4), nullable=False)
    p50: Mapped[Decimal] = mapped_column(sa.Numeric(8, 4), nullable=False)
    p90: Mapped[Decimal] = mapped_column(sa.Numeric(8, 4), nullable=False)
    sample_count: Mapped[int] = mapped_column(sa.Integer, nullable=False)
