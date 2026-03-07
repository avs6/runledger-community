"""ORM models for prompt management."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from runledger_api.core.db import Base


class Prompt(Base):
    """A named prompt template with versioned content."""

    __tablename__ = "prompts"
    __table_args__ = (
        sa.UniqueConstraint("workspace_id", "name", name="ix_prompts_workspace_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    default_environment: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default="production"
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )

    versions: Mapped[list[PromptVersion]] = relationship(
        "PromptVersion", back_populates="prompt", cascade="all, delete-orphan"
    )


class PromptVersion(Base):
    """A specific version of a prompt template."""

    __tablename__ = "prompt_versions"
    __table_args__ = (
        sa.UniqueConstraint("prompt_id", "version", name="ix_prompt_versions_prompt_version"),
        sa.Index("ix_prompt_versions_prompt_env", "prompt_id", "environment"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    prompt_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("prompts.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    content: Mapped[str] = mapped_column(sa.Text, nullable=False)
    variables: Mapped[Any] = mapped_column(JSONB, nullable=False, server_default="[]")
    commit_message: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    environment: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default="production"
    )
    model_hint: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )

    prompt: Mapped[Prompt] = relationship("Prompt", back_populates="versions")
