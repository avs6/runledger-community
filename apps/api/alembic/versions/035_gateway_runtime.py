"""035 — Gateway runtime controls: cost caps, PII redaction, per-user rate limits, health

Revision ID: 035
Revises: 034
Create Date: 2026-03-24
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "035"
down_revision = "034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Cost caps on gateway_routes ────────────────────────────────────────────
    op.execute(
        sa.text(
            "ALTER TABLE gateway_routes ADD COLUMN IF NOT EXISTS "
            "daily_cost_limit_usd NUMERIC(12,4) NULL"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE gateway_routes ADD COLUMN IF NOT EXISTS "
            "monthly_cost_limit_usd NUMERIC(12,4) NULL"
        )
    )

    # ── PII redaction toggle ───────────────────────────────────────────────────
    op.execute(
        sa.text(
            "ALTER TABLE gateway_routes ADD COLUMN IF NOT EXISTS "
            "pii_redaction_enabled BOOLEAN NOT NULL DEFAULT FALSE"
        )
    )

    # ── Per-end-user rate limit ────────────────────────────────────────────────
    op.execute(
        sa.text(
            "ALTER TABLE gateway_routes ADD COLUMN IF NOT EXISTS "
            "per_user_rpm_limit INTEGER NULL"
        )
    )

    # ── Route health monitoring ────────────────────────────────────────────────
    op.execute(
        sa.text(
            "ALTER TABLE gateway_routes ADD COLUMN IF NOT EXISTS "
            "health_auto_disable BOOLEAN NOT NULL DEFAULT TRUE"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE gateway_routes ADD COLUMN IF NOT EXISTS "
            "last_health_check_at TIMESTAMPTZ NULL"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE gateway_routes ADD COLUMN IF NOT EXISTS "
            "consecutive_health_failures INTEGER NOT NULL DEFAULT 0"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE gateway_routes ADD COLUMN IF NOT EXISTS "
            "disabled_reason TEXT NULL"
        )
    )


def downgrade() -> None:
    for col in [
        "disabled_reason",
        "consecutive_health_failures",
        "last_health_check_at",
        "health_auto_disable",
        "per_user_rpm_limit",
        "pii_redaction_enabled",
        "monthly_cost_limit_usd",
        "daily_cost_limit_usd",
    ]:
        op.execute(sa.text(f"ALTER TABLE gateway_routes DROP COLUMN IF EXISTS {col}"))
