"""Add guardrail enhancements — alerts, bypass, per-key config, system message skip, feedback.

Revision ID: 058
Revises: 057
Create Date: 2026-08-04
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision = "058"
down_revision = "057"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # GuardrailRule — skip_system_messages flag
    op.add_column(
        "guardrail_rules",
        sa.Column("skip_system_messages", sa.Boolean, server_default=sa.text("false"), nullable=False),
    )

    # GuardrailEvent — extra dimensions for monitoring breakdown
    op.add_column(
        "guardrail_events",
        sa.Column("model", sa.Text, nullable=True),
    )
    op.add_column(
        "guardrail_events",
        sa.Column("user_id", sa.Text, nullable=True),
    )
    op.add_column(
        "guardrail_events",
        sa.Column("error", sa.Text, nullable=True),
    )
    op.add_column(
        "guardrail_events",
        sa.Column("is_false_positive", sa.Boolean, server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "guardrail_events",
        sa.Column("feedback_reason", sa.Text, nullable=True),
    )

    # Workspace guardrail settings
    op.add_column(
        "workspaces",
        sa.Column("guardrail_bypass", sa.Boolean, server_default=sa.text("false"), nullable=False),
    )

    # ApiKey guardrail config
    op.add_column(
        "api_keys",
        sa.Column("guardrail_config", JSONB, server_default=sa.text("'{}'"), nullable=False),
    )

    # Guardrail alerts table
    op.create_table(
        "guardrail_alerts",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("alert_type", sa.Text, nullable=False),
        sa.Column("severity", sa.Text, nullable=False, server_default=sa.text("'warning'")),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("metric_value", sa.Float, nullable=True),
        sa.Column("threshold_value", sa.Float, nullable=True),
        sa.Column("guardrail_rule_id", PGUUID(as_uuid=True), nullable=True),
        sa.Column("guardrail_name", sa.Text, nullable=True),
        sa.Column("alert_metadata", JSONB, server_default=sa.text("'{}'"), nullable=False),
        sa.Column("status", sa.Text, nullable=False, server_default=sa.text("'active'")),
        sa.Column("acknowledged_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_guardrail_alerts_workspace", "guardrail_alerts", ["workspace_id"])
    op.create_index("ix_guardrail_alerts_workspace_type", "guardrail_alerts", ["workspace_id", "alert_type"])
    op.create_index("ix_guardrail_alerts_created", "guardrail_alerts", ["created_at"])


def downgrade() -> None:
    op.drop_table("guardrail_alerts")
    op.drop_column("api_keys", "guardrail_config")
    op.drop_column("workspaces", "guardrail_bypass")
    op.drop_column("guardrail_events", "feedback_reason")
    op.drop_column("guardrail_events", "is_false_positive")
    op.drop_column("guardrail_events", "error")
    op.drop_column("guardrail_events", "user_id")
    op.drop_column("guardrail_events", "model")
    op.drop_column("guardrail_rules", "skip_system_messages")
