"""ORM models for evaluation experiments, datasets, and GitHub prompt sync."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from runledger_api.core.db import Base


class EvalDataset(Base):
    """
    A collection of test cases (input/expected_output pairs) used as experiment input.
    Items are stored as JSONB: [{input, expected_output, metadata}]
    """

    __tablename__ = "eval_datasets"
    __table_args__ = (sa.Index("ix_eval_datasets_workspace", "workspace_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    source: Mapped[str] = mapped_column(sa.String(32), nullable=False, default="manual")
    items: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    item_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class EvalExperiment(Base):
    """
    An evaluation experiment: run a prompt against a dataset and score with evaluators.
    Links to an existing Prompt by name/version and one or more Evaluators.
    """

    __tablename__ = "eval_experiments"
    __table_args__ = (sa.Index("ix_eval_experiments_workspace", "workspace_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("eval_datasets.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    # Linked prompt (by name + version from this workspace)
    prompt_name: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    prompt_version: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    # Which evaluator IDs to run after experiment completes
    evaluator_ids: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    # Model configs to test: [{"model": "gpt-4o", "provider": "openai", "label": "..."}]
    models: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(sa.String(16), nullable=False, default="pending")
    results: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    run_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    scores_created: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    started_at: Mapped[datetime | None] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True
    )
    created_by: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class PromptGithubConfig(Base):
    """Per-workspace GitHub sync config for prompt management."""

    __tablename__ = "prompt_github_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    repo: Mapped[str] = mapped_column(sa.Text, nullable=False)
    branch: Mapped[str] = mapped_column(sa.String(128), nullable=False, default="main")
    path_prefix: Mapped[str] = mapped_column(sa.String(256), nullable=False, default="prompts/")
    token_enc: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    auto_sync: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    last_sync_at: Mapped[datetime | None] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True
    )
    last_sync_status: Mapped[str | None] = mapped_column(sa.String(16), nullable=True)
    last_sync_message: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
