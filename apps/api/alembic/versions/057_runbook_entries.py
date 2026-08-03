"""057 - add runbook_entries table for agent incident summaries

Revision ID: 057
Revises: 056
Create Date: 2026-08-03
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "057"
down_revision = "056"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "runbook_entries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("agent_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("severity", sa.String(20), nullable=False, server_default="info"),
        sa.Column("summary", JSONB, nullable=False),
        sa.Column(
            "generated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_runbook_entries_workspace",
        "runbook_entries",
        ["workspace_id", "generated_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_runbook_entries_workspace", table_name="runbook_entries")
    op.drop_table("runbook_entries")
