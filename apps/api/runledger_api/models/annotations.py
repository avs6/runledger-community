"""ORM model for team annotations anchored to a date or deployment version."""

from __future__ import annotations

import uuid
from datetime import date, datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from runledger_api.core.db import Base


class Annotation(Base):
    """
    A team note anchored to a calendar date and optionally to a deployment_version.

    Examples:
      - "switched gpt-4o → gpt-4o-mini on 2026-02-27, version v2.1"
      - "added caching layer — latency dropped 40ms"
    """

    __tablename__ = "annotations"
    __table_args__ = (
        sa.Index("ix_annotations_workspace_date", "workspace_id", "annotation_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    note: Mapped[str] = mapped_column(sa.Text, nullable=False)
    annotation_date: Mapped[date] = mapped_column(sa.Date, nullable=False)
    version: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
