"""045 — Gateway route: context compiler toggle + config

Revision ID: 045
Revises: 044
Create Date: 2026-07-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "045"
down_revision = "044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "ALTER TABLE gateway_routes ADD COLUMN IF NOT EXISTS "
            "context_compiler_enabled BOOLEAN NOT NULL DEFAULT FALSE"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE gateway_routes ADD COLUMN IF NOT EXISTS context_compiler_config JSONB NULL"
        )
    )


def downgrade() -> None:
    op.execute(sa.text("ALTER TABLE gateway_routes DROP COLUMN IF EXISTS context_compiler_config"))
    op.execute(sa.text("ALTER TABLE gateway_routes DROP COLUMN IF EXISTS context_compiler_enabled"))
