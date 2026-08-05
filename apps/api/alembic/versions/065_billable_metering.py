"""Add is_billable to provider_calls and billable_cost_usd to usage_daily.

Revision ID: 065
Revises: 064
"""

import sqlalchemy as sa
from alembic import op

revision = "065"
down_revision = "064"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "provider_calls",
        sa.Column(
            "is_billable",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "usage_daily",
        sa.Column(
            "billable_cost_usd",
            sa.Numeric(18, 8),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )


def downgrade() -> None:
    op.drop_column("usage_daily", "billable_cost_usd")
    op.drop_column("provider_calls", "is_billable")
