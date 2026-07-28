"""046 — Gateway route: intelligent routing toggle + config

Revision ID: 046
Revises: 045
Create Date: 2026-07-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "046"
down_revision = "045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "ALTER TABLE gateway_routes ADD COLUMN IF NOT EXISTS "
            "intelligent_routing_enabled BOOLEAN NOT NULL DEFAULT FALSE"
        )
    )
    op.execute(
        sa.text("ALTER TABLE gateway_routes ADD COLUMN IF NOT EXISTS routing_config JSONB NULL")
    )


def downgrade() -> None:
    op.execute(sa.text("ALTER TABLE gateway_routes DROP COLUMN IF EXISTS routing_config"))
    op.execute(
        sa.text("ALTER TABLE gateway_routes DROP COLUMN IF EXISTS intelligent_routing_enabled")
    )
