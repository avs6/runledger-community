"""gateway enterprise routing and security foundations

Revision ID: 075_gateway_enterprise_security_foundations
Revises: 074_gateway_fallback_key_ownership_team_privacy
Create Date: 2026-08-06
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "075_gateway_enterprise_security_foundations"
down_revision = "074_gateway_fallback_key_ownership_team_privacy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "gateway_routes",
        sa.Column("required_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column(
        "gateway_routes",
        sa.Column("excluded_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column("gateway_routes", sa.Column("retry_count", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("gateway_routes", sa.Column("timeout_ms", sa.Integer(), nullable=True))
    op.add_column("gateway_routes", sa.Column("cooldown_seconds", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("gateway_routes", sa.Column("cooldown_until", sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column("gateway_routes", sa.Column("region", sa.String(length=64), nullable=True))
    op.add_column(
        "gateway_routes",
        sa.Column("mirror_config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    op.create_table(
        "gateway_passthrough_endpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("path_prefix", sa.Text(), nullable=False, server_default=sa.text("'/''")),
        sa.Column("upstream_base_url", sa.Text(), nullable=False),
        sa.Column("auth_type", sa.String(length=32), nullable=True),
        sa.Column("auth_config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("header_config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("default_query", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("timeout_ms", sa.Integer(), nullable=False, server_default="30000"),
        sa.Column("rate_limit_rpm", sa.Integer(), nullable=True),
        sa.Column("cost_per_call_usd", sa.Numeric(12, 6), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("workspace_id", "slug", name="uq_gateway_passthrough_workspace_slug"),
    )
    op.create_index("ix_gateway_passthrough_workspace", "gateway_passthrough_endpoints", ["workspace_id", "slug"])

    op.create_table(
        "workspace_security_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("required_metadata_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("required_metadata_mode", sa.String(length=16), nullable=False, server_default=sa.text("'warn'")),
        sa.Column("data_residency_regions", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("callback_config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("brand_config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("oidc_session_config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("workspace_id", name="uq_workspace_security_settings_workspace"),
    )

    op.create_table(
        "oidc_providers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("issuer_url", sa.Text(), nullable=False),
        sa.Column("audience", sa.Text(), nullable=True),
        sa.Column("discovery_url", sa.Text(), nullable=True),
        sa.Column("jwks_uri", sa.Text(), nullable=True),
        sa.Column("claim_mappings", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_oidc_providers_workspace_active", "oidc_providers", ["workspace_id", "is_active"])

    op.create_table(
        "ip_acl_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("api_key_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scope_type", sa.String(length=32), nullable=False, server_default=sa.text("'workspace'")),
        sa.Column("team_name", sa.String(length=255), nullable=True),
        sa.Column("cidr", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=8), nullable=False, server_default=sa.text("'allow'")),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["api_key_id"], ["api_keys.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_ip_acl_rules_workspace_scope", "ip_acl_rules", ["workspace_id", "scope_type", "priority"])

    op.create_table(
        "key_rotation_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("api_key_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rotated_from_prefix", sa.String(length=24), nullable=False),
        sa.Column("rotated_to_prefix", sa.String(length=24), nullable=False),
        sa.Column("triggered_by", sa.Text(), nullable=True),
        sa.Column("grace_expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["api_key_id"], ["api_keys.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_key_rotation_events_api_key", "key_rotation_events", ["api_key_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_key_rotation_events_api_key", table_name="key_rotation_events")
    op.drop_table("key_rotation_events")
    op.drop_index("ix_ip_acl_rules_workspace_scope", table_name="ip_acl_rules")
    op.drop_table("ip_acl_rules")
    op.drop_index("ix_oidc_providers_workspace_active", table_name="oidc_providers")
    op.drop_table("oidc_providers")
    op.drop_table("workspace_security_settings")
    op.drop_index("ix_gateway_passthrough_workspace", table_name="gateway_passthrough_endpoints")
    op.drop_table("gateway_passthrough_endpoints")
    op.drop_column("gateway_routes", "mirror_config")
    op.drop_column("gateway_routes", "region")
    op.drop_column("gateway_routes", "cooldown_until")
    op.drop_column("gateway_routes", "cooldown_seconds")
    op.drop_column("gateway_routes", "timeout_ms")
    op.drop_column("gateway_routes", "retry_count")
    op.drop_column("gateway_routes", "excluded_tags")
    op.drop_column("gateway_routes", "required_tags")
