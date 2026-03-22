"""ORM model for LLM-judge and rule-based evaluators."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from runledger_api.core.db import Base


class Evaluator(Base):
    """
    An evaluator defines how to automatically score agent runs.

    type = "llm_judge"
        config keys: model, api_key, base_url, prompt_template, criteria,
                     min_score (float 0-1), max_score (float 0-1)

    type = "rule"
        config keys: rules: [{field, op, value, score_if_pass, score_if_fail}]
                     Supported ops: eq, neq, gt, gte, lt, lte, contains, regex
    """

    __tablename__ = "evaluators"
    __table_args__ = (
        sa.Index("ix_evaluators_workspace", "workspace_id"),
        sa.Index("ix_evaluators_workspace_name", "workspace_id", "name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    type: Mapped[str] = mapped_column(sa.String(32), nullable=False, server_default="rule")
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=sa.text("'{}'"))
    status: Mapped[str] = mapped_column(sa.String(16), nullable=False, server_default="active")
    last_run_at: Mapped[datetime | None] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=True)
    last_run_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("0"))
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
