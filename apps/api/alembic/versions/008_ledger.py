"""Add ledger_keys, ledger_snapshots, tool_registry, security_events, capture_policies.

Revision ID: 008
Revises: 007
Create Date: 2026-02-28
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision: str = "008"
down_revision: str | None = "007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ledger_keys
    op.create_table(
        "ledger_keys",
        sa.Column(
            "id",
            PGUUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "workspace_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("key_value", sa.Text, nullable=False),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.text("TRUE")),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_ledger_keys_workspace",
        "ledger_keys",
        ["workspace_id", "active", "expires_at"],
    )

    # ledger_snapshots
    op.create_table(
        "ledger_snapshots",
        sa.Column(
            "id",
            PGUUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "workspace_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("snapshot_date", sa.Date, nullable=False),
        sa.Column("total_cost_usd", sa.Numeric(14, 8), nullable=False),
        sa.Column("model_breakdown", JSONB, nullable=False, server_default="{}"),
        sa.Column("call_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("hash", sa.Text, nullable=False),
        sa.Column(
            "key_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("ledger_keys.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_ledger_snapshots_workspace_date",
        "ledger_snapshots",
        ["workspace_id", "snapshot_date"],
        unique=True,
    )

    # tool_registry
    op.create_table(
        "tool_registry",
        sa.Column(
            "id",
            PGUUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "workspace_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tool_name", sa.Text, nullable=False),
        sa.Column("policy", sa.Text, nullable=False, server_default="audit"),
        sa.Column("description", sa.Text, nullable=True),
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
        "ix_tool_registry_workspace_name",
        "tool_registry",
        ["workspace_id", "tool_name"],
        unique=True,
    )

    # security_events
    op.create_table(
        "security_events",
        sa.Column(
            "id",
            PGUUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "workspace_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.Text, nullable=False),
        sa.Column("tool_name", sa.Text, nullable=True),
        sa.Column("end_user_id", sa.Text, nullable=True),
        sa.Column("run_id", PGUUID(as_uuid=True), nullable=True),
        sa.Column("details", JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "detected_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_security_events_workspace_detected",
        "security_events",
        ["workspace_id", "detected_at"],
    )

    # capture_policies
    op.create_table(
        "capture_policies",
        sa.Column(
            "id",
            PGUUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "workspace_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("privacy_mode", sa.Text, nullable=False, server_default="METADATA_ONLY"),
        sa.Column("sampled_rate", sa.Numeric(5, 4), nullable=True),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("capture_policies")
    op.drop_index("ix_security_events_workspace_detected", "security_events")
    op.drop_table("security_events")
    op.drop_index("ix_tool_registry_workspace_name", "tool_registry")
    op.drop_table("tool_registry")
    op.drop_index("ix_ledger_snapshots_workspace_date", "ledger_snapshots")
    op.drop_table("ledger_snapshots")
    op.drop_index("ix_ledger_keys_workspace", "ledger_keys")
    op.drop_table("ledger_keys")
