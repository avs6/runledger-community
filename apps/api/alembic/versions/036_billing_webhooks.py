"""036 — Finance system integrations: billing webhook configs + delivery log

Revision ID: 036
Revises: 035
Create Date: 2026-03-24
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "036"
down_revision = "035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Webhook configurations ────────────────────────────────────────────────
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS billing_webhook_configs (
                id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                workspace_id    UUID NOT NULL,
                url             TEXT NOT NULL,
                secret          TEXT NOT NULL,
                label           VARCHAR(128) NOT NULL DEFAULT 'billing webhook',
                enabled         BOOLEAN NOT NULL DEFAULT TRUE,
                created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_billing_webhook_configs_workspace "
            "ON billing_webhook_configs (workspace_id)"
        )
    )

    # ── Webhook delivery log ──────────────────────────────────────────────────
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS billing_webhook_deliveries (
                id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                webhook_config_id   UUID NOT NULL REFERENCES billing_webhook_configs(id)
                                        ON DELETE CASCADE,
                billing_period_id   UUID NOT NULL,
                attempt             INTEGER NOT NULL DEFAULT 1,
                status              VARCHAR(16) NOT NULL DEFAULT 'pending',
                response_status     INTEGER,
                response_body       TEXT,
                delivered_at        TIMESTAMPTZ,
                created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_billing_webhook_deliveries_config "
            "ON billing_webhook_deliveries (webhook_config_id, created_at)"
        )
    )
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_billing_webhook_deliveries_period "
            "ON billing_webhook_deliveries (billing_period_id)"
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS billing_webhook_deliveries"))
    op.execute(sa.text("DROP TABLE IF EXISTS billing_webhook_configs"))
