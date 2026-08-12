"""076 - ops backup and kafka hardening

Revision ID: 076
Revises: 075
Create Date: 2026-08-06
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "076"
down_revision = "075"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "email_preferences",
        sa.Column(
            "report_template",
            sa.String(length=32),
            server_default=sa.text("'detailed'"),
            nullable=False,
        ),
    )
    op.add_column(
        "kafka_export_configs",
        sa.Column("dead_letter_topic", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "kafka_export_configs",
        sa.Column(
            "redaction_mode",
            sa.String(length=32),
            server_default=sa.text("'none'"),
            nullable=False,
        ),
    )
    op.add_column(
        "kafka_export_configs",
        sa.Column(
            "max_retries",
            sa.Integer(),
            server_default=sa.text("2"),
            nullable=False,
        ),
    )
    op.add_column(
        "kafka_export_configs",
        sa.Column(
            "retry_backoff_seconds",
            sa.Integer(),
            server_default=sa.text("5"),
            nullable=False,
        ),
    )
    op.add_column(
        "kafka_export_deliveries",
        sa.Column("next_retry_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "kafka_export_deliveries",
        sa.Column("last_error_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "kafka_export_deliveries",
        sa.Column("dead_letter_topic", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "kafka_export_deliveries",
        sa.Column("dead_lettered_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("kafka_export_deliveries", "dead_lettered_at")
    op.drop_column("kafka_export_deliveries", "dead_letter_topic")
    op.drop_column("kafka_export_deliveries", "last_error_at")
    op.drop_column("kafka_export_deliveries", "next_retry_at")
    op.drop_column("kafka_export_configs", "retry_backoff_seconds")
    op.drop_column("kafka_export_configs", "max_retries")
    op.drop_column("kafka_export_configs", "redaction_mode")
    op.drop_column("kafka_export_configs", "dead_letter_topic")
    op.drop_column("email_preferences", "report_template")
