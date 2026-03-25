"""Add pricing_sync_config table — singleton row controlling catalog sync behaviour.

Revision ID: 041
Revises: 040
Create Date: 2026-03-24
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision = "041"
down_revision = "040"
branch_labels = None
depends_on = None

# Stable singleton ID so callers can always GET/PUT this one row
_SINGLETON_ID = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    op.create_table(
        "pricing_sync_config",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        # Master on/off — when False the beat task exits immediately
        sa.Column(
            "sync_enabled",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        # JSON arrays of strings: ["mistral", "google"]
        sa.Column(
            "excluded_providers",
            JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        # JSON arrays of exact model strings: ["gpt-4", "claude-3-opus-20240229"]
        sa.Column(
            "excluded_models",
            JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        # When True, sync will UPDATE existing catalog rows (re-price)
        sa.Column(
            "force_update",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        # Audit trail
        sa.Column("last_sync_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_sync_result", JSONB, nullable=True),
        sa.Column("updated_by", sa.Text, nullable=True),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    # Seed the singleton row
    op.execute(
        f"INSERT INTO pricing_sync_config (id) VALUES ('{_SINGLETON_ID}')"
    )


def downgrade() -> None:
    op.drop_table("pricing_sync_config")
