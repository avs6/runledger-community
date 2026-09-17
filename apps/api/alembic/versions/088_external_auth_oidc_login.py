"""Add external_identities table and OIDC login columns on oidc_providers.

Revision ID: 088_external_auth_oidc
Revises: 087_chargeback_status
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision = "088_external_auth_oidc"
down_revision = "087_chargeback_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- Extend oidc_providers with authorization-code-flow columns ----------
    op.add_column(
        "oidc_providers",
        sa.Column("tenant_id", PGUUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_oidc_providers_tenant",
        "oidc_providers",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_oidc_providers_tenant", "oidc_providers", ["tenant_id"])

    op.add_column(
        "oidc_providers",
        sa.Column("client_id", sa.Text, nullable=True),
    )
    op.add_column(
        "oidc_providers",
        sa.Column("client_secret_encrypted", sa.Text, nullable=True),
    )
    op.add_column(
        "oidc_providers",
        sa.Column(
            "scopes",
            sa.Text,
            nullable=False,
            server_default=sa.text("'openid email profile'"),
        ),
    )
    op.add_column(
        "oidc_providers",
        sa.Column(
            "auto_provision",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "oidc_providers",
        sa.Column(
            "default_workspace_role",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'viewer'"),
        ),
    )
    op.add_column(
        "oidc_providers",
        sa.Column(
            "default_tenant_role",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'org_member'"),
        ),
    )

    # -- external_identities table -------------------------------------------
    op.create_table(
        "external_identities",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider_type", sa.String(16), nullable=False),
        sa.Column("provider_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("external_subject", sa.String(512), nullable=False),
        sa.Column("external_email", sa.String(320), nullable=True),
        sa.Column(
            "external_metadata",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("last_login_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "provider_type",
            "provider_id",
            "external_subject",
            name="uq_external_identity_provider_subject",
        ),
    )
    op.create_index(
        "ix_external_identities_user", "external_identities", ["user_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_external_identities_user", table_name="external_identities")
    op.drop_table("external_identities")

    op.drop_column("oidc_providers", "default_tenant_role")
    op.drop_column("oidc_providers", "default_workspace_role")
    op.drop_column("oidc_providers", "auto_provision")
    op.drop_column("oidc_providers", "scopes")
    op.drop_column("oidc_providers", "client_secret_encrypted")
    op.drop_column("oidc_providers", "client_id")
    op.drop_index("ix_oidc_providers_tenant", table_name="oidc_providers")
    op.drop_constraint("fk_oidc_providers_tenant", "oidc_providers", type_="foreignkey")
    op.drop_column("oidc_providers", "tenant_id")
