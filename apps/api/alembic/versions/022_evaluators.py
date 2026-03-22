"""Add evaluators table and evaluator_id to score_events.

Revision ID: 022
Revises: 021
Create Date: 2026-03-22
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evaluators",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("type", sa.String(32), nullable=False, server_default="rule"),
        sa.Column("config", JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("last_run_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_run_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("ix_evaluators_workspace", "evaluators", ["workspace_id"])
    op.create_index("ix_evaluators_workspace_name", "evaluators", ["workspace_id", "name"])

    op.add_column(
        "score_events",
        sa.Column("evaluator_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_score_events_evaluator", "score_events", ["evaluator_id"])


def downgrade() -> None:
    op.drop_index("ix_score_events_evaluator", table_name="score_events")
    op.drop_column("score_events", "evaluator_id")
    op.drop_index("ix_evaluators_workspace_name", table_name="evaluators")
    op.drop_index("ix_evaluators_workspace", table_name="evaluators")
    op.drop_table("evaluators")
