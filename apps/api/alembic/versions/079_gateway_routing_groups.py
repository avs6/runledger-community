"""079 - gateway routing groups

Revision ID: 079_gateway_routing_groups
Revises: 078_otlp_metrics_and_logs
Create Date: 2026-08-07 12:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "079_gateway_routing_groups"
down_revision = "078_otlp_metrics_and_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gateway_routing_groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alias", sa.Text(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("match_tags", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'"), nullable=False),
        sa.Column("default_tags", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'"), nullable=False),
        sa.Column("strategy_type", sa.String(length=32), server_default="manual", nullable=False),
        sa.Column("strategy_config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_gateway_routing_groups_workspace",
        "gateway_routing_groups",
        ["workspace_id", "alias", "name"],
        unique=False,
    )
    op.add_column(
        "gateway_routes",
        sa.Column("routing_group_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_gateway_routes_routing_group_id",
        "gateway_routes",
        "gateway_routing_groups",
        ["routing_group_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_gateway_routes_routing_group_id", "gateway_routes", type_="foreignkey")
    op.drop_column("gateway_routes", "routing_group_id")
    op.drop_index("ix_gateway_routing_groups_workspace", table_name="gateway_routing_groups")
    op.drop_table("gateway_routing_groups")
