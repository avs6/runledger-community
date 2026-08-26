"""Add agent registry and workflow run tracking tables.

Revision ID: 067
Revises: 066
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "067"
down_revision = "066"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Agent Registry ────────────────────────────────────────────────────
    op.create_table(
        "agents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "agent_type",
            sa.Text,
            nullable=False,
            server_default=sa.text("'autonomous'"),
        ),
        sa.Column("owner", sa.Text, nullable=True),
        sa.Column("default_model", sa.Text, nullable=True),
        sa.Column("default_tools", JSONB, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("budget_envelope", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("policy_profile", sa.Text, nullable=True),
        sa.Column(
            "status",
            sa.Text,
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column("config", JSONB, nullable=False, server_default=sa.text("'{}'")),
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
    op.create_index("ix_agents_workspace", "agents", ["workspace_id"])
    op.create_index("ix_agents_workspace_status", "agents", ["workspace_id", "status"])

    # ── Workflow Definitions ──────────────────────────────────────────────
    op.create_table(
        "workflow_definitions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("steps_schema", JSONB, nullable=False, server_default=sa.text("'[]'")),
        sa.Column(
            "status",
            sa.Text,
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column("config", JSONB, nullable=False, server_default=sa.text("'{}'")),
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
    op.create_index("ix_workflow_definitions_workspace", "workflow_definitions", ["workspace_id"])

    # ── Workflow Runs ─────────────────────────────────────────────────────
    op.create_table(
        "workflow_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_id", UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", UUID(as_uuid=True), nullable=True),
        sa.Column("parent_run_id", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            sa.Text,
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("total_cost", sa.Numeric(precision=12, scale=6), server_default=sa.text("0")),
        sa.Column("total_tokens", sa.BigInteger, server_default=sa.text("0")),
        sa.Column("total_duration_ms", sa.BigInteger, nullable=True),
        sa.Column("trigger", sa.Text, nullable=True),
        sa.Column("input_data", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("output_data", JSONB, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column(
            "started_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "completed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index("ix_workflow_runs_workspace", "workflow_runs", ["workspace_id"])
    op.create_index("ix_workflow_runs_workflow", "workflow_runs", ["workflow_id"])
    op.create_index(
        "ix_workflow_runs_agent",
        "workflow_runs",
        ["agent_id"],
        postgresql_where=sa.text("agent_id IS NOT NULL"),
    )
    op.create_index(
        "ix_workflow_runs_parent",
        "workflow_runs",
        ["parent_run_id"],
        postgresql_where=sa.text("parent_run_id IS NOT NULL"),
    )

    # ── Workflow Steps ────────────────────────────────────────────────────
    op.create_table(
        "workflow_steps",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", UUID(as_uuid=True), nullable=False),
        sa.Column("step_index", sa.Integer, nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column(
            "step_type",
            sa.Text,
            nullable=False,
            server_default=sa.text("'agent'"),
        ),
        sa.Column("agent_id", UUID(as_uuid=True), nullable=True),
        sa.Column("model", sa.Text, nullable=True),
        sa.Column("tool", sa.Text, nullable=True),
        sa.Column(
            "status",
            sa.Text,
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("cost", sa.Numeric(precision=12, scale=6), server_default=sa.text("0")),
        sa.Column("tokens", sa.BigInteger, server_default=sa.text("0")),
        sa.Column("duration_ms", sa.BigInteger, nullable=True),
        sa.Column("input_data", JSONB, nullable=True),
        sa.Column("output_data", JSONB, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column(
            "started_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "completed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index("ix_workflow_steps_run", "workflow_steps", ["run_id"])
    op.create_index("ix_workflow_steps_run_index", "workflow_steps", ["run_id", "step_index"])


def downgrade() -> None:
    op.drop_table("workflow_steps")
    op.drop_table("workflow_runs")
    op.drop_table("workflow_definitions")
    op.drop_table("agents")
