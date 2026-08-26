"""ORM models for the AI Hub model catalog."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from runledger_api.core.db import Base


class HubModel(Base):
    __tablename__ = "hub_models"
    __table_args__ = (sa.Index("ix_hub_models_workspace", "workspace_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    provider: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    capabilities: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'[]'")
    )
    context_window: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    input_cost_per_1k: Mapped[Decimal | None] = mapped_column(sa.Numeric(12, 6), nullable=True)
    output_cost_per_1k: Mapped[Decimal | None] = mapped_column(sa.Numeric(12, 6), nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default=sa.text("'[]'"))
    is_featured: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )
    is_deprecated: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )
    deprecation_notice: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )
    access_request_count: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default=sa.text("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
