"""Org & Access hardening: session owners, auth tokens, tenant audit scope,
unique access-group membership, access-group budgets moved to Budget rows.

Revision ID: 090_org_access_hardening
Revises: 089_oauth2_ldap
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision = "090_org_access_hardening"
down_revision = "089_oauth2_ldap"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── api_keys.user_id: owner of dashboard session keys ──────────────────────
    op.add_column(
        "api_keys",
        sa.Column(
            "user_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_api_keys_user_session",
        "api_keys",
        ["user_id"],
        postgresql_where=sa.text("is_session = true"),
    )
    # Backfill session-key owners from the creator email.
    op.execute(
        """
        UPDATE api_keys k
           SET user_id = u.id
          FROM users u
         WHERE k.is_session = true
           AND k.user_id IS NULL
           AND k.created_by = u.email
        """
    )
    # Session keys that can no longer be tied to a user are revoked.
    op.execute(
        """
        UPDATE api_keys
           SET revoked_at = NOW()
         WHERE is_session = true AND user_id IS NULL AND revoked_at IS NULL
        """
    )

    # ── users: verification / reset tokens, forced password change ─────────────
    op.add_column(
        "users",
        sa.Column("email_verify_expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column("users", sa.Column("password_reset_token_hash", sa.String(64), nullable=True))
    op.create_index("ix_users_password_reset_token_hash", "users", ["password_reset_token_hash"])
    op.add_column(
        "users",
        sa.Column("password_reset_expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    # Verification tokens are now stored hashed; old raw tokens are invalidated.
    op.execute("UPDATE users SET email_verify_token = NULL")

    # ── audit_events.tenant_id ─────────────────────────────────────────────────
    op.add_column("audit_events", sa.Column("tenant_id", PGUUID(as_uuid=True), nullable=True))
    op.create_index("ix_audit_events_tenant_id", "audit_events", ["tenant_id"])
    op.execute(
        """
        UPDATE audit_events a
           SET tenant_id = w.tenant_id
          FROM workspaces w
         WHERE a.workspace_id = w.id AND a.tenant_id IS NULL
        """
    )
    # Normalise double-prefixed action names written by the old log_audit helper.
    op.execute(
        "UPDATE audit_events SET action = substr(action, 8) WHERE action LIKE 'tenant.org.%'"
    )
    op.execute(
        "UPDATE audit_events SET action = substr(action, 11) "
        "WHERE action LIKE 'workspace.workspace.%'"
    )

    # ── access_group_members: unique (group_id, user_id) ───────────────────────
    op.execute(
        """
        DELETE FROM access_group_members m
         USING access_group_members d
         WHERE m.group_id = d.group_id
           AND m.user_id = d.user_id
           AND (m.created_at, m.id::text) > (d.created_at, d.id::text)
        """
    )
    op.create_unique_constraint(
        "uq_access_group_members_group_user", "access_group_members", ["group_id", "user_id"]
    )
    op.execute(
        """
        UPDATE access_groups g
           SET member_count = (
               SELECT COUNT(*) FROM access_group_members m WHERE m.group_id = g.id
           )
        """
    )

    # ── access_groups.budget_*: move into Budget rows, then drop ───────────────
    op.execute(
        """
        INSERT INTO budgets (id, workspace_id, scope_type, scope_id, period_type,
                             limit_usd, action, is_active, created_at)
        SELECT gen_random_uuid(), g.workspace_id, 'access_group', g.id::text,
               CASE WHEN g.budget_period IN ('daily', 'monthly', 'total')
                    THEN g.budget_period ELSE 'monthly' END,
               g.budget_usd, 'notify', g.is_active, NOW()
          FROM access_groups g
         WHERE g.budget_usd IS NOT NULL AND g.budget_usd > 0
           AND NOT EXISTS (
               SELECT 1 FROM budgets b
                WHERE b.workspace_id = g.workspace_id
                  AND b.scope_type = 'access_group'
                  AND b.scope_id = g.id::text
           )
        """
    )
    op.drop_column("access_groups", "budget_usd")
    op.drop_column("access_groups", "budget_period")


def downgrade() -> None:
    op.add_column("access_groups", sa.Column("budget_period", sa.String(20), nullable=True))
    op.add_column("access_groups", sa.Column("budget_usd", sa.Numeric(12, 2), nullable=True))
    op.drop_constraint("uq_access_group_members_group_user", "access_group_members", type_="unique")
    op.drop_index("ix_audit_events_tenant_id", table_name="audit_events")
    op.drop_column("audit_events", "tenant_id")
    op.drop_column("users", "must_change_password")
    op.drop_column("users", "password_reset_expires_at")
    op.drop_index("ix_users_password_reset_token_hash", table_name="users")
    op.drop_column("users", "password_reset_token_hash")
    op.drop_column("users", "email_verify_expires_at")
    op.drop_index("ix_api_keys_user_session", table_name="api_keys")
    op.drop_column("api_keys", "user_id")
