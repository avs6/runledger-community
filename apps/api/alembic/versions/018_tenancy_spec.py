"""Tenancy spec: status fields, extended roles, audit_events table.

Revision ID: 018
Revises: 017
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Extend enums ───────────────────────────────────────────────────────────
    # ALTER TYPE ... ADD VALUE requires no active transaction in PG.
    # Use op.execute which Alembic runs inside its transaction for DDL-safe dialects,
    # but for PG enum additions we must commit first via a raw connection.
    conn = op.get_bind()
    # Commit any open transaction before ALTER TYPE (PG requirement)
    conn.execute(sa.text("COMMIT"))
    conn.execute(sa.text("ALTER TYPE tenant_role_enum ADD VALUE IF NOT EXISTS 'org_manager'"))
    conn.execute(sa.text("ALTER TYPE tenant_role_enum ADD VALUE IF NOT EXISTS 'org_billing_admin'"))
    conn.execute(sa.text("ALTER TYPE tenant_role_enum ADD VALUE IF NOT EXISTS 'org_auditor'"))
    conn.execute(sa.text("ALTER TYPE workspace_role_enum ADD VALUE IF NOT EXISTS 'workspace_editor'"))
    conn.execute(sa.text("ALTER TYPE workspace_role_enum ADD VALUE IF NOT EXISTS 'workspace_contributor'"))
    conn.execute(sa.text("BEGIN"))

    # ── tenants: status ────────────────────────────────────────────────────────
    op.add_column("tenants", sa.Column("status", sa.String(16), nullable=False, server_default="active"))

    # ── workspaces: status + is_restricted ─────────────────────────────────────
    op.add_column("workspaces", sa.Column("status", sa.String(16), nullable=False, server_default="active"))
    op.add_column("workspaces", sa.Column("is_restricted", sa.Boolean(), nullable=False, server_default=sa.text("false")))

    # ── tenant_users: status ───────────────────────────────────────────────────
    op.add_column("tenant_users", sa.Column("status", sa.String(16), nullable=False, server_default="active"))

    # ── workspace_users: status ────────────────────────────────────────────────
    op.add_column("workspace_users", sa.Column("status", sa.String(16), nullable=False, server_default="active"))

    # ── audit_events table ─────────────────────────────────────────────────────
    op.create_table(
        "audit_events",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("actor_user_id", PGUUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("target_user_id", PGUUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("scope_type", sa.String(32), nullable=False),
        sa.Column("scope_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_audit_events_scope", "audit_events", ["scope_type", "scope_id"])
    op.create_index("ix_audit_events_actor", "audit_events", ["actor_user_id"])
    op.create_index("ix_audit_events_created", "audit_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_created", table_name="audit_events")
    op.drop_index("ix_audit_events_actor", table_name="audit_events")
    op.drop_index("ix_audit_events_scope", table_name="audit_events")
    op.drop_table("audit_events")

    op.drop_column("workspace_users", "status")
    op.drop_column("tenant_users", "status")
    op.drop_column("workspaces", "is_restricted")
    op.drop_column("workspaces", "status")
    op.drop_column("tenants", "status")
    # Note: cannot remove values from PG enum types without a full recreate
