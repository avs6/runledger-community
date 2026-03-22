"""Add email_verified and email_verify_token to users.

Revision ID: 020
Revises: 019
Create Date: 2026-03-22
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("email_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("email_verify_token", sa.String(64), nullable=True),
    )
    op.create_index("ix_users_email_verify_token", "users", ["email_verify_token"])


def downgrade() -> None:
    op.drop_index("ix_users_email_verify_token", table_name="users")
    op.drop_column("users", "email_verify_token")
    op.drop_column("users", "email_verified")
