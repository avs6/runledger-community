"""Add status column to chargeback_rules for approval gating.

Revision ID: 038
Revises: 037
Create Date: 2026-03-24
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "038"
down_revision = "037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "chargeback_rules",
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
    )
    op.create_index(
        "ix_chargeback_rules_status",
        "chargeback_rules",
        ["workspace_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_chargeback_rules_status", table_name="chargeback_rules")
    op.drop_column("chargeback_rules", "status")
