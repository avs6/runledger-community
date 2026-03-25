"""042 — Kafka export configs and delivery log

Revision ID: 042
Revises: 041
Create Date: 2026-03-24
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "042"
down_revision = "041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Kafka export configurations ───────────────────────────────────────────
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS kafka_export_configs (
                id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                workspace_id            UUID NOT NULL,
                label                   VARCHAR(128) NOT NULL DEFAULT 'kafka export',
                bootstrap_servers       TEXT NOT NULL,
                topic_prefix            VARCHAR(64) NOT NULL DEFAULT 'runledger',
                security_protocol       VARCHAR(32) NOT NULL DEFAULT 'PLAINTEXT',
                sasl_mechanism          VARCHAR(32),
                sasl_username           VARCHAR(256),
                sasl_password_encrypted TEXT,
                ssl_ca_cert             TEXT,
                event_types             JSONB NOT NULL DEFAULT
                    '["run.completed","run.failed","alert.fired","budget.breached","score.submitted"]',
                enabled                 BOOLEAN NOT NULL DEFAULT TRUE,
                created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_kafka_export_configs_workspace "
            "ON kafka_export_configs (workspace_id)"
        )
    )

    # ── Kafka export delivery log ─────────────────────────────────────────────
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS kafka_export_deliveries (
                id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                config_id       UUID NOT NULL REFERENCES kafka_export_configs(id)
                                    ON DELETE CASCADE,
                event_type      VARCHAR(64) NOT NULL,
                topic           VARCHAR(256) NOT NULL,
                status          VARCHAR(16) NOT NULL DEFAULT 'pending',
                error_detail    VARCHAR(512),
                attempt         INTEGER NOT NULL DEFAULT 1,
                delivered_at    TIMESTAMPTZ,
                created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_kafka_export_deliveries_config "
            "ON kafka_export_deliveries (config_id, created_at)"
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS kafka_export_deliveries"))
    op.execute(sa.text("DROP TABLE IF EXISTS kafka_export_configs"))
