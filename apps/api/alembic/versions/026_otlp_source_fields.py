"""Add OTLP source-provenance fields to existing event tables.

Revision ID: 026
Revises: 025
Create Date: 2026-03-22
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── agent_runs ────────────────────────────────────────────────────────────
    op.add_column("agent_runs", sa.Column("source_type", sa.Text, nullable=True))
    op.add_column("agent_runs", sa.Column("external_trace_id", sa.Text, nullable=True))
    op.add_column("agent_runs", sa.Column("external_trace_state", sa.Text, nullable=True))
    op.add_column("agent_runs", sa.Column("resource_attributes", JSONB, nullable=True))
    op.create_index(
        "uix_agent_runs_workspace_ext_trace",
        "agent_runs",
        ["workspace_id", "external_trace_id"],
        unique=True,
        postgresql_where=sa.text("external_trace_id IS NOT NULL"),
    )

    # ── spans ─────────────────────────────────────────────────────────────────
    op.add_column("spans", sa.Column("external_span_id", sa.Text, nullable=True))
    op.add_column("spans", sa.Column("external_parent_span_id", sa.Text, nullable=True))
    op.add_column("spans", sa.Column("trace_flags", sa.Text, nullable=True))
    op.add_column("spans", sa.Column("instrumentation_scope_name", sa.Text, nullable=True))
    op.add_column("spans", sa.Column("instrumentation_scope_version", sa.Text, nullable=True))
    op.add_column("spans", sa.Column("source_span_kind", sa.Text, nullable=True))
    op.add_column("spans", sa.Column("source_attributes", JSONB, nullable=True))
    op.create_index(
        "uix_spans_run_ext_span",
        "spans",
        ["run_id", "external_span_id"],
        unique=True,
        postgresql_where=sa.text("external_span_id IS NOT NULL"),
    )

    # ── provider_calls ────────────────────────────────────────────────────────
    op.add_column("provider_calls", sa.Column("provider_request_id", sa.Text, nullable=True))
    op.add_column(
        "provider_calls", sa.Column("reported_cost_usd", sa.Numeric(14, 8), nullable=True)
    )
    op.add_column("provider_calls", sa.Column("cost_source", sa.Text, nullable=True))
    op.add_column("provider_calls", sa.Column("model_provider", sa.Text, nullable=True))
    op.add_column("provider_calls", sa.Column("input_tokens_details", JSONB, nullable=True))
    op.add_column("provider_calls", sa.Column("output_tokens_details", JSONB, nullable=True))
    op.create_index(
        "ix_provider_calls_provider_request",
        "provider_calls",
        ["workspace_id", "provider", "provider_request_id"],
        postgresql_where=sa.text("provider_request_id IS NOT NULL"),
    )

    # ── tool_calls ────────────────────────────────────────────────────────────
    op.add_column("tool_calls", sa.Column("external_span_id", sa.Text, nullable=True))
    op.add_column("tool_calls", sa.Column("tool_arguments", JSONB, nullable=True))
    op.add_column("tool_calls", sa.Column("tool_result_summary", JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("tool_calls", "tool_result_summary")
    op.drop_column("tool_calls", "tool_arguments")
    op.drop_column("tool_calls", "external_span_id")

    op.drop_index("ix_provider_calls_provider_request", table_name="provider_calls")
    op.drop_column("provider_calls", "output_tokens_details")
    op.drop_column("provider_calls", "input_tokens_details")
    op.drop_column("provider_calls", "model_provider")
    op.drop_column("provider_calls", "cost_source")
    op.drop_column("provider_calls", "reported_cost_usd")
    op.drop_column("provider_calls", "provider_request_id")

    op.drop_index("uix_spans_run_ext_span", table_name="spans")
    op.drop_column("spans", "source_attributes")
    op.drop_column("spans", "source_span_kind")
    op.drop_column("spans", "instrumentation_scope_version")
    op.drop_column("spans", "instrumentation_scope_name")
    op.drop_column("spans", "trace_flags")
    op.drop_column("spans", "external_parent_span_id")
    op.drop_column("spans", "external_span_id")

    op.drop_index("uix_agent_runs_workspace_ext_trace", table_name="agent_runs")
    op.drop_column("agent_runs", "resource_attributes")
    op.drop_column("agent_runs", "external_trace_state")
    op.drop_column("agent_runs", "external_trace_id")
    op.drop_column("agent_runs", "source_type")
