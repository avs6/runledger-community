"""080 - capture policy scopes and routing policies

Revision ID: 080
Revises: 079
Create Date: 2026-08-07 13:40:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "080"
down_revision = "079"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "capture_policy_scopes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope_type", sa.String(length=32), nullable=False),
        sa.Column("scope_id", sa.Text(), nullable=False),
        sa.Column(
            "privacy_mode",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'METADATA_ONLY'"),
        ),
        sa.Column("sampled_rate", sa.Numeric(5, 4), nullable=True),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "scope_type",
            "scope_id",
            name="uq_capture_policy_scopes_workspace_scope",
        ),
    )
    op.create_index(
        "ix_capture_policy_scopes_workspace",
        "capture_policy_scopes",
        ["workspace_id", "scope_type", "scope_id"],
        unique=False,
    )

    op.create_table(
        "routing_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alias", sa.Text(), nullable=False),
        sa.Column(
            "policy_type",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'manual'"),
        ),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "alias", name="uq_routing_policies_workspace_alias"),
    )
    op.create_index(
        "ix_routing_policies_workspace",
        "routing_policies",
        ["workspace_id", "alias"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_routing_policies_workspace", table_name="routing_policies")
    op.drop_table("routing_policies")
    op.drop_index("ix_capture_policy_scopes_workspace", table_name="capture_policy_scopes")
    op.drop_table("capture_policy_scopes")
