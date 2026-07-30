"""054 - add kafka export tables

Revision ID: 054
Revises: 053
Create Date: 2026-07-30
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "054"
down_revision = "053"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "kafka_export_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("bootstrap_servers", sa.Text(), nullable=False),
        sa.Column("topic_prefix", sa.String(length=255), nullable=False),
        sa.Column("security_protocol", sa.String(length=32), nullable=False),
        sa.Column("sasl_mechanism", sa.String(length=32), nullable=True),
        sa.Column("sasl_username", sa.Text(), nullable=True),
        sa.Column("sasl_password_secret", sa.Text(), nullable=True),
        sa.Column("ssl_ca_cert", sa.Text(), nullable=True),
        sa.Column(
            "event_types",
            postgresql.ARRAY(sa.String()),
            server_default=sa.text("'{}'::varchar[]"),
            nullable=False,
        ),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_kafka_export_configs_workspace",
        "kafka_export_configs",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        "ix_kafka_export_configs_enabled",
        "kafka_export_configs",
        ["workspace_id", "enabled"],
        unique=False,
    )

    op.create_table(
        "kafka_export_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("config_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("topic", sa.String(length=512), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("attempt", sa.Integer(), server_default="1", nullable=False),
        sa.Column("delivered_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["config_id"], ["kafka_export_configs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_kafka_export_deliveries_config_created",
        "kafka_export_deliveries",
        ["config_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_kafka_export_deliveries_workspace_created",
        "kafka_export_deliveries",
        ["workspace_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_kafka_export_deliveries_workspace_created", table_name="kafka_export_deliveries")
    op.drop_index("ix_kafka_export_deliveries_config_created", table_name="kafka_export_deliveries")
    op.drop_table("kafka_export_deliveries")
    op.drop_index("ix_kafka_export_configs_enabled", table_name="kafka_export_configs")
    op.drop_index("ix_kafka_export_configs_workspace", table_name="kafka_export_configs")
    op.drop_table("kafka_export_configs")
