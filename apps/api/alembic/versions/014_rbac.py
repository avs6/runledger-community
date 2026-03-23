"""Multi-tenancy RBAC: tenant_users, workspace roles, user fields

Revision ID: 014
Revises: 013
Create Date: 2026-03-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Extend users table
    op.add_column("users", sa.Column("full_name", sa.String(255), nullable=True))
    op.add_column(
        "users",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column(
        "users",
        sa.Column("last_login_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "is_platform_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )

    # 2. Extend tenants table
    op.add_column(
        "tenants",
        sa.Column("owner_user_id", PGUUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "tenants",
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_foreign_key(
        "fk_tenants_owner_user",
        "tenants",
        "users",
        ["owner_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    # Partial unique index: only one default tenant allowed
    op.execute(
        "CREATE UNIQUE INDEX uq_tenants_is_default ON tenants (is_default) WHERE is_default = true"
    )

    # 3. Create tenant_role enum (idempotent) + tenant_users table
    #    Use raw SQL throughout to bypass SQLAlchemy's before_create DDL event
    #    which would fire CREATE TYPE even after we created it explicitly.
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE tenant_role_enum AS ENUM ('org_admin', 'org_member');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)
    op.execute("""
        CREATE TABLE tenant_users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            role tenant_role_enum NOT NULL DEFAULT 'org_member',
            invited_by UUID,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_tenant_users UNIQUE (tenant_id, user_id)
        )
    """)
    op.execute("CREATE INDEX ix_tenant_users_tenant ON tenant_users (tenant_id)")
    op.execute("CREATE INDEX ix_tenant_users_user ON tenant_users (user_id)")

    # 4. Create workspace_role enum (idempotent), migrate workspace_users.role varchar → enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE workspace_role_enum AS ENUM ('workspace_admin', 'member', 'viewer');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)
    op.execute("ALTER TABLE workspace_users ADD COLUMN role_new workspace_role_enum")
    op.execute("""
        UPDATE workspace_users SET role_new = CASE
            WHEN role = 'workspace_admin' THEN 'workspace_admin'::workspace_role_enum
            WHEN role = 'member' THEN 'member'::workspace_role_enum
            WHEN role = 'viewer' THEN 'viewer'::workspace_role_enum
            ELSE 'workspace_admin'::workspace_role_enum
        END
    """)
    op.execute("ALTER TABLE workspace_users ALTER COLUMN role_new SET NOT NULL")
    op.execute("ALTER TABLE workspace_users DROP COLUMN role")
    op.execute("ALTER TABLE workspace_users RENAME COLUMN role_new TO role")

    # 5. Add invited_by to workspace_users
    op.execute("ALTER TABLE workspace_users ADD COLUMN invited_by UUID")


def downgrade() -> None:
    op.execute("ALTER TABLE workspace_users DROP COLUMN IF EXISTS invited_by")
    op.execute("ALTER TABLE workspace_users ADD COLUMN role_tmp VARCHAR(32)")
    op.execute("UPDATE workspace_users SET role_tmp = role::text")
    op.execute("ALTER TABLE workspace_users DROP COLUMN role")
    op.execute("ALTER TABLE workspace_users RENAME COLUMN role_tmp TO role")
    op.execute("ALTER TABLE workspace_users ALTER COLUMN role SET NOT NULL")
    op.execute("ALTER TABLE workspace_users ALTER COLUMN role SET DEFAULT 'admin'")
    op.execute("DROP TYPE IF EXISTS workspace_role_enum")
    op.execute("DROP TABLE IF EXISTS tenant_users")
    op.execute("DROP TYPE IF EXISTS tenant_role_enum")
    op.execute("DROP INDEX IF EXISTS uq_tenants_is_default")
    op.drop_constraint("fk_tenants_owner_user", "tenants", type_="foreignkey")
    op.drop_column("tenants", "is_default")
    op.drop_column("tenants", "owner_user_id")
    op.drop_column("users", "is_platform_admin")
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "is_active")
    op.drop_column("users", "full_name")
