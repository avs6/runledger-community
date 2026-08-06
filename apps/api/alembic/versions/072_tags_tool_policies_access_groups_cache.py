"""Add tags, auto-tagging rules, search tools, tool policies, access groups, cache configs.

Revision ID: 072
Revises: 071
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "072"
down_revision = "071"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Tags ────────────────────────────────────────────────────────────────
    op.create_table(
        "tags",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("value", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("parent_tag_id", UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_tags_workspace_category", "tags", ["workspace_id", "category"])
    op.create_index("ix_tags_workspace_key", "tags", ["workspace_id", "key"])

    # ── Auto-Tagging Rules ──────────────────────────────────────────────────
    op.create_table(
        "auto_tagging_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("match_type", sa.String(50), nullable=False),
        sa.Column("match_field", sa.String(100), nullable=False),
        sa.Column("match_pattern", sa.String(500), nullable=False),
        sa.Column("tag_key", sa.String(100), nullable=False),
        sa.Column("tag_value", sa.String(255), nullable=False),
        sa.Column("priority", sa.Integer, server_default="100"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Search Tools ────────────────────────────────────────────────────────
    op.create_table(
        "search_tools",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("tool_type", sa.String(50), nullable=False),
        sa.Column("endpoint_url", sa.Text, nullable=True),
        sa.Column("auth_type", sa.String(50), nullable=True),
        sa.Column("auth_config", JSONB, nullable=True),
        sa.Column("rate_limit_rpm", sa.Integer, nullable=True),
        sa.Column("cost_per_query", sa.Numeric(12, 6), server_default="0"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("total_queries", sa.Integer, server_default="0"),
        sa.Column("total_cost_usd", sa.Numeric(12, 6), server_default="0"),
        sa.Column("avg_quality_score", sa.Numeric(5, 3), nullable=True),
        sa.Column("config", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Tool Policies ───────────────────────────────────────────────────────
    op.create_table(
        "tool_policies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("tool_name", sa.String(200), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("condition_type", sa.String(50), nullable=True),
        sa.Column("condition_config", JSONB, nullable=True),
        sa.Column("scope_type", sa.String(50), server_default="'workspace'"),
        sa.Column("scope_id", UUID(as_uuid=True), nullable=True),
        sa.Column("priority", sa.Integer, server_default="100"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_tool_policies_workspace_tool", "tool_policies", ["workspace_id", "tool_name"])

    # ── Access Groups ───────────────────────────────────────────────────────
    op.create_table(
        "access_groups",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("permissions", JSONB, nullable=True),
        sa.Column("budget_usd", sa.Numeric(12, 2), nullable=True),
        sa.Column("budget_period", sa.String(20), nullable=True),
        sa.Column("guardrail_profile", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("member_count", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "access_group_members",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("group_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(50), server_default="'member'"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_access_group_members_group_user", "access_group_members", ["group_id", "user_id"], unique=True)

    # ── Response Cache Configs ──────────────────────────────────────────────
    op.create_table(
        "response_cache_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("is_enabled", sa.Boolean, server_default="true"),
        sa.Column("ttl_seconds", sa.Integer, server_default="3600"),
        sa.Column("max_entries", sa.Integer, server_default="10000"),
        sa.Column("eviction_policy", sa.String(20), server_default="'lru'"),
        sa.Column("similarity_threshold", sa.Numeric(5, 4), server_default="0.95"),
        sa.Column("embedding_model", sa.String(100), nullable=True),
        sa.Column("scope_models", JSONB, nullable=True),
        sa.Column("total_hits", sa.Integer, server_default="0"),
        sa.Column("total_misses", sa.Integer, server_default="0"),
        sa.Column("total_savings_usd", sa.Numeric(12, 6), server_default="0"),
        sa.Column("config", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("response_cache_configs")
    op.drop_table("access_group_members")
    op.drop_table("access_groups")
    op.drop_table("tool_policies")
    op.drop_table("search_tools")
    op.drop_table("auto_tagging_rules")
    op.drop_table("tags")
