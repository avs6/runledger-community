"""Add API playground tables.

Revision ID: 070
Revises: 069
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "070"
down_revision = "069"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "playground_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text, nullable=True),
        sa.Column("system_prompt", sa.Text, nullable=True),
        sa.Column("mode", sa.Text, nullable=False, server_default=sa.text("'single'")),
        sa.Column("is_favorite", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("config", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_by", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index("ix_playground_sessions_workspace", "playground_sessions", ["workspace_id"])

    op.create_table(
        "playground_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", UUID(as_uuid=True), nullable=True),
        sa.Column("model", sa.Text, nullable=False),
        sa.Column("provider", sa.Text, nullable=True),
        sa.Column("system_prompt", sa.Text, nullable=True),
        sa.Column("user_prompt", sa.Text, nullable=False),
        sa.Column("parameters", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("response_text", sa.Text, nullable=True),
        sa.Column("input_tokens", sa.Integer, nullable=True),
        sa.Column("output_tokens", sa.Integer, nullable=True),
        sa.Column("cost_usd", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("status", sa.Text, nullable=False, server_default=sa.text("'pending'")),
        sa.Column("route_decision", sa.Text, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("gateway_request_id", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index("ix_playground_requests_workspace", "playground_requests", ["workspace_id"])
    op.create_index("ix_playground_requests_session", "playground_requests", ["session_id"])


def downgrade() -> None:
    op.drop_table("playground_requests")
    op.drop_table("playground_sessions")
