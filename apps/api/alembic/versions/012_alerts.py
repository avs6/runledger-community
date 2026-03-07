"""Add alert_rules and alert_firings tables.

Revision ID: 012
Revises: 011
Create Date: 2026-03-06
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "012"
down_revision: str | None = "011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "alert_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("metric", sa.String(32), nullable=False),
        sa.Column("operator", sa.String(4), nullable=False),
        sa.Column("threshold", sa.Numeric(14, 6), nullable=False),
        sa.Column("window_minutes", sa.Integer, nullable=False, server_default="60"),
        sa.Column("action", sa.Text, nullable=False, server_default="notify"),
        sa.Column("channel_id", UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["channel_id"],
            ["budget_notifications.id"],
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_alert_rules_workspace", "alert_rules", ["workspace_id", "is_active"])

    op.create_table(
        "alert_firings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("rule_id", UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "fired_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("metric_value", sa.Numeric(14, 6), nullable=False),
        sa.Column("resolved_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["rule_id"],
            ["alert_rules.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_alert_firings_rule", "alert_firings", ["rule_id", "fired_at"])
    op.create_index("ix_alert_firings_workspace", "alert_firings", ["workspace_id", "fired_at"])


def downgrade() -> None:
    op.drop_index("ix_alert_firings_workspace", "alert_firings")
    op.drop_index("ix_alert_firings_rule", "alert_firings")
    op.drop_table("alert_firings")
    op.drop_index("ix_alert_rules_workspace", "alert_rules")
    op.drop_table("alert_rules")
