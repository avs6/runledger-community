"""Ingest events that could not be applied, kept for inspection and replay."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from runledger_api.core.db import Base


class IngestDeadLetter(Base):
    """One ingest event the pipeline failed to apply.

    The pipeline applies each event in its own savepoint; a failing event is stored
    here (with the error) instead of aborting its batch. Workspace admins can list,
    replay or discard dead letters (``/ingest/v1/dead-letters``).

    status: ``pending`` (awaiting replay) · ``replayed`` (re-queued and applied) ·
    ``discarded`` (dismissed by an admin).
    """

    __tablename__ = "ingest_dead_letters"
    __table_args__ = (
        sa.Index("ix_ingest_dead_letters_ws_status", "workspace_id", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    event_type: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
    run_id: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
    event: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    error: Mapped[str] = mapped_column(sa.Text, nullable=False)
    attempts: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(sa.String(16), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
    last_attempt_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
