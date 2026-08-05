"""Add adaptive alert threshold columns to alert_rules.

Revision ID: 060
Revises: 059
Create Date: 2026-08-05
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "060"
down_revision = "059"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "alert_rules",
        sa.Column("use_adaptive", sa.Boolean, server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "alert_rules",
        sa.Column("adaptive_baseline", sa.Numeric(14, 6), nullable=True),
    )
    op.add_column(
        "alert_rules",
        sa.Column("adaptive_upper", sa.Numeric(14, 6), nullable=True),
    )
    op.add_column(
        "alert_rules",
        sa.Column("adaptive_lower", sa.Numeric(14, 6), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("alert_rules", "adaptive_lower")
    op.drop_column("alert_rules", "adaptive_upper")
    op.drop_column("alert_rules", "adaptive_baseline")
    op.drop_column("alert_rules", "use_adaptive")
