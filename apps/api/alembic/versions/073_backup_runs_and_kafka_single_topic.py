"""073 - backup runs and kafka single-topic mode

Revision ID: 073
Revises: 072
Create Date: 2026-08-06
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "073"
down_revision = "072"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "backup_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "trigger_mode", sa.String(length=32), server_default=sa.text("'manual'"), nullable=False
        ),
        sa.Column(
            "status", sa.String(length=32), server_default=sa.text("'queued'"), nullable=False
        ),
        sa.Column(
            "backup_scope", sa.String(length=64), server_default=sa.text("'full'"), nullable=False
        ),
        sa.Column("target", sa.String(length=512), nullable=True),
        sa.Column("command", sa.Text(), nullable=True),
        sa.Column("triggered_by", sa.String(length=255), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("output_excerpt", sa.Text(), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_backup_runs_workspace_created", "backup_runs", ["workspace_id", "created_at"]
    )
    op.create_index("ix_backup_runs_workspace_status", "backup_runs", ["workspace_id", "status"])

    op.add_column(
        "kafka_export_configs",
        sa.Column(
            "single_topic_mode", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
    )
    op.add_column(
        "kafka_export_configs",
        sa.Column("single_topic_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "kafka_export_deliveries",
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("kafka_export_deliveries", "idempotency_key")
    op.drop_column("kafka_export_configs", "single_topic_name")
    op.drop_column("kafka_export_configs", "single_topic_mode")
    op.drop_index("ix_backup_runs_workspace_status", table_name="backup_runs")
    op.drop_index("ix_backup_runs_workspace_created", table_name="backup_runs")
    op.drop_table("backup_runs")
