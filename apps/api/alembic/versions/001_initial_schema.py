"""Initial schema: tenants, workspaces, applications, api_keys, agent_runs, spans, provider_calls, tool_calls, outcome_events

Revision ID: 001
Revises:
Create Date: 2026-02-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── tenants ───────────────────────────────────────────────────────────────
    # Note: PostgreSQL enum types are created automatically by SQLAlchemy's DDL
    # events when the first table using each type is created (op.create_table).
    op.create_table(
        "tenants",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "plan",
            sa.Enum("free", "starter", "growth", "enterprise", name="plan_enum"),
            nullable=False,
            server_default="free",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )

    # ── workspaces ────────────────────────────────────────────────────────────
    op.create_table(
        "workspaces",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )

    # ── applications ──────────────────────────────────────────────────────────
    op.create_table(
        "applications",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "environment",
            sa.Enum("dev", "staging", "prod", name="environment_enum"),
            nullable=False,
            server_default="dev",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )

    # ── api_keys ──────────────────────────────────────────────────────────────
    op.create_table(
        "api_keys",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("key_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("key_prefix", sa.String(24), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column(
            "scopes",
            ARRAY(sa.String),
            nullable=False,
            server_default=sa.text("'{}'::varchar[]"),
        ),
        sa.Column("last_used_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )

    # ── agent_runs ────────────────────────────────────────────────────────────
    op.create_table(
        "agent_runs",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "application_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("applications.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("end_user_id", sa.String(255), nullable=True),
        sa.Column("session_id", sa.String(255), nullable=True),
        sa.Column("feature_tag", sa.String(255), nullable=True),
        sa.Column("deployment_version", sa.String(255), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "running",
                "succeeded",
                "failed",
                "cancelled",
                name="run_status_enum",
            ),
            nullable=False,
            server_default="running",
        ),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("ended_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("total_cost_usd", sa.Numeric(14, 8), nullable=True),
        sa.Column("total_input_tokens", sa.BigInteger, nullable=True),
        sa.Column("total_output_tokens", sa.BigInteger, nullable=True),
        sa.Column("metadata", JSONB, nullable=True),
    )
    op.create_index("ix_agent_runs_workspace_started", "agent_runs", ["workspace_id", "started_at"])
    op.create_index("ix_agent_runs_end_user", "agent_runs", ["workspace_id", "end_user_id"])
    op.create_index("ix_agent_runs_feature_tag", "agent_runs", ["workspace_id", "feature_tag"])

    # ── spans ─────────────────────────────────────────────────────────────────
    op.create_table(
        "spans",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column(
            "run_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("agent_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("parent_span_id", PGUUID(as_uuid=True), nullable=True),
        sa.Column(
            "span_type",
            sa.Enum(
                "chain",
                "llm",
                "tool",
                "agent",
                "retrieval",
                name="span_type_enum",
            ),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("ended_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "running",
                "succeeded",
                "failed",
                name="span_status_enum",
            ),
            nullable=False,
            server_default="running",
        ),
        sa.Column("cost_usd", sa.Numeric(14, 8), nullable=True),
        sa.Column("metadata", JSONB, nullable=True),
    )
    op.create_index("ix_spans_run_id", "spans", ["run_id"])
    op.create_index("ix_spans_parent", "spans", ["parent_span_id"])

    # ── provider_calls ────────────────────────────────────────────────────────
    op.create_table(
        "provider_calls",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("span_id", PGUUID(as_uuid=True), nullable=True),
        sa.Column(
            "run_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("agent_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("workspace_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("end_user_id", sa.String(255), nullable=True),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("input_tokens", sa.Integer, nullable=True),
        sa.Column("output_tokens", sa.Integer, nullable=True),
        sa.Column("cached_input_tokens", sa.Integer, nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("cost_usd", sa.Numeric(14, 8), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("error_type", sa.String(128), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index("ix_provider_calls_run_id", "provider_calls", ["run_id"])
    op.create_index(
        "ix_provider_calls_workspace_created", "provider_calls", ["workspace_id", "created_at"]
    )
    op.create_index("ix_provider_calls_end_user", "provider_calls", ["workspace_id", "end_user_id"])

    # ── tool_calls ────────────────────────────────────────────────────────────
    op.create_table(
        "tool_calls",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("span_id", PGUUID(as_uuid=True), nullable=True),
        sa.Column(
            "run_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("agent_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("workspace_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("tool_name", sa.String(255), nullable=False),
        sa.Column(
            "tool_type",
            sa.Enum("read", "write", "privileged", name="tool_type_enum"),
            nullable=False,
            server_default="read",
        ),
        sa.Column("risk_score", sa.SmallInteger, nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index("ix_tool_calls_run_id", "tool_calls", ["run_id"])

    # ── outcome_events ────────────────────────────────────────────────────────
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
        sa.Column("success", sa.Boolean, nullable=False),
        sa.Column("labels", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index("ix_outcome_events_run_id", "outcome_events", ["run_id"])


def downgrade() -> None:
    op.drop_table("outcome_events")
    op.drop_table("tool_calls")
    op.drop_table("provider_calls")
    op.drop_table("spans")
    op.drop_table("agent_runs")
    op.drop_table("api_keys")
    op.drop_table("applications")
    op.drop_table("workspaces")
    op.drop_table("tenants")

    op.execute("DROP TYPE tool_type_enum")
    op.execute("DROP TYPE span_status_enum")
    op.execute("DROP TYPE span_type_enum")
    op.execute("DROP TYPE run_status_enum")
    op.execute("DROP TYPE environment_enum")
    op.execute("DROP TYPE plan_enum")
