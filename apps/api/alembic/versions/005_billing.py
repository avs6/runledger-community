"""Billing tables: billing_periods, chargeback_rules, usage_snapshots

Revision ID: 005
Revises: 004
Create Date: 2026-02-27
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── billing_periods ───────────────────────────────────────────────────────
    op.create_table(
        "billing_periods",
        sa.Column(
            "id",
            PGUUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "workspace_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column(
            "status",
            sa.String(16),
            nullable=False,
            server_default=sa.text("'open'"),
        ),
        sa.Column("total_cost_usd", sa.Numeric(14, 6), nullable=True),
        sa.Column("snapshot_hash", sa.Text, nullable=True),
        sa.Column("closed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_billing_periods_workspace",
        "billing_periods",
        ["workspace_id", "status"],
    )
    op.create_index(
        "ix_billing_periods_dates",
        "billing_periods",
        ["workspace_id", "period_start", "period_end"],
    )

    # ── chargeback_rules ──────────────────────────────────────────────────────
    op.create_table(
        "chargeback_rules",
        sa.Column(
            "id",
            PGUUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "workspace_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("allocation_type", sa.String(32), nullable=False),
        sa.Column("dimension", sa.Text, nullable=False),
        sa.Column("weight", sa.Numeric(6, 4), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_chargeback_rules_workspace",
        "chargeback_rules",
        ["workspace_id"],
    )

    # ── usage_snapshots ───────────────────────────────────────────────────────
    op.create_table(
        "usage_snapshots",
        sa.Column(
            "id",
            PGUUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "billing_period_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("billing_periods.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("snapshot_data", JSONB, nullable=False),
        sa.Column("signature", sa.Text, nullable=False),
        sa.Column(
            "signing_key_id",
            sa.Text,
            nullable=False,
            server_default=sa.text("'v1'"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_usage_snapshots_period",
        "usage_snapshots",
        ["billing_period_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_usage_snapshots_period", "usage_snapshots")
    op.drop_table("usage_snapshots")
    op.drop_index("ix_chargeback_rules_workspace", "chargeback_rules")
    op.drop_table("chargeback_rules")
    op.drop_index("ix_billing_periods_dates", "billing_periods")
    op.drop_index("ix_billing_periods_workspace", "billing_periods")
    op.drop_table("billing_periods")
