"""078 - OTLP metrics and logs staging

Revision ID: 078
Revises: 077
Create Date: 2026-08-07 09:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "078"
down_revision = "077"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "otlp_ingest_batches",
        sa.Column("signal_type", sa.Text(), server_default=sa.text("'trace'"), nullable=False),
    )
    op.add_column(
        "otlp_ingest_batches",
        sa.Column("metric_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.add_column(
        "otlp_ingest_batches",
        sa.Column("log_record_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("otlp_ingest_batches", "log_record_count")
    op.drop_column("otlp_ingest_batches", "metric_count")
    op.drop_column("otlp_ingest_batches", "signal_type")
