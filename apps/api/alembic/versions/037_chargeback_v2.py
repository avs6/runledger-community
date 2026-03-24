"""037 — Chargeback v2: cost_centers, billing_adjustments, multi-currency

Revision ID: 037
Revises: 036
Create Date: 2026-03-24
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision = "037"
down_revision = "036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── cost_centers ──────────────────────────────────────────────────────────
    op.create_table(
        "cost_centers",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("code", sa.String(64), nullable=True),
        sa.Column(
            "parent_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("cost_centers.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index("ix_cost_centers_workspace", "cost_centers", ["workspace_id"])
    op.create_index(
        "ix_cost_centers_parent", "cost_centers", ["workspace_id", "parent_id"]
    )

    # ── billing_adjustments ───────────────────────────────────────────────────
    op.create_table(
        "billing_adjustments",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column(
            "billing_period_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("billing_periods.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "adjustment_type",
            sa.String(32),
            nullable=False,
        ),  # credit | refund | prepaid_deduction | surcharge
        sa.Column("amount_usd", sa.Numeric(14, 6), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("reference_id", sa.Text, nullable=True),
        sa.Column("created_by", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_billing_adjustments_period", "billing_adjustments", ["billing_period_id"]
    )
    op.create_index(
        "ix_billing_adjustments_workspace", "billing_adjustments", ["workspace_id"]
    )

    # ── chargeback_rules — add cost_center_id FK ──────────────────────────────
    op.add_column(
        "chargeback_rules",
        sa.Column(
            "cost_center_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("cost_centers.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # ── billing_periods — add multi-currency fields ───────────────────────────
    op.add_column(
        "billing_periods",
        sa.Column(
            "currency", sa.String(3), nullable=False, server_default=sa.text("'USD'")
        ),
    )
    op.add_column(
        "billing_periods",
        sa.Column(
            "exchange_rate_to_usd",
            sa.Numeric(12, 6),
            nullable=False,
            server_default=sa.text("1.0"),
        ),
    )
    op.add_column(
        "billing_periods",
        sa.Column(
            "net_cost_usd",
            sa.Numeric(14, 6),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("billing_periods", "net_cost_usd")
    op.drop_column("billing_periods", "exchange_rate_to_usd")
    op.drop_column("billing_periods", "currency")
    op.drop_column("chargeback_rules", "cost_center_id")
    op.drop_table("billing_adjustments")
    op.drop_table("cost_centers")
