"""eval_experiments and eval_datasets tables

Revision ID: 043
Revises: 042
Create Date: 2026-03-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision = "043"
down_revision = "042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "eval_datasets",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("source", sa.String(32), nullable=False, server_default="manual"),
        sa.Column("items", JSONB, nullable=False, server_default="[]"),
        sa.Column("item_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index("ix_eval_datasets_workspace", "eval_datasets", ["workspace_id", "created_at"])

    op.create_table(
        "eval_experiments",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column(
            "dataset_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("eval_datasets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("prompt_name", sa.Text, nullable=True),
        sa.Column("prompt_version", sa.Integer, nullable=True),
        sa.Column("evaluator_ids", JSONB, nullable=False, server_default="[]"),
        sa.Column("models", JSONB, nullable=False, server_default="[]"),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("results", JSONB, nullable=True),
        sa.Column("run_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("scores_created", sa.Integer, nullable=False, server_default="0"),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_by", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_eval_experiments_workspace", "eval_experiments", ["workspace_id", "created_at"]
    )

    # GitHub sync config per workspace
    op.create_table(
        "prompt_github_configs",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("repo", sa.Text, nullable=False),
        sa.Column("branch", sa.String(128), nullable=False, server_default="main"),
        sa.Column("path_prefix", sa.String(256), nullable=False, server_default="prompts/"),
        sa.Column("token_enc", sa.Text, nullable=True),
        sa.Column("auto_sync", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("last_sync_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_sync_status", sa.String(16), nullable=True),
        sa.Column("last_sync_message", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("prompt_github_configs")
    op.drop_index("ix_eval_experiments_workspace", table_name="eval_experiments")
    op.drop_table("eval_experiments")
    op.drop_index("ix_eval_datasets_workspace", table_name="eval_datasets")
    op.drop_table("eval_datasets")
