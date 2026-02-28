"""Add user_anomalies, replay_datasets, replay_experiments tables.

Revision ID: 007
Revises: 006
Create Date: 2026-02-27
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID

revision: str = "007"
down_revision: str | None = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # user_anomalies
    op.create_table(
        "user_anomalies",
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
        sa.Column("end_user_id", sa.Text, nullable=False),
        sa.Column("detected_at", sa.Date, nullable=False),
        sa.Column("daily_spend", sa.Numeric(14, 8), nullable=False),
        sa.Column("mean_spend", sa.Numeric(14, 8), nullable=False),
        sa.Column("zscore", sa.Numeric(8, 4), nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_user_anomalies_workspace_date",
        "user_anomalies",
        ["workspace_id", "detected_at"],
    )

    # replay_datasets
    op.create_table(
        "replay_datasets",
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
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("source", sa.Text, nullable=False, server_default="live_runs"),
        sa.Column("run_ids", JSONB, nullable=False, server_default="[]"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_replay_datasets_workspace",
        "replay_datasets",
        ["workspace_id", "created_at"],
    )

    # replay_experiments
    op.create_table(
        "replay_experiments",
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
        sa.Column(
            "dataset_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("replay_datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("configs", JSONB, nullable=False, server_default="[]"),
        sa.Column("status", sa.Text, nullable=False, server_default="pending"),
        sa.Column("results", JSONB, nullable=True),
        sa.Column("estimated_cost_usd", sa.Numeric(14, 8), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_replay_experiments_workspace",
        "replay_experiments",
        ["workspace_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_replay_experiments_workspace", "replay_experiments")
    op.drop_table("replay_experiments")
    op.drop_index("ix_replay_datasets_workspace", "replay_datasets")
    op.drop_table("replay_datasets")
    op.drop_index("ix_user_anomalies_workspace_date", "user_anomalies")
    op.drop_table("user_anomalies")
