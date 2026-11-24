"""Observe: one outcomes table, session index, saved views (review O-03, O-15, ENH).

- outcome_events (SDK/MCP ingest) is folded into outcomes, the table the Outcomes &
  ROI API reads. Existing rows are copied with their run's workspace, then the old
  table is dropped. Ingest now writes outcomes directly.
- agent_runs gets a (workspace_id, session_id) index for the Sessions views.
- saved_views stores per-user named filter sets for Runs, Explorer and Sessions.

Revision ID: observe_outcomes_views
Revises: workflows_spine
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision = "observe_outcomes_views"
down_revision = "workflows_spine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO outcomes (id, workspace_id, run_id, session_id, end_user_id,
                              outcome_type, success, labels, created_at)
        SELECT oe.id, ar.workspace_id, oe.run_id, ar.session_id, ar.end_user_id,
               oe.event_type, oe.success, COALESCE(oe.labels, '{}'::jsonb), oe.created_at
        FROM outcome_events oe
        JOIN agent_runs ar ON ar.id = oe.run_id
        ON CONFLICT (id) DO NOTHING
        """
    )
    op.drop_index("ix_outcome_events_run_id", table_name="outcome_events")
    op.drop_table("outcome_events")

    op.create_index("ix_agent_runs_session", "agent_runs", ["workspace_id", "session_id"])

    op.create_table(
        "saved_views",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("page", sa.String(32), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("query", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("workspace_id", "user_id", "page", "name", name="uq_saved_views_name"),
    )
    op.create_index("ix_saved_views_owner", "saved_views", ["workspace_id", "user_id", "page"])


def downgrade() -> None:
    op.drop_index("ix_saved_views_owner", table_name="saved_views")
    op.drop_table("saved_views")
    op.drop_index("ix_agent_runs_session", table_name="agent_runs")

    op.create_table(
        "outcome_events",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column(
            "run_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("agent_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("labels", JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index("ix_outcome_events_run_id", "outcome_events", ["run_id"])
    op.execute(
        """
        INSERT INTO outcome_events (id, run_id, event_type, success, labels, created_at)
        SELECT o.id, o.run_id, o.outcome_type, o.success, o.labels, o.created_at
        FROM outcomes o JOIN agent_runs ar ON ar.id = o.run_id
        """
    )
