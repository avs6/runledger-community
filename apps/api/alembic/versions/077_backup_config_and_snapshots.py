"""077 - backup config and snapshots

Revision ID: 077_backup_config_and_snapshots
Revises: 076_ops_backup_and_kafka_hardening
Create Date: 2026-08-06 12:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "077_backup_config_and_snapshots"
down_revision = "076_ops_backup_and_kafka_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "backup_target_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=32), server_default=sa.text("'s3'"), nullable=False),
        sa.Column("bucket", sa.String(length=255), nullable=False),
        sa.Column("prefix", sa.String(length=255), nullable=True),
        sa.Column("region", sa.String(length=64), nullable=True),
        sa.Column("endpoint_url", sa.String(length=512), nullable=True),
        sa.Column("access_key_id", sa.String(length=255), nullable=True),
        sa.Column("secret_access_key", sa.String(length=255), nullable=True),
        sa.Column("force_path_style", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("schedule_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("cadence", sa.String(length=32), server_default=sa.text("'daily'"), nullable=False),
        sa.Column("run_hour_utc", sa.Integer(), server_default=sa.text("2"), nullable=False),
        sa.Column("retention_days", sa.Integer(), server_default=sa.text("30"), nullable=False),
        sa.Column("include_memory_db", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("include_qdrant", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("include_kuzu", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("include_skills", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("encryption_mode", sa.String(length=32), server_default=sa.text("'server_side'"), nullable=False),
        sa.Column("last_verified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", name="uq_backup_target_configs_workspace"),
    )
    op.create_table(
        "backup_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("backup_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_type", sa.String(length=32), server_default=sa.text("'full'"), nullable=False),
        sa.Column("bucket", sa.String(length=255), nullable=False),
        sa.Column("prefix", sa.String(length=255), nullable=True),
        sa.Column("manifest_key", sa.String(length=512), nullable=True),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("total_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("artifact_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("artifacts", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("integrity_status", sa.String(length=32), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("verified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["backup_run_id"], ["backup_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_backup_snapshots_workspace_created", "backup_snapshots", ["workspace_id", "created_at"])
    op.create_index("ix_backup_snapshots_run", "backup_snapshots", ["backup_run_id"])


def downgrade() -> None:
    op.drop_index("ix_backup_snapshots_run", table_name="backup_snapshots")
    op.drop_index("ix_backup_snapshots_workspace_created", table_name="backup_snapshots")
    op.drop_table("backup_snapshots")
    op.drop_table("backup_target_configs")
