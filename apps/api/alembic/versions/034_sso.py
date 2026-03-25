"""034 — SSO / OIDC + SCIM: sso_configs, sso_identities, scim_tokens tables

Revision ID: 034
Revises: 033
Create Date: 2026-03-23
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "034"
down_revision = "033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── sso_configs ───────────────────────────────────────────────────────────
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS sso_configs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                provider VARCHAR(32) NOT NULL,
                issuer_url VARCHAR(512) NOT NULL,
                client_id VARCHAR(256) NOT NULL,
                client_secret_enc TEXT NOT NULL,
                scopes VARCHAR(512) NOT NULL DEFAULT 'openid email profile',
                default_role VARCHAR(32) NOT NULL DEFAULT 'member',
                enabled BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE(tenant_id, provider)
            )
            """
        )
    )
    op.execute(
        sa.text("CREATE INDEX IF NOT EXISTS ix_sso_configs_tenant ON sso_configs(tenant_id)")
    )

    # ── sso_identities ────────────────────────────────────────────────────────
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS sso_identities (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                sso_config_id UUID NOT NULL REFERENCES sso_configs(id) ON DELETE CASCADE,
                external_sub VARCHAR(512) NOT NULL,
                external_email VARCHAR(256) NOT NULL,
                last_login_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE(sso_config_id, external_sub)
            )
            """
        )
    )
    op.execute(
        sa.text("CREATE INDEX IF NOT EXISTS ix_sso_identities_user ON sso_identities(user_id)")
    )

    # ── scim_tokens ───────────────────────────────────────────────────────────
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS scim_tokens (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                token_hash VARCHAR(64) NOT NULL UNIQUE,
                token_prefix VARCHAR(16) NOT NULL,
                label VARCHAR(128) NOT NULL DEFAULT 'SCIM provisioning',
                enabled BOOLEAN NOT NULL DEFAULT TRUE,
                last_used_at TIMESTAMPTZ,
                expires_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )
    op.execute(
        sa.text("CREATE INDEX IF NOT EXISTS ix_scim_tokens_tenant ON scim_tokens(tenant_id)")
    )


def downgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS scim_tokens"))
    op.execute(sa.text("DROP TABLE IF EXISTS sso_identities"))
    op.execute(sa.text("DROP TABLE IF EXISTS sso_configs"))
