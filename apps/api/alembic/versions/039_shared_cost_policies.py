"""Add shared_cost_policies table for cross-tenant cost pool splitting.

Revision ID: 039
Revises: 038
Create Date: 2026-03-24
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID

# revision identifiers
revision = "039"
down_revision = "038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shared_cost_policies",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        # formula_type: equal_split | proportional | fixed_weight
        sa.Column("formula_type", sa.String(32), nullable=False),
        # JSONB list of allocation targets:
        # [{cost_center_id, label, weight?, denominator_value?}]
        sa.Column("allocations", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
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
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index(
        "ix_shared_cost_policies_workspace",
        "shared_cost_policies",
        ["workspace_id", "is_active"],
    )


def downgrade() -> None:
    op.drop_index("ix_shared_cost_policies_workspace", table_name="shared_cost_policies")
    op.drop_table("shared_cost_policies")
