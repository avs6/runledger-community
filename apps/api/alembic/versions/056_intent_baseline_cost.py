"""056 - add intent classification + optimization attribution fields

Revision ID: 056
Revises: 055
Create Date: 2026-08-03
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "056"
down_revision = "055"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent_runs",
        sa.Column("intent", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_agent_runs_intent",
        "agent_runs",
        ["workspace_id", "intent"],
        unique=False,
    )

    op.add_column(
        "provider_calls",
        sa.Column("baseline_cost_usd", sa.Numeric(14, 8), nullable=True),
    )
    op.add_column(
        "provider_calls",
        sa.Column("optimization_applied", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_provider_calls_optimization",
        "provider_calls",
        ["workspace_id", "optimization_applied", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_provider_calls_optimization", table_name="provider_calls")
    op.drop_column("provider_calls", "optimization_applied")
    op.drop_column("provider_calls", "baseline_cost_usd")
    op.drop_index("ix_agent_runs_intent", table_name="agent_runs")
    op.drop_column("agent_runs", "intent")
