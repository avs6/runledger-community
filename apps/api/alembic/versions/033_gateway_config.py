"""033 — Add config JSONB to gateway_routes for provider-specific settings.

Revision ID: 033
Revises: 032
Create Date: 2026-03-23
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "033"
down_revision = "032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TABLE gateway_routes ADD COLUMN IF NOT EXISTS config JSONB"))


def downgrade() -> None:
    op.execute(sa.text("ALTER TABLE gateway_routes DROP COLUMN IF EXISTS config"))
