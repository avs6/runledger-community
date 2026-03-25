"""Add pricing intelligence: contracts, credits, and source column on provider_pricing.

Revision ID: 040
Revises: 039
Create Date: 2026-03-24
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "040"
down_revision = "039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add source column to provider_pricing
    op.add_column(
        "provider_pricing",
        sa.Column(
            "source",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'manual'"),
        ),
    )

    # 2. Create pricing_contracts table
    op.create_table(
        "pricing_contracts",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("model", sa.String(128), nullable=True),
        sa.Column("discount_pct", sa.Numeric(6, 4), nullable=True),
        sa.Column("fixed_input_per_1m", sa.Numeric(14, 8), nullable=True),
        sa.Column("fixed_output_per_1m", sa.Numeric(14, 8), nullable=True),
        sa.Column("effective_from", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("effective_until", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_by", sa.Text, nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index(
        "ix_pricing_contracts_workspace",
        "pricing_contracts",
        ["workspace_id", "provider", "is_active"],
    )

    # 3. Create pricing_credits table
    op.create_table(
        "pricing_credits",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("credit_type", sa.String(32), nullable=False),
        sa.Column("amount_usd", sa.Numeric(14, 6), nullable=False),
        sa.Column("remaining_usd", sa.Numeric(14, 6), nullable=False),
        sa.Column(
            "source",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'manual'"),
        ),
        sa.Column("effective_from", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("effective_until", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "priority",
            sa.Integer,
            nullable=False,
            server_default=sa.text("100"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("created_by", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index(
        "ix_pricing_credits_workspace",
        "pricing_credits",
        ["workspace_id", "is_active", "priority"],
    )


def downgrade() -> None:
    op.drop_index("ix_pricing_credits_workspace", table_name="pricing_credits")
    op.drop_table("pricing_credits")
    op.drop_index("ix_pricing_contracts_workspace", table_name="pricing_contracts")
    op.drop_table("pricing_contracts")
    op.drop_column("provider_pricing", "source")
