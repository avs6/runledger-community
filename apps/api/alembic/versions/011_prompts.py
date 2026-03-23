"""Add prompts and prompt_versions tables.

Revision ID: 011
Revises: 010
Create Date: 2026-03-06
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision: str = "011"
down_revision: str | None = "010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "prompts",
        sa.Column("id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("default_environment", sa.Text(), nullable=False, server_default="production"),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "name", name="ix_prompts_workspace_name"),
    )

    op.create_table(
        "prompt_versions",
        sa.Column("id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("prompt_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("variables", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("commit_message", sa.Text(), nullable=True),
        sa.Column("environment", sa.Text(), nullable=False, server_default="production"),
        sa.Column("model_hint", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["prompt_id"], ["prompts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("prompt_id", "version", name="ix_prompt_versions_prompt_version"),
    )
    op.create_index(
        "ix_prompt_versions_prompt_env",
        "prompt_versions",
        ["prompt_id", "environment"],
    )


def downgrade() -> None:
    op.drop_index("ix_prompt_versions_prompt_env", table_name="prompt_versions")
    op.drop_table("prompt_versions")
    op.drop_table("prompts")
