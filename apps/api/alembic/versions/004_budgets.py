"""Budget tables: budgets, budget_breaches, budget_notifications

Revision ID: 004
Revises: 003
Create Date: 2026-02-27
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PGUUID

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── budgets ───────────────────────────────────────────────────────────────
    op.create_table(
        "budgets",
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
        sa.Column("scope_type", sa.String(32), nullable=False),
        sa.Column("scope_id", sa.Text, nullable=True),
        sa.Column("period_type", sa.String(16), nullable=False),
        sa.Column("limit_usd", sa.Numeric(14, 6), nullable=False),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("downgrade_to_model", sa.Text, nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_budgets_workspace",
        "budgets",
        ["workspace_id", "is_active"],
    )

    # ── budget_breaches ───────────────────────────────────────────────────────
    op.create_table(
        "budget_breaches",
        sa.Column(
            "id",
            PGUUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "budget_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("budgets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "occurred_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("spend_at_breach_usd", sa.Numeric(14, 6), nullable=True),
        sa.Column("action_taken", sa.String(16), nullable=True),
        sa.Column("notified_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_budget_breaches_budget",
        "budget_breaches",
        ["budget_id", "occurred_at"],
    )

    # ── budget_notifications ──────────────────────────────────────────────────
    op.create_table(
        "budget_notifications",
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
        sa.Column("channel", sa.String(16), nullable=False),
        sa.Column("destination_url", sa.Text, nullable=False),
        sa.Column("events", ARRAY(sa.Text), nullable=False, server_default="{}"),
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_budget_notifications_workspace",
        "budget_notifications",
        ["workspace_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_budget_notifications_workspace", "budget_notifications")
    op.drop_table("budget_notifications")
    op.drop_index("ix_budget_breaches_budget", "budget_breaches")
    op.drop_table("budget_breaches")
    op.drop_index("ix_budgets_workspace", "budgets")
    op.drop_table("budgets")
