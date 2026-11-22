"""Ingestion hardening: dead-letter queue, unpriceable-call tracking for enrichment,
per-batch ingest-health columns for OTLP, per-workspace signed-ingest secret version.

Revision ID: 091_ingestion_hardening
Revises: 090_org_access_hardening
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision = "091_ingestion_hardening"
down_revision = "090_org_access_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ingest_dead_letters",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=True),
        sa.Column("run_id", sa.String(64), nullable=True),
        sa.Column("event", JSONB, nullable=False),
        sa.Column("error", sa.Text, nullable=False),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="1"),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "last_attempt_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_ingest_dead_letters_ws_status",
        "ingest_dead_letters",
        ["workspace_id", "status", "created_at"],
    )

    # Enrichment: remember unpriceable calls so they stop blocking newer ones.
    op.add_column(
        "provider_calls",
        sa.Column("cost_checked_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_provider_calls_unpriced",
        "provider_calls",
        ["created_at"],
        postgresql_where=sa.text("cost_usd IS NULL AND input_tokens IS NOT NULL"),
    )

    # OTLP ingest health.
    op.add_column(
        "otlp_ingest_batches",
        sa.Column("runs_created", sa.Integer, nullable=False, server_default="0"),
    )
    op.add_column(
        "otlp_ingest_batches",
        sa.Column("traces_dropped", sa.Integer, nullable=False, server_default="0"),
    )
    op.add_column("otlp_ingest_batches", sa.Column("resource_summary", JSONB, nullable=True))

    # Signed ingest: per-workspace secret version (rotation).
    op.add_column(
        "workspaces",
        sa.Column("ingest_signing_version", sa.Integer, nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_column("workspaces", "ingest_signing_version")
    op.drop_column("otlp_ingest_batches", "resource_summary")
    op.drop_column("otlp_ingest_batches", "traces_dropped")
    op.drop_column("otlp_ingest_batches", "runs_created")
    op.drop_index("ix_provider_calls_unpriced", table_name="provider_calls")
    op.drop_column("provider_calls", "cost_checked_at")
    op.drop_index("ix_ingest_dead_letters_ws_status", table_name="ingest_dead_letters")
    op.drop_table("ingest_dead_letters")
