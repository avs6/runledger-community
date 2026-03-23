"""030 — Warehouse Export Destinations and Jobs

Revision ID: 030
Revises: 029
Create Date: 2026-03-23
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "030"
down_revision = "029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "warehouse_destinations",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.UUID(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),  # 's3', 'gcs', 'r2'
        sa.Column("bucket", sa.String(255), nullable=False),
        sa.Column("prefix", sa.String(500), server_default="", nullable=False),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column("endpoint_url", sa.Text, nullable=True),
        sa.Column("access_key_id", sa.Text, nullable=False),
        sa.Column("secret_access_key", sa.Text, nullable=False),
        sa.Column("format", sa.String(20), server_default="jsonl", nullable=False),
        sa.Column("resources", JSONB, nullable=False),  # ['runs','spans','provider_calls']
        sa.Column("is_active", sa.Boolean, server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("last_export_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_warehouse_destinations_workspace",
        "warehouse_destinations",
        ["workspace_id"],
    )

    op.create_table(
        "warehouse_export_jobs",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.UUID(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "destination_id",
            sa.UUID(),
            sa.ForeignKey("warehouse_destinations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("export_date", sa.Date, nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("resources", JSONB, nullable=False),
        sa.Column("file_keys", JSONB, nullable=True),  # resource -> s3 URI
        sa.Column("row_counts", JSONB, nullable=True),  # resource -> int
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_warehouse_export_jobs_workspace",
        "warehouse_export_jobs",
        ["workspace_id", "created_at"],
    )
    op.create_index(
        "ix_warehouse_export_jobs_destination",
        "warehouse_export_jobs",
        ["destination_id", "export_date"],
    )


def downgrade() -> None:
    op.drop_table("warehouse_export_jobs")
    op.drop_table("warehouse_destinations")
