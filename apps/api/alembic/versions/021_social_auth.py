"""Add firebase_uid to users; make password_hash nullable for social accounts.

Revision ID: 021
Revises: 020
Create Date: 2026-03-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add firebase_uid column
    op.add_column(
        "users",
        sa.Column("firebase_uid", sa.String(128), nullable=True),
    )
    op.create_index("ix_users_firebase_uid", "users", ["firebase_uid"], unique=True)

    # Make password_hash nullable (social login users have no password)
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=True)


def downgrade() -> None:
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=False)
    op.drop_index("ix_users_firebase_uid", table_name="users")
    op.drop_column("users", "firebase_uid")
