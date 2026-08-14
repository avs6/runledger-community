"""083 - auto approval policies

Revision ID: 083
Revises: 082
Create Date: 2026-08-14 17:20:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "083"
down_revision = "082"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auto_approval_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_type", sa.Text(), nullable=False),
        sa.Column("condition", sa.Text(), nullable=False),
        sa.Column("created_by", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_auto_approval_policies_workspace_type",
        "auto_approval_policies",
        ["workspace_id", "request_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_auto_approval_policies_workspace_type", table_name="auto_approval_policies")
    op.drop_table("auto_approval_policies")
