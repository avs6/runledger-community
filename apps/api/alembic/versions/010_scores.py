"""Add score_events and score_rollups_daily tables.

Revision ID: 010
Revises: 009
Create Date: 2026-03-01
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision: str = "010"
down_revision: str | None = "009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "score_events",
        sa.Column("id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("run_id", PGUUID(as_uuid=True), nullable=True),
        sa.Column("span_id", PGUUID(as_uuid=True), nullable=True),
        sa.Column("session_id", sa.Text(), nullable=True),
        sa.Column("end_user_id", sa.Text(), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("value", sa.Numeric(8, 4), nullable=False),
        sa.Column("label", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=False, server_default="human"),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_score_events_workspace", "score_events", ["workspace_id", "created_at"]
    )
    op.create_index("ix_score_events_run", "score_events", ["run_id"])
    op.create_index(
        "ix_score_events_name", "score_events", ["workspace_id", "name"]
    )

    op.create_table(
        "score_rollups_daily",
        sa.Column("workspace_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("score_name", sa.Text(), nullable=False),
        sa.Column("feature_tag", sa.Text(), nullable=False, server_default=""),
        sa.Column("model", sa.Text(), nullable=False, server_default=""),
        sa.Column("deployment_version", sa.Text(), nullable=False, server_default=""),
        sa.Column("avg_value", sa.Numeric(8, 4), nullable=False),
        sa.Column("p50", sa.Numeric(8, 4), nullable=False),
        sa.Column("p90", sa.Numeric(8, 4), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint(
            "workspace_id", "day", "score_name", "feature_tag", "model", "deployment_version"
        ),
    )


def downgrade() -> None:
    op.drop_table("score_rollups_daily")
    op.drop_index("ix_score_events_name", table_name="score_events")
    op.drop_index("ix_score_events_run", table_name="score_events")
    op.drop_index("ix_score_events_workspace", table_name="score_events")
    op.drop_table("score_events")
