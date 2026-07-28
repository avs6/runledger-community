"""048 — Optimization flywheel: settings + recommendations (Phase 7)

Two tables:
  flywheel_settings        — per-workspace SLA + how the flywheel behaves
                             (apply mode, quality metric, segmentation, action space).
  flywheel_recommendations — the loop's output: per-segment proposals to move cost
                             down while holding the quality floor, with status tracking
                             for approval / auto-apply / rollback.

Revision ID: 048
Revises: 047
Create Date: 2026-07-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision = "048"
down_revision = "047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "flywheel_settings",
        sa.Column("workspace_id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        # approval | auto | off
        sa.Column("apply_mode", sa.String(16), nullable=False, server_default="approval"),
        # {"type": "outcome_success" | "eval_score" | "blend", "weight": 0.5, "evaluator": null}
        sa.Column(
            "quality_metric",
            JSONB,
            nullable=False,
            server_default=sa.text('\'{"type": "blend", "weight": 0.5}\''),
        ),
        sa.Column("min_quality", sa.Numeric(6, 4), nullable=False, server_default="0.8"),
        # outcome_type | task_class | alias
        sa.Column("segment_by", sa.String(24), nullable=False, server_default="outcome_type"),
        # which config dimensions the flywheel may tune
        sa.Column(
            "action_space",
            JSONB,
            nullable=False,
            server_default=sa.text(
                '\'["model", "stages", "compression_rate", "cache_threshold", "routing"]\''
            ),
        ),
        sa.Column("min_sample_size", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("lookback_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )

    op.create_table(
        "flywheel_recommendations",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("segment_by", sa.String(24), nullable=False),
        sa.Column("segment_key", sa.Text(), nullable=False),
        # switch | explore | guardrail
        sa.Column("kind", sa.String(16), nullable=False, server_default="switch"),
        sa.Column("current_config", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("proposed_config", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("est_cost_delta_pct", sa.Numeric(8, 4), nullable=True),
        sa.Column("est_cost_delta_per_req", sa.Numeric(14, 8), nullable=True),
        sa.Column("current_quality", sa.Numeric(6, 4), nullable=True),
        sa.Column("proposed_quality", sa.Numeric(6, 4), nullable=True),
        sa.Column("min_quality", sa.Numeric(6, 4), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default="0"),
        # high | medium | low
        sa.Column("confidence", sa.String(8), nullable=False, server_default="low"),
        sa.Column("rationale", sa.Text(), nullable=True),
        # pending | applied | dismissed | rolled_back | superseded
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        # how it was (or would be) applied: approval | auto
        sa.Column("apply_mode", sa.String(16), nullable=False, server_default="approval"),
        # gateway_routes.id when the proposal was applied to a concrete route
        sa.Column("applied_route_id", PGUUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("applied_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_flywheel_recs_workspace",
        "flywheel_recommendations",
        ["workspace_id", "status", "created_at"],
    )
    op.create_index(
        "ix_flywheel_recs_segment",
        "flywheel_recommendations",
        ["workspace_id", "segment_by", "segment_key"],
    )


def downgrade() -> None:
    op.drop_index("ix_flywheel_recs_segment", table_name="flywheel_recommendations")
    op.drop_index("ix_flywheel_recs_workspace", table_name="flywheel_recommendations")
    op.drop_table("flywheel_recommendations")
    op.drop_table("flywheel_settings")
