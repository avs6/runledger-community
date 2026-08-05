"""Add budget tiers table and budget_tier_id to api_keys.

Revision ID: 062
Revises: 061
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "062"
down_revision = "061"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "budget_tiers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("max_spend_usd", sa.Numeric(14, 6), nullable=True),
        sa.Column(
            "period_type",
            sa.String(16),
            nullable=False,
            server_default=sa.text("'monthly'"),
        ),
        sa.Column("rpm_limit", sa.Integer, nullable=True),
        sa.Column("tpm_limit", sa.Integer, nullable=True),
        sa.Column("allowed_models", sa.ARRAY(sa.Text), nullable=True),
        sa.Column(
            "is_default",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
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
        sa.UniqueConstraint("workspace_id", "name", name="uq_budget_tiers_ws_name"),
    )
    op.create_index("ix_budget_tiers_workspace", "budget_tiers", ["workspace_id"])

    op.add_column(
        "api_keys",
        sa.Column("budget_tier_id", UUID(as_uuid=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("api_keys", "budget_tier_id")
    op.drop_index("ix_budget_tiers_workspace", table_name="budget_tiers")
    op.drop_table("budget_tiers")
