"""055 - add provider call savings attribution

Revision ID: 055
Revises: 054
Create Date: 2026-07-30
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "055"
down_revision = "054"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("provider_calls", sa.Column("savings_usd", sa.Numeric(14, 8), nullable=True))
    op.add_column(
        "provider_calls", sa.Column("savings_category", sa.String(length=64), nullable=True)
    )
    op.add_column("provider_calls", sa.Column("savings_reason", sa.Text(), nullable=True))
    op.create_index(
        "ix_provider_calls_savings_category",
        "provider_calls",
        ["workspace_id", "savings_category", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_provider_calls_savings_category", table_name="provider_calls")
    op.drop_column("provider_calls", "savings_reason")
    op.drop_column("provider_calls", "savings_category")
    op.drop_column("provider_calls", "savings_usd")
