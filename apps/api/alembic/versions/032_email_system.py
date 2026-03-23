"""032 — Email notification system: email_preferences, email_log, user columns

Revision ID: 032
Revises: 031
Create Date: 2026-03-23
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "032"
down_revision = "031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Add columns to existing tables ────────────────────────────────────────
    op.execute(
        sa.text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_notifications_enabled BOOLEAN NOT NULL DEFAULT TRUE"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_unsubscribe_token VARCHAR(64) UNIQUE"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE budget_notifications ADD COLUMN IF NOT EXISTS email_enabled BOOLEAN NOT NULL DEFAULT FALSE"
        )
    )

    # ── email_preferences ─────────────────────────────────────────────────────
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS email_preferences (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE UNIQUE,
                report_frequency VARCHAR(16) NOT NULL DEFAULT 'weekly',
                alerts_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                approvals_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                reconciliation_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                budget_alerts_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                billing_closed_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                score_regression_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                dispute_flagged_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )

    # ── email_log ─────────────────────────────────────────────────────────────
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS email_log (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                workspace_id UUID REFERENCES workspaces(id) ON DELETE SET NULL,
                to_email VARCHAR NOT NULL,
                subject VARCHAR NOT NULL,
                event_type VARCHAR(64) NOT NULL,
                status VARCHAR(16) NOT NULL DEFAULT 'sent',
                error_message TEXT,
                sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_email_log_workspace ON email_log(workspace_id, sent_at DESC)"
        )
    )
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_email_log_event ON email_log(event_type, sent_at DESC)"
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS email_log"))
    op.execute(sa.text("DROP TABLE IF EXISTS email_preferences"))
    op.execute(
        sa.text("ALTER TABLE budget_notifications DROP COLUMN IF EXISTS email_enabled")
    )
    op.execute(
        sa.text("ALTER TABLE users DROP COLUMN IF EXISTS email_unsubscribe_token")
    )
    op.execute(
        sa.text("ALTER TABLE users DROP COLUMN IF EXISTS email_notifications_enabled")
    )
