"""Add agent_memories table for per-agent key-value memory store.

Revision ID: 068
Revises: 067
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "068"
down_revision = "067"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_memories",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.Text, nullable=False),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column(
            "memory_type",
            sa.Text,
            nullable=False,
            server_default=sa.text("'long_term'"),
        ),
        sa.Column("metadata", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("size_bytes", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("access_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("has_pii", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("retention_days", sa.Integer, nullable=True),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "last_accessed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
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
    op.create_index(
        "ix_agent_memories_agent", "agent_memories", ["agent_id"]
    )
    op.create_index(
        "ix_agent_memories_workspace", "agent_memories", ["workspace_id"]
    )
    op.create_index(
        "ix_agent_memories_agent_key",
        "agent_memories",
        ["agent_id", "key"],
        unique=True,
    )
    op.create_index(
        "ix_agent_memories_type",
        "agent_memories",
        ["agent_id", "memory_type"],
    )
    op.create_index(
        "ix_agent_memories_expires",
        "agent_memories",
        ["expires_at"],
        postgresql_where=sa.text("expires_at IS NOT NULL"),
    )

    # Audit log for memory governance
    op.create_table(
        "agent_memory_audit",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", UUID(as_uuid=True), nullable=False),
        sa.Column("memory_id", UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.Text, nullable=False),
        sa.Column("key", sa.Text, nullable=True),
        sa.Column("details", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("actor", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_agent_memory_audit_agent",
        "agent_memory_audit",
        ["agent_id"],
    )
    op.create_index(
        "ix_agent_memory_audit_workspace",
        "agent_memory_audit",
        ["workspace_id"],
    )


def downgrade() -> None:
    op.drop_table("agent_memory_audit")
    op.drop_table("agent_memories")
