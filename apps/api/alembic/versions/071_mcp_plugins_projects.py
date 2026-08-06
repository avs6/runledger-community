"""Add MCP server registry, plugins, AI Hub, projects, team models tables.

Revision ID: 071
Revises: 070
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "071"
down_revision = "070"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── MCP Server Registry ──────────────────────────────────────────────────
    op.create_table(
        "mcp_servers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("transport", sa.String(16), nullable=False, server_default=sa.text("'http'")),
        sa.Column("url", sa.Text, nullable=True),
        sa.Column("command", sa.Text, nullable=True),
        sa.Column("args", JSONB, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("env", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("auth_type", sa.String(32), nullable=True),
        sa.Column("auth_config", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("discovered_tools", JSONB, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("discovered_resources", JSONB, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("discovered_prompts", JSONB, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("health_status", sa.String(16), nullable=False, server_default=sa.text("'unknown'")),
        sa.Column("last_health_check", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_mcp_servers_workspace", "mcp_servers", ["workspace_id"])

    op.create_table(
        "mcp_permissions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("mcp_server_id", UUID(as_uuid=True), nullable=False),
        sa.Column("scope_type", sa.String(16), nullable=False),
        sa.Column("scope_id", UUID(as_uuid=True), nullable=False),
        sa.Column("allowed_tools", JSONB, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_mcp_perms_workspace", "mcp_permissions", ["workspace_id"])
    op.create_index("ix_mcp_perms_server", "mcp_permissions", ["mcp_server_id"])

    op.create_table(
        "mcp_tool_calls",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("mcp_server_id", UUID(as_uuid=True), nullable=False),
        sa.Column("api_key_id", UUID(as_uuid=True), nullable=True),
        sa.Column("tool_name", sa.Text, nullable=False),
        sa.Column("arguments", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("result", JSONB, nullable=True),
        sa.Column("cost_usd", sa.Numeric(12, 6), nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'success'")),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_mcp_calls_workspace", "mcp_tool_calls", ["workspace_id"])
    op.create_index("ix_mcp_calls_server", "mcp_tool_calls", ["mcp_server_id"])

    # ── Custom Plugins ───────────────────────────────────────────────────────
    op.create_table(
        "plugins",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("plugin_type", sa.String(32), nullable=False),
        sa.Column("hooks", JSONB, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("config", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("priority", sa.Integer, nullable=False, server_default=sa.text("100")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("version", sa.String(32), nullable=True),
        sa.Column("author", sa.String(128), nullable=True),
        sa.Column("install_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_plugins_workspace", "plugins", ["workspace_id"])

    op.create_table(
        "plugin_executions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("plugin_id", UUID(as_uuid=True), nullable=False),
        sa.Column("hook", sa.String(32), nullable=False),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'success'")),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_plugin_exec_workspace", "plugin_executions", ["workspace_id"])
    op.create_index("ix_plugin_exec_plugin", "plugin_executions", ["plugin_id"])

    # ── AI Hub (Model Catalog) ───────────────────────────────────────────────
    op.create_table(
        "hub_models",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("capabilities", JSONB, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("context_window", sa.Integer, nullable=True),
        sa.Column("input_cost_per_1k", sa.Numeric(12, 6), nullable=True),
        sa.Column("output_cost_per_1k", sa.Numeric(12, 6), nullable=True),
        sa.Column("tags", JSONB, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("is_featured", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("is_deprecated", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("deprecation_notice", sa.Text, nullable=True),
        sa.Column("is_public", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("access_request_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_hub_models_workspace", "hub_models", ["workspace_id"])

    # ── Projects ─────────────────────────────────────────────────────────────
    op.create_table(
        "projects",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("owner", sa.String(128), nullable=True),
        sa.Column("budget_usd", sa.Numeric(14, 6), nullable=True),
        sa.Column("budget_period", sa.String(16), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("config", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_projects_workspace", "projects", ["workspace_id"])

    op.create_table(
        "project_keys",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), nullable=False),
        sa.Column("api_key_id", UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_project_keys_project", "project_keys", ["project_id"])
    op.create_index("ix_project_keys_key", "project_keys", ["api_key_id"])

    # ── Team Models ──────────────────────────────────────────────────────────
    op.create_table(
        "team_models",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("team_name", sa.String(128), nullable=False),
        sa.Column("model_name", sa.String(128), nullable=False),
        sa.Column("provider", sa.String(64), nullable=True),
        sa.Column("api_base_url", sa.Text, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("budget_usd", sa.Numeric(14, 6), nullable=True),
        sa.Column("budget_period", sa.String(16), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("health_status", sa.String(16), nullable=False, server_default=sa.text("'unknown'")),
        sa.Column("last_health_check", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("total_calls", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("total_cost_usd", sa.Numeric(14, 6), nullable=False, server_default=sa.text("0")),
        sa.Column("config", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_team_models_workspace", "team_models", ["workspace_id"])


def downgrade() -> None:
    op.drop_table("team_models")
    op.drop_table("project_keys")
    op.drop_table("projects")
    op.drop_table("hub_models")
    op.drop_table("plugin_executions")
    op.drop_table("plugins")
    op.drop_table("mcp_tool_calls")
    op.drop_table("mcp_permissions")
    op.drop_table("mcp_servers")
