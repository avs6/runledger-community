"""routing_policies table + decision_reason on gateway_requests

Revision ID: 015
Revises: 014
Create Date: 2026-03-20
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add decision_reason to gateway_requests
    op.add_column(
        "gateway_requests",
        sa.Column("decision_reason", sa.Text, nullable=True),
    )

    # Routing policies — one policy per (workspace, alias)
    op.create_table(
        "routing_policies",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("alias", sa.Text, nullable=False),
        sa.Column("policy_type", sa.String(32), nullable=False, server_default="manual"),
        sa.Column("config", sa.dialects.postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
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
    )
    op.create_unique_constraint(
        "uq_routing_policies_workspace_alias",
        "routing_policies",
        ["workspace_id", "alias"],
    )
    op.create_index(
        "ix_routing_policies_workspace",
        "routing_policies",
        ["workspace_id", "alias"],
    )


def downgrade() -> None:
    op.drop_table("routing_policies")
    op.drop_column("gateway_requests", "decision_reason")
