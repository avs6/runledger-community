"""Add oauth2_providers and ldap_providers tables.

Revision ID: 089_oauth2_ldap
Revises: 088_external_auth_oidc
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision = "089_oauth2_ldap"
down_revision = "088_external_auth_oidc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- oauth2_providers ----------------------------------------------------
    op.create_table(
        "oauth2_providers",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("authorization_endpoint", sa.Text, nullable=False),
        sa.Column("token_endpoint", sa.Text, nullable=False),
        sa.Column("userinfo_endpoint", sa.Text, nullable=False),
        sa.Column("client_id", sa.Text, nullable=False),
        sa.Column("client_secret_encrypted", sa.Text, nullable=True),
        sa.Column(
            "scopes",
            sa.Text,
            nullable=False,
            server_default=sa.text("'openid email profile'"),
        ),
        sa.Column(
            "userinfo_id_field",
            sa.String(64),
            nullable=False,
            server_default=sa.text("'sub'"),
        ),
        sa.Column(
            "userinfo_email_field",
            sa.String(64),
            nullable=False,
            server_default=sa.text("'email'"),
        ),
        sa.Column(
            "userinfo_name_field",
            sa.String(64),
            nullable=False,
            server_default=sa.text("'name'"),
        ),
        sa.Column(
            "auto_provision",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "default_workspace_role",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'viewer'"),
        ),
        sa.Column(
            "default_tenant_role",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'org_member'"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
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
        "ix_oauth2_providers_workspace_active",
        "oauth2_providers",
        ["workspace_id", "is_active"],
    )
    op.create_index("ix_oauth2_providers_tenant", "oauth2_providers", ["tenant_id"])

    # -- ldap_providers ------------------------------------------------------
    op.create_table(
        "ldap_providers",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("server_url", sa.Text, nullable=False),
        sa.Column("bind_dn", sa.Text, nullable=True),
        sa.Column("bind_password_encrypted", sa.Text, nullable=True),
        sa.Column(
            "use_ssl",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "start_tls",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("user_search_base", sa.Text, nullable=False),
        sa.Column(
            "user_search_filter",
            sa.Text,
            nullable=False,
            server_default=sa.text("'(uid={username})'"),
        ),
        sa.Column(
            "email_attribute",
            sa.String(64),
            nullable=False,
            server_default=sa.text("'mail'"),
        ),
        sa.Column(
            "name_attribute",
            sa.String(64),
            nullable=False,
            server_default=sa.text("'cn'"),
        ),
        sa.Column(
            "uid_attribute",
            sa.String(64),
            nullable=False,
            server_default=sa.text("'uid'"),
        ),
        sa.Column("group_search_base", sa.Text, nullable=True),
        sa.Column("group_search_filter", sa.Text, nullable=True),
        sa.Column(
            "auto_provision",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "default_workspace_role",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'viewer'"),
        ),
        sa.Column(
            "default_tenant_role",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'org_member'"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
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
        "ix_ldap_providers_workspace_active",
        "ldap_providers",
        ["workspace_id", "is_active"],
    )
    op.create_index("ix_ldap_providers_tenant", "ldap_providers", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_ldap_providers_tenant", table_name="ldap_providers")
    op.drop_index("ix_ldap_providers_workspace_active", table_name="ldap_providers")
    op.drop_table("ldap_providers")

    op.drop_index("ix_oauth2_providers_tenant", table_name="oauth2_providers")
    op.drop_index("ix_oauth2_providers_workspace_active", table_name="oauth2_providers")
    op.drop_table("oauth2_providers")
