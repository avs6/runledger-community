"""Add gateway_routes, gateway_requests, and prompt_cache tables.

Revision ID: 013
Revises: 012
Create Date: 2026-03-06
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "013"
down_revision: str | None = "012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "gateway_routes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("alias", sa.Text, nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("target_model", sa.Text, nullable=False),
        sa.Column("base_url", sa.Text, nullable=True),
        sa.Column("api_key_env_var", sa.Text, nullable=True),
        sa.Column("priority", sa.Integer, nullable=False, server_default="10"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_gateway_routes_workspace",
        "gateway_routes",
        ["workspace_id", "alias", "priority"],
    )

    op.create_table(
        "gateway_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("route_id", UUID(as_uuid=True), nullable=True),
        sa.Column("model_requested", sa.Text, nullable=False),
        sa.Column("model_used", sa.Text, nullable=True),
        sa.Column("cache_hit", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("input_tokens", sa.Integer, nullable=True),
        sa.Column("output_tokens", sa.Integer, nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="success"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["route_id"],
            ["gateway_routes.id"],
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_gateway_requests_workspace", "gateway_requests", ["workspace_id", "created_at"]
    )
    op.create_index("ix_gateway_requests_route", "gateway_requests", ["route_id", "created_at"])

    op.create_table(
        "prompt_cache",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("cache_key", sa.String(64), nullable=False),
        sa.Column("model", sa.Text, nullable=False),
        sa.Column("response_json", JSONB, nullable=False),
        sa.Column("prompt_tokens", sa.Integer, nullable=True),
        sa.Column("completion_tokens", sa.Integer, nullable=True),
        sa.Column("hit_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.UniqueConstraint("workspace_id", "cache_key", name="uq_prompt_cache_key"),
    )
    op.create_index("ix_prompt_cache_expires", "prompt_cache", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_prompt_cache_expires", "prompt_cache")
    op.drop_table("prompt_cache")
    op.drop_index("ix_gateway_requests_route", "gateway_requests")
    op.drop_index("ix_gateway_requests_workspace", "gateway_requests")
    op.drop_table("gateway_requests")
    op.drop_index("ix_gateway_routes_workspace", "gateway_routes")
    op.drop_table("gateway_routes")
