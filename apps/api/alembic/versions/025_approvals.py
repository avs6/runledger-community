"""Add approvals table for policy workflow governance.

Revision ID: 025
Revises: 024
Create Date: 2026-03-23
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "approvals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("request_type", sa.Text, nullable=False),
        sa.Column("request", JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.Text, nullable=False, server_default="pending"),
        sa.Column("requested_by", sa.Text, nullable=True),
        sa.Column("decided_by", sa.Text, nullable=True),
        sa.Column(
            "decided_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column("decision_note", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("ix_approvals_workspace_status", "approvals", ["workspace_id", "status"])
    op.create_index("ix_approvals_workspace_type", "approvals", ["workspace_id", "request_type"])


def downgrade() -> None:
    op.drop_index("ix_approvals_workspace_type", table_name="approvals")
    op.drop_index("ix_approvals_workspace_status", table_name="approvals")
    op.drop_table("approvals")
