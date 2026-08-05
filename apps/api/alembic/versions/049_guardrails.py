"""Add guardrails tables for content safety and policy engine.

Revision ID: 049
Revises: 048
Create Date: 2026-08-04
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "049"
down_revision = "048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "guardrail_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("mode", sa.Text, nullable=False, server_default="pre_call"),
        sa.Column("rule_type", sa.Text, nullable=False, server_default="custom"),
        sa.Column("logic", sa.Text, nullable=True),
        sa.Column("config", JSONB, nullable=False, server_default="{}"),
        sa.Column("severity", sa.Text, nullable=False, server_default="medium"),
        sa.Column("priority", sa.Integer, nullable=False, server_default="100"),
        sa.Column("status", sa.Text, nullable=False, server_default="active"),
        sa.Column("template_id", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("ix_guardrail_rules_workspace", "guardrail_rules", ["workspace_id"])
    op.create_index(
        "ix_guardrail_rules_workspace_status",
        "guardrail_rules",
        ["workspace_id", "status"],
    )
    op.create_index(
        "ix_guardrail_rules_workspace_type",
        "guardrail_rules",
        ["workspace_id", "rule_type"],
    )

    op.create_table(
        "guardrail_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("guardrail_rule_id", UUID(as_uuid=True), nullable=False),
        sa.Column("guardrail_name", sa.Text, nullable=False),
        sa.Column("mode", sa.Text, nullable=False),
        sa.Column("decision", sa.Text, nullable=False),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("latency_ms", sa.Float, nullable=False, server_default="0"),
        sa.Column("request_metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("gateway_request_id", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("ix_guardrail_events_workspace", "guardrail_events", ["workspace_id"])
    op.create_index(
        "ix_guardrail_events_workspace_decision",
        "guardrail_events",
        ["workspace_id", "decision"],
    )
    op.create_index("ix_guardrail_events_rule", "guardrail_events", ["guardrail_rule_id"])
    op.create_index("ix_guardrail_events_created", "guardrail_events", ["created_at"])

    op.create_table(
        "partner_guardrails",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.Text, nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("mode", sa.Text, nullable=False, server_default="pre_call"),
        sa.Column("endpoint_url", sa.Text, nullable=True),
        sa.Column("credentials", JSONB, nullable=False, server_default="{}"),
        sa.Column("config", JSONB, nullable=False, server_default="{}"),
        sa.Column("timeout_ms", sa.Integer, nullable=False, server_default="2000"),
        sa.Column("fallback_action", sa.Text, nullable=False, server_default="allow"),
        sa.Column("priority", sa.Integer, nullable=False, server_default="200"),
        sa.Column("status", sa.Text, nullable=False, server_default="active"),
        sa.Column("last_health_check", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("health_status", sa.Text, nullable=True),
        sa.Column("total_calls", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_cost_usd", sa.Float, nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("ix_partner_guardrails_workspace", "partner_guardrails", ["workspace_id"])
    op.create_index(
        "ix_partner_guardrails_workspace_provider",
        "partner_guardrails",
        ["workspace_id", "provider"],
    )

    op.create_table(
        "guardrail_test_cases",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("guardrail_rule_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("input_text", sa.Text, nullable=False),
        sa.Column("input_metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("expected_decision", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("ix_guardrail_test_cases_workspace", "guardrail_test_cases", ["workspace_id"])
    op.create_index(
        "ix_guardrail_test_cases_rule",
        "guardrail_test_cases",
        ["guardrail_rule_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_guardrail_test_cases_rule", table_name="guardrail_test_cases")
    op.drop_index("ix_guardrail_test_cases_workspace", table_name="guardrail_test_cases")
    op.drop_table("guardrail_test_cases")

    op.drop_index("ix_partner_guardrails_workspace_provider", table_name="partner_guardrails")
    op.drop_index("ix_partner_guardrails_workspace", table_name="partner_guardrails")
    op.drop_table("partner_guardrails")

    op.drop_index("ix_guardrail_events_created", table_name="guardrail_events")
    op.drop_index("ix_guardrail_events_rule", table_name="guardrail_events")
    op.drop_index("ix_guardrail_events_workspace_decision", table_name="guardrail_events")
    op.drop_index("ix_guardrail_events_workspace", table_name="guardrail_events")
    op.drop_table("guardrail_events")

    op.drop_index("ix_guardrail_rules_workspace_type", table_name="guardrail_rules")
    op.drop_index("ix_guardrail_rules_workspace_status", table_name="guardrail_rules")
    op.drop_index("ix_guardrail_rules_workspace", table_name="guardrail_rules")
    op.drop_table("guardrail_rules")
