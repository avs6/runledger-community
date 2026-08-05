"""Add budget overrides table for temporary budget increases.

Revision ID: 064
Revises: 063
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "064"
down_revision = "063"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "budget_overrides",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("budget_id", UUID(as_uuid=True), nullable=False),
        sa.Column("original_limit_usd", sa.Numeric(14, 6), nullable=False),
        sa.Column("override_limit_usd", sa.Numeric(14, 6), nullable=False),
        sa.Column("starts_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("approved_by", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            sa.String(16),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_budget_overrides_budget", "budget_overrides", ["budget_id", "status"]
    )


def downgrade() -> None:
    op.drop_index("ix_budget_overrides_budget", table_name="budget_overrides")
    op.drop_table("budget_overrides")
