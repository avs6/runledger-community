"""029_retention_policies

Revision ID: 029
Revises: 028
Create Date: 2026-03-23
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "029"
down_revision = "028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "retention_policies",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "workspace_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("resource_type", sa.Text, nullable=False),  # runs|spans|payloads|provider_calls
        sa.Column("action", sa.Text, nullable=False),  # delete|scrub
        sa.Column(
            "scope", sa.Text, nullable=False, server_default=sa.text("'workspace'")
        ),  # workspace|end_user
        sa.Column("scope_value", sa.Text, nullable=True),  # end_user_id when scope=end_user
        sa.Column("max_age_days", sa.Integer, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("TRUE")),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("last_run_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_purged_count", sa.Integer, nullable=True),
    )
    op.create_index("ix_retention_policies_workspace", "retention_policies", ["workspace_id"])
    op.create_index(
        "ix_retention_policies_active", "retention_policies", ["workspace_id", "is_active"]
    )


def downgrade() -> None:
    op.drop_index("ix_retention_policies_active", table_name="retention_policies")
    op.drop_index("ix_retention_policies_workspace", table_name="retention_policies")
    op.drop_table("retention_policies")
