"""RetentionPolicy ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from runledger_api.core.db import Base


class RetentionPolicy(Base):
    __tablename__ = "retention_policies"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    resource_type: Mapped[str] = mapped_column(sa.Text, nullable=False)
    action: Mapped[str] = mapped_column(sa.Text, nullable=False)
    scope: Mapped[str] = mapped_column(sa.Text, nullable=False, server_default=sa.text("'workspace'"))
    scope_value: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    max_age_days: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text("TRUE"))
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
    last_run_at: Mapped[datetime | None] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=True)
    last_purged_count: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
