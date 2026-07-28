"""047 — Gateway request: config fingerprint + segment key (Phase 7 flywheel)

Stamps each gateway request with the optimization configuration it actually ran
under (model/tier + which stages were on + compression rate + cache/routing) and a
coarse segment key, so the flywheel can group traffic by (segment, config) and learn
the cheapest configuration that still holds the quality SLA.

Revision ID: 047
Revises: 046
Create Date: 2026-07-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "047"
down_revision = "046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text("ALTER TABLE gateway_requests ADD COLUMN IF NOT EXISTS config_fingerprint JSONB NULL")
    )
    op.execute(
        sa.text("ALTER TABLE gateway_requests ADD COLUMN IF NOT EXISTS segment_key TEXT NULL")
    )


def downgrade() -> None:
    op.execute(sa.text("ALTER TABLE gateway_requests DROP COLUMN IF EXISTS segment_key"))
    op.execute(sa.text("ALTER TABLE gateway_requests DROP COLUMN IF EXISTS config_fingerprint"))
