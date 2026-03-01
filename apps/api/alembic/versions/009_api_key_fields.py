"""Add is_session and created_by to api_keys.

Revision ID: 009
Revises: 008
Create Date: 2026-03-01
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "009"
down_revision: str | None = "008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "api_keys",
        sa.Column(
            "is_session",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column("api_keys", sa.Column("created_by", sa.Text(), nullable=True))

    # Back-fill: mark all existing "dashboard-session" keys as session keys
    op.execute("UPDATE api_keys SET is_session = true WHERE name = 'dashboard-session'")


def downgrade() -> None:
    op.drop_column("api_keys", "created_by")
    op.drop_column("api_keys", "is_session")
