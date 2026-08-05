"""Add per-model budget limits table.

Revision ID: 063
Revises: 062
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "063"
down_revision = "062"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_budgets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("api_key_id", UUID(as_uuid=True), nullable=False),
        sa.Column("model_pattern", sa.String(255), nullable=False),
        sa.Column("max_spend_usd", sa.Numeric(14, 6), nullable=True),
        sa.Column(
            "period_type",
            sa.String(16),
            nullable=False,
            server_default=sa.text("'monthly'"),
        ),
        sa.Column("rpm_limit", sa.Integer, nullable=True),
        sa.Column("tpm_limit", sa.Integer, nullable=True),
        sa.Column(
            "action",
            sa.String(16),
            nullable=False,
            server_default=sa.text("'block'"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index("ix_model_budgets_key", "model_budgets", ["api_key_id", "is_active"])


def downgrade() -> None:
    op.drop_index("ix_model_budgets_key", table_name="model_budgets")
    op.drop_table("model_budgets")
