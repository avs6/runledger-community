"""Add runtime_enforcement to tool_registry.

Revision ID: 016
Revises: 015
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tool_registry",
        sa.Column(
            "runtime_enforcement",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
    )


def downgrade() -> None:
    op.drop_column("tool_registry", "runtime_enforcement")
