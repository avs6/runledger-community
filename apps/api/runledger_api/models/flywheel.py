"""
ORM models for the optimization flywheel (Phase 7).

The flywheel closes the cost x quality loop: it reads the (config, cost, quality, outcome)
tuples RunLedger already records and, per traffic segment, finds the cheapest configuration
that still holds a customer-defined quality SLA — then proposes (or auto-applies) it.

  FlywheelSettings        — per-workspace SLA + behaviour (apply mode, quality metric,
                            segmentation, action space). Default off / approval-gated.
  FlywheelRecommendation  — one proposal for a segment, with status tracking for
                            approval / auto-apply / rollback.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from runledger_api.core.db import Base


class FlywheelSettings(Base):
    """Per-workspace flywheel configuration (singleton keyed by workspace)."""

    __tablename__ = "flywheel_settings"

    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    enabled: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )
    # approval — propose only, human clicks Apply
    # auto     — apply guardrail-passing proposals automatically, auto-rollback on SLA breach
    # off      — analysis runs but nothing is applied
    apply_mode: Mapped[str] = mapped_column(
        sa.String(16), nullable=False, server_default="approval"
    )
    # {"type": "outcome_success" | "eval_score" | "blend", "weight": 0.5, "evaluator": null}
    quality_metric: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text('\'{"type": "blend", "weight": 0.5}\'')
    )
    min_quality: Mapped[Decimal] = mapped_column(
        sa.Numeric(6, 4), nullable=False, server_default="0.8"
    )
    # outcome_type | task_class | alias
    segment_by: Mapped[str] = mapped_column(
        sa.String(24), nullable=False, server_default="outcome_type"
    )
    action_space: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=sa.text(
            '\'["model", "stages", "compression_rate", "cache_threshold", "routing"]\''
        ),
    )
    min_sample_size: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default="20")
    lookback_days: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default="30")
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class FlywheelRecommendation(Base):
    """A single per-segment recommendation produced by the flywheel."""

    __tablename__ = "flywheel_recommendations"
    __table_args__ = (
        sa.Index("ix_flywheel_recs_workspace", "workspace_id", "status", "created_at"),
        sa.Index("ix_flywheel_recs_segment", "workspace_id", "segment_by", "segment_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    segment_by: Mapped[str] = mapped_column(sa.String(24), nullable=False)
    segment_key: Mapped[str] = mapped_column(sa.Text, nullable=False)
    # switch    — a cheaper observed config holds the SLA; move to it
    # explore   — a cheaper config looks promising but lacks data; canary to gather it
    # guardrail — the current config breaches the SLA; upgrade needed
    kind: Mapped[str] = mapped_column(sa.String(16), nullable=False, server_default="switch")
    current_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'{}'")
    )
    proposed_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'{}'")
    )
    est_cost_delta_pct: Mapped[Decimal | None] = mapped_column(sa.Numeric(8, 4), nullable=True)
    est_cost_delta_per_req: Mapped[Decimal | None] = mapped_column(sa.Numeric(14, 8), nullable=True)
    current_quality: Mapped[Decimal | None] = mapped_column(sa.Numeric(6, 4), nullable=True)
    proposed_quality: Mapped[Decimal | None] = mapped_column(sa.Numeric(6, 4), nullable=True)
    min_quality: Mapped[Decimal] = mapped_column(sa.Numeric(6, 4), nullable=False)
    sample_size: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default="0")
    confidence: Mapped[str] = mapped_column(sa.String(8), nullable=False, server_default="low")
    rationale: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    status: Mapped[str] = mapped_column(sa.String(16), nullable=False, server_default="pending")
    apply_mode: Mapped[str] = mapped_column(
        sa.String(16), nullable=False, server_default="approval"
    )
    applied_route_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
    applied_at: Mapped[datetime | None] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=True)
