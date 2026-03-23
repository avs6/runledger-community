"""Add OTLP raw-ingestion staging tables (otlp_ingest_batches + otlp_spans_raw).

Revision ID: 027
Revises: 026
Create Date: 2026-03-22
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "otlp_ingest_batches",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "received_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("content_type", sa.Text, nullable=True),
        sa.Column("encoding", sa.Text, nullable=True),
        sa.Column("trace_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("span_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("status", sa.Text, nullable=False, server_default="pending"),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("raw_payload", sa.LargeBinary, nullable=True),
    )
    op.create_index(
        "ix_otlp_batches_workspace",
        "otlp_ingest_batches",
        ["workspace_id", "received_at"],
    )

    op.create_table(
        "otlp_spans_raw",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "batch_id",
            UUID(as_uuid=True),
            sa.ForeignKey("otlp_ingest_batches.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("external_trace_id", sa.Text, nullable=False),
        sa.Column("external_span_id", sa.Text, nullable=False),
        sa.Column("external_parent_span_id", sa.Text, nullable=True),
        sa.Column("span_name", sa.Text, nullable=False),
        sa.Column("start_time", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("end_time", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("status_code", sa.Text, nullable=True),
        sa.Column("resource_attributes", JSONB, nullable=True),
        sa.Column("scope_attributes", JSONB, nullable=True),
        sa.Column("span_attributes", JSONB, nullable=True),
        sa.Column("events", JSONB, nullable=True),
        sa.Column("links", JSONB, nullable=True),
        sa.Column("normalized", sa.Boolean, nullable=False, server_default="false"),
    )
    op.create_index("ix_otlp_spans_raw_batch", "otlp_spans_raw", ["batch_id"])
    op.create_index(
        "ix_otlp_spans_raw_trace",
        "otlp_spans_raw",
        ["workspace_id", "external_trace_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_otlp_spans_raw_trace", table_name="otlp_spans_raw")
    op.drop_index("ix_otlp_spans_raw_batch", table_name="otlp_spans_raw")
    op.drop_table("otlp_spans_raw")

    op.drop_index("ix_otlp_batches_workspace", table_name="otlp_ingest_batches")
    op.drop_table("otlp_ingest_batches")
