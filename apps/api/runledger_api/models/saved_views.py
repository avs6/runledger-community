"""Per-user saved views for the Observe list pages (Runs, Request Explorer, Sessions).

A saved view is a name plus the page's URL query string. Storage is deliberately
minimal: a later user-preferences API (review W2-C) can absorb these rows.
"""

from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from runledger_api.core.db import Base

SAVED_VIEW_PAGES = ("runs", "explorer", "sessions")


class SavedView(Base):
    __tablename__ = "saved_views"
    __table_args__ = (
        sa.UniqueConstraint("workspace_id", "user_id", "page", "name", name="uq_saved_views_name"),
        sa.Index("ix_saved_views_owner", "workspace_id", "user_id", "page"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    page: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    name: Mapped[str] = mapped_column(sa.String(120), nullable=False)
    query: Mapped[str] = mapped_column(sa.Text, nullable=False, server_default="")
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
    )
