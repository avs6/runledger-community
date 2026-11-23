"""Workflow spine: workflow_id on runs; WorkflowRun becomes a view (review top#4, B-11/14/17/18).

- workflow_definitions gains feature_tag (unique per workspace among non-archived
  workflows), gateway_alias and owner. Existing workflows whose config carries a
  feature_tag are linked to it.
- agent_runs gains workflow_id (FK workflow_definitions, SET NULL) and agent_id
  (FK agents, SET NULL), resolved at ingest. Existing runs are back-filled from
  feature_tag.
- The record-only workflow_runs / workflow_steps tables (rows were written by hand
  through POST /workflows/{id}/runs and never executed or costed) are dropped;
  workflow_runs is recreated as a read-only view over agent_runs.

Revision ID: workflows_spine
Revises: 095_ip_acl_access_groups
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision = "workflows_spine"
down_revision = "095_ip_acl_access_groups"
branch_labels = None
depends_on = None

_VIEW = """
CREATE VIEW workflow_runs AS
SELECT
    r.id,
    r.workspace_id,
    r.workflow_id,
    r.agent_id,
    NULL::uuid AS parent_run_id,
    r.api_key_id,
    NULL::uuid AS access_group_id,
    r.status::text AS status,
    COALESCE(r.total_cost_usd, 0) AS total_cost,
    COALESCE(r.total_input_tokens, 0) + COALESCE(r.total_output_tokens, 0) AS total_tokens,
    (EXTRACT(EPOCH FROM (r.ended_at - r.started_at)) * 1000)::bigint AS total_duration_ms,
    r.source_type AS trigger,
    r.started_at,
    r.ended_at AS completed_at,
    r.started_at AS created_at
FROM agent_runs r
WHERE r.workflow_id IS NOT NULL
"""


def upgrade() -> None:
    op.add_column("workflow_definitions", sa.Column("feature_tag", sa.String(255), nullable=True))
    op.add_column("workflow_definitions", sa.Column("gateway_alias", sa.Text, nullable=True))
    op.add_column("workflow_definitions", sa.Column("owner", sa.Text, nullable=True))
    # Link workflows that already named their tag in config (first one wins per tag).
    op.execute(
        """
        UPDATE workflow_definitions w SET feature_tag = left(w.config->>'feature_tag', 255)
        WHERE w.config ? 'feature_tag' AND w.status <> 'archived'
          AND w.id = (
            SELECT w2.id FROM workflow_definitions w2
            WHERE w2.workspace_id = w.workspace_id
              AND w2.config->>'feature_tag' = w.config->>'feature_tag'
              AND w2.status <> 'archived'
            ORDER BY w2.created_at LIMIT 1
          )
        """
    )
    op.create_index(
        "uq_workflow_definitions_feature_tag",
        "workflow_definitions",
        ["workspace_id", "feature_tag"],
        unique=True,
        postgresql_where=sa.text("feature_tag IS NOT NULL AND status <> 'archived'"),
    )

    op.add_column(
        "agent_runs",
        sa.Column(
            "workflow_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("workflow_definitions.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "agent_runs",
        sa.Column(
            "agent_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_agent_runs_workflow", "agent_runs", ["workspace_id", "workflow_id", "started_at"]
    )
    op.create_index("ix_agent_runs_agent", "agent_runs", ["workspace_id", "agent_id", "started_at"])
    op.execute(
        """
        UPDATE agent_runs r SET workflow_id = w.id
        FROM workflow_definitions w
        WHERE w.workspace_id = r.workspace_id AND w.feature_tag = r.feature_tag
          AND w.status <> 'archived' AND r.workflow_id IS NULL
        """
    )

    op.drop_table("workflow_steps")
    op.drop_table("workflow_runs")
    op.execute(_VIEW)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS workflow_runs")
    op.create_table(
        "workflow_runs",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("workflow_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", PGUUID(as_uuid=True), nullable=True),
        sa.Column("parent_run_id", PGUUID(as_uuid=True), nullable=True),
        sa.Column(
            "api_key_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("api_keys.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "access_group_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("access_groups.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.Text, nullable=False, server_default=sa.text("'pending'")),
        sa.Column("total_cost", sa.Numeric(12, 6), server_default=sa.text("0")),
        sa.Column("total_tokens", sa.BigInteger, server_default=sa.text("0")),
        sa.Column("total_duration_ms", sa.BigInteger, nullable=True),
        sa.Column("trigger", sa.Text, nullable=True),
        sa.Column("input_data", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("output_data", JSONB, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index("ix_workflow_runs_workspace", "workflow_runs", ["workspace_id"])
    op.create_index("ix_workflow_runs_workflow", "workflow_runs", ["workflow_id"])
    op.create_table(
        "workflow_steps",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("step_index", sa.Integer, nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("step_type", sa.Text, nullable=False, server_default=sa.text("'agent'")),
        sa.Column("agent_id", PGUUID(as_uuid=True), nullable=True),
        sa.Column("model", sa.Text, nullable=True),
        sa.Column("tool", sa.Text, nullable=True),
        sa.Column("status", sa.Text, nullable=False, server_default=sa.text("'pending'")),
        sa.Column("cost", sa.Numeric(12, 6), server_default=sa.text("0")),
        sa.Column("tokens", sa.BigInteger, server_default=sa.text("0")),
        sa.Column("duration_ms", sa.BigInteger, nullable=True),
        sa.Column("input_data", JSONB, nullable=True),
        sa.Column("output_data", JSONB, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index("ix_workflow_steps_run", "workflow_steps", ["run_id"])
    op.create_index("ix_workflow_steps_run_index", "workflow_steps", ["run_id", "step_index"])

    op.drop_index("ix_agent_runs_agent", table_name="agent_runs")
    op.drop_index("ix_agent_runs_workflow", table_name="agent_runs")
    op.drop_column("agent_runs", "agent_id")
    op.drop_column("agent_runs", "workflow_id")
    op.drop_index("uq_workflow_definitions_feature_tag", table_name="workflow_definitions")
    op.drop_column("workflow_definitions", "owner")
    op.drop_column("workflow_definitions", "gateway_alias")
    op.drop_column("workflow_definitions", "feature_tag")
