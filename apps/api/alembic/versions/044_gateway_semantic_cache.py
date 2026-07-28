"""044 — Gateway route: semantic_cache_enabled toggle

Revision ID: 044
Revises: 043
Create Date: 2026-07-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "044"
down_revision = "043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "ALTER TABLE gateway_routes ADD COLUMN IF NOT EXISTS "
            "semantic_cache_enabled BOOLEAN NOT NULL DEFAULT FALSE"
        )
    )


def downgrade() -> None:
    op.execute(sa.text("ALTER TABLE gateway_routes DROP COLUMN IF EXISTS semantic_cache_enabled"))
