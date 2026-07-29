"""049 — provider_pricing: freeform tags + display name

Adds model metadata so a pricing row can be labelled (embedding / reasoning / coding /
custom tags) and given a friendly display name. Populated by the YAML import.

Revision ID: 049
Revises: 048
Create Date: 2026-07-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "049"
down_revision = "048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "ALTER TABLE provider_pricing ADD COLUMN IF NOT EXISTS "
            "tags JSONB NOT NULL DEFAULT '[]'::jsonb"
        )
    )
    op.execute(
        sa.text("ALTER TABLE provider_pricing ADD COLUMN IF NOT EXISTS display_name TEXT NULL")
    )


def downgrade() -> None:
    op.execute(sa.text("ALTER TABLE provider_pricing DROP COLUMN IF EXISTS display_name"))
    op.execute(sa.text("ALTER TABLE provider_pricing DROP COLUMN IF EXISTS tags"))
