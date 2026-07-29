"""051 — add provider_pricing.source and gateway_requests.decision_reason

Both columns are on their models but no migration ever created them, so a from-scratch
database was missing them (the pricing import 500'd on `provider_pricing.source`, and
gateway request logging would fail on `decision_reason`). Idempotent (IF NOT EXISTS).

Revision ID: 051
Revises: 050
Create Date: 2026-07-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "051"
down_revision = "050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "ALTER TABLE provider_pricing ADD COLUMN IF NOT EXISTS "
            "source VARCHAR(32) NOT NULL DEFAULT 'manual'"
        )
    )
    op.execute(
        sa.text("ALTER TABLE gateway_requests ADD COLUMN IF NOT EXISTS decision_reason TEXT NULL")
    )


def downgrade() -> None:
    op.execute(sa.text("ALTER TABLE gateway_requests DROP COLUMN IF EXISTS decision_reason"))
    op.execute(sa.text("ALTER TABLE provider_pricing DROP COLUMN IF EXISTS source"))
