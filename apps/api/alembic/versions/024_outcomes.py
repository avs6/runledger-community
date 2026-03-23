"""Add outcomes and outcome_rollups_daily tables.

Revision ID: 024
Revises: 023
Create Date: 2026-03-22
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "outcomes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", UUID(as_uuid=True), nullable=True),
        sa.Column("session_id", sa.Text, nullable=True),
        sa.Column("end_user_id", sa.Text, nullable=True),
        sa.Column("outcome_type", sa.Text, nullable=False),
        sa.Column("success", sa.Boolean, nullable=False),
        sa.Column("value_usd", sa.Numeric(14, 4), nullable=True),
        sa.Column("labels", JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("ix_outcomes_workspace", "outcomes", ["workspace_id", "created_at"])
    op.create_index("ix_outcomes_run", "outcomes", ["run_id"])
    op.create_index("ix_outcomes_type", "outcomes", ["workspace_id", "outcome_type"])
    op.create_index("ix_outcomes_end_user", "outcomes", ["workspace_id", "end_user_id"])

    op.create_table(
        "outcome_rollups_daily",
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("day", sa.Date, nullable=False),
        sa.Column("outcome_type", sa.Text, nullable=False),
        sa.Column("success_rate", sa.Numeric(6, 4), nullable=False),
        sa.Column("count", sa.Integer, nullable=False),
        sa.Column("total_cost_usd", sa.Numeric(14, 6), nullable=False),
        sa.Column("cost_per_success_usd", sa.Numeric(14, 6), nullable=False),
        sa.Column("total_value_usd", sa.Numeric(14, 4), nullable=True),
        sa.Column("roi", sa.Numeric(10, 4), nullable=True),
    )
    op.create_primary_key(
        "pk_outcome_rollups_daily",
        "outcome_rollups_daily",
        ["workspace_id", "day", "outcome_type"],
    )


def downgrade() -> None:
    op.drop_table("outcome_rollups_daily")
    op.drop_index("ix_outcomes_end_user", table_name="outcomes")
    op.drop_index("ix_outcomes_type", table_name="outcomes")
    op.drop_index("ix_outcomes_run", table_name="outcomes")
    op.drop_index("ix_outcomes_workspace", table_name="outcomes")
    op.drop_table("outcomes")
