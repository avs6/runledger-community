"""Governance (W1-H): one tool-control system, governed MCP calls, no decorative settings.

- tool_registry.policy/runtime_enforcement → managed ToolPolicy rows named
  ``registry:<tool>`` (priority 50). ``block`` without runtime enforcement was
  advisory, so it becomes ``audit``. Then the two columns are dropped (S-07).
- mcp_permissions → ToolPolicy ``allow`` rows scoped to the permission's api_key or
  access_group with condition ``mcp_server``; the table is dropped (S-23). Grants were
  never enforced, so no deny rows are created (no behaviour change on upgrade).
- mcp_tool_calls gains decision, policy_name, approval_id, end_user_id (cd:S-04).
- tool_policies: ``deny`` → ``block``, ``group`` → ``access_group``.
- workspace_security_settings drops data_residency_regions, callback_config,
  brand_config, oidc_session_config: stored, never read (S-24).
- capture_policy_scopes: scope types ingest can't resolve are removed (S-09).

Revision ID: governance_tool_policy
Revises: 095_ip_acl_access_groups
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision = "governance_tool_policy"
down_revision = "095_ip_acl_access_groups"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO tool_policies (id, workspace_id, name, description, tool_name, action,
                                   condition_type, scope_type, priority, is_active)
        SELECT gen_random_uuid(), workspace_id, left('registry:' || tool_name, 200),
               'Managed by the tool registry', left(tool_name, 200),
               CASE WHEN policy = 'block' AND NOT runtime_enforcement THEN 'audit'
                    WHEN policy IN ('allow', 'audit', 'block', 'require_approval') THEN policy
                    ELSE 'audit' END,
               'all', 'workspace', 50, true
        FROM tool_registry
        """
    )
    op.drop_column("tool_registry", "policy")
    op.drop_column("tool_registry", "runtime_enforcement")

    op.execute(
        """
        INSERT INTO tool_policies (id, workspace_id, name, description, tool_name, action,
                                   condition_type, condition_config, scope_type, scope_id,
                                   priority, is_active)
        SELECT gen_random_uuid(), p.workspace_id,
               left('mcp-permission:' || coalesce(s.name, p.mcp_server_id::text), 200),
               'Migrated from MCP permissions', left(coalesce(t.tool, '*'), 200), 'allow',
               'mcp_server', jsonb_build_object('server_id', p.mcp_server_id::text),
               CASE WHEN p.scope_type IN ('group', 'access_group') THEN 'access_group'
                    WHEN p.scope_type = 'api_key' THEN 'api_key' ELSE 'workspace' END,
               CASE WHEN p.scope_type IN ('group', 'access_group', 'api_key') THEN p.scope_id END,
               90, true
        FROM mcp_permissions p
        LEFT JOIN mcp_servers s ON s.id = p.mcp_server_id
        LEFT JOIN LATERAL jsonb_array_elements_text(
            CASE WHEN jsonb_typeof(p.allowed_tools) = 'array' THEN p.allowed_tools
                 ELSE '[]'::jsonb END
        ) AS t(tool) ON true
        """
    )
    op.drop_table("mcp_permissions")

    op.add_column("mcp_tool_calls", sa.Column("decision", sa.String(32), nullable=True))
    op.add_column("mcp_tool_calls", sa.Column("policy_name", sa.Text(), nullable=True))
    op.add_column("mcp_tool_calls", sa.Column("approval_id", PGUUID(as_uuid=True), nullable=True))
    op.add_column("mcp_tool_calls", sa.Column("end_user_id", sa.Text(), nullable=True))
    op.create_index(
        "ix_mcp_calls_workspace_created", "mcp_tool_calls", ["workspace_id", "created_at"]
    )

    op.execute("UPDATE tool_policies SET action = 'block' WHERE action = 'deny'")
    op.execute("UPDATE tool_policies SET scope_type = 'access_group' WHERE scope_type = 'group'")
    op.execute("UPDATE tool_policies SET condition_type = 'all' WHERE condition_type IS NULL")

    for col in ("data_residency_regions", "callback_config", "brand_config", "oidc_session_config"):
        op.drop_column("workspace_security_settings", col)

    op.execute(
        "DELETE FROM capture_policy_scopes "
        "WHERE scope_type NOT IN ('api_key', 'user', 'feature_tag', 'intent', 'workspace')"
    )


def downgrade() -> None:
    for col, default in (
        ("data_residency_regions", "'[]'"),
        ("callback_config", "'{}'"),
        ("brand_config", "'{}'"),
        ("oidc_session_config", "'{}'"),
    ):
        op.add_column(
            "workspace_security_settings",
            sa.Column(col, JSONB(), nullable=False, server_default=sa.text(default)),
        )

    op.drop_index("ix_mcp_calls_workspace_created", table_name="mcp_tool_calls")
    for col in ("end_user_id", "approval_id", "policy_name", "decision"):
        op.drop_column("mcp_tool_calls", col)

    op.create_table(
        "mcp_permissions",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("mcp_server_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("scope_type", sa.String(16), nullable=False),
        sa.Column("scope_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("allowed_tools", JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index("ix_mcp_perms_workspace", "mcp_permissions", ["workspace_id"])
    op.create_index("ix_mcp_perms_server", "mcp_permissions", ["mcp_server_id"])
    op.execute("DELETE FROM tool_policies WHERE name LIKE 'mcp-permission:%'")

    op.add_column(
        "tool_registry",
        sa.Column("policy", sa.Text(), nullable=False, server_default=sa.text("'audit'")),
    )
    op.add_column(
        "tool_registry",
        sa.Column(
            "runtime_enforcement", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")
        ),
    )
    op.execute(
        """
        UPDATE tool_registry r
        SET policy = CASE WHEN p.action = 'require_approval' THEN 'block' ELSE p.action END,
            runtime_enforcement = p.action IN ('block', 'require_approval')
        FROM tool_policies p
        WHERE p.workspace_id = r.workspace_id
          AND p.name = left('registry:' || r.tool_name, 200)
          AND p.is_active
        """
    )
    op.execute("DELETE FROM tool_policies WHERE name LIKE 'registry:%'")
