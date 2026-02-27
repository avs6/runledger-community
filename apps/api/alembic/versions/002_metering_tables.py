"""Metering tables: provider_pricing, usage_hourly, usage_daily, data_quality_issues

Revision ID: 002
Revises: 001
Create Date: 2026-02-26
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── provider_pricing ──────────────────────────────────────────────────────
    # Effective-dated pricing table. workspace_id=NULL means global default.
    # workspace_id IS NOT NULL means a workspace-specific override.
    op.create_table(
        "provider_pricing",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("input_cost_per_1m", sa.Numeric(14, 8), nullable=False),
        sa.Column("output_cost_per_1m", sa.Numeric(14, 8), nullable=False),
        sa.Column(
            "cached_input_cost_per_1m",
            sa.Numeric(14, 8),
            nullable=True,
            comment="NULL means use input_cost_per_1m * 0.5 as default",
        ),
        sa.Column("effective_from", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("effective_to", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("workspace_id", PGUUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    # An index to efficiently find the right price row for a given model + time
    op.create_index(
        "ix_provider_pricing_lookup",
        "provider_pricing",
        ["provider", "model", "effective_from"],
    )
    op.create_index(
        "ix_provider_pricing_workspace",
        "provider_pricing",
        ["workspace_id", "provider", "model"],
    )

    # ── usage_hourly ──────────────────────────────────────────────────────────
    op.create_table(
        "usage_hourly",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workspace_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("feature_tag", sa.String(255), nullable=True),
        sa.Column("end_user_id", sa.String(255), nullable=True),
        sa.Column("hour", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("input_tokens", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Numeric(18, 8), nullable=False, server_default="0"),
        sa.Column("run_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("call_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "computed_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_usage_hourly_workspace_hour",
        "usage_hourly",
        ["workspace_id", "hour"],
    )
    op.create_index(
        "ix_usage_hourly_model",
        "usage_hourly",
        ["workspace_id", "model", "hour"],
    )

    # ── usage_daily ───────────────────────────────────────────────────────────
    op.create_table(
        "usage_daily",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workspace_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("feature_tag", sa.String(255), nullable=True),
        sa.Column("end_user_id", sa.String(255), nullable=True),
        sa.Column("day", sa.Date, nullable=False),
        sa.Column("input_tokens", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Numeric(18, 8), nullable=False, server_default="0"),
        sa.Column("run_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("call_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "computed_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_usage_daily_workspace_day",
        "usage_daily",
        ["workspace_id", "day"],
    )

    # ── data_quality_issues ───────────────────────────────────────────────────
    op.create_table(
        "data_quality_issues",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workspace_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("provider_call_id", PGUUID(as_uuid=True), nullable=True),
        sa.Column("run_id", PGUUID(as_uuid=True), nullable=True),
        sa.Column("issue_type", sa.String(64), nullable=False),
        sa.Column("details", JSONB, nullable=True),
        sa.Column("resolved", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "detected_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_data_quality_workspace",
        "data_quality_issues",
        ["workspace_id", "detected_at"],
    )
    op.create_index(
        "ix_data_quality_provider_call",
        "data_quality_issues",
        ["provider_call_id"],
    )


def downgrade() -> None:
    op.drop_table("data_quality_issues")
    op.drop_table("usage_daily")
    op.drop_table("usage_hourly")
    op.drop_table("provider_pricing")
