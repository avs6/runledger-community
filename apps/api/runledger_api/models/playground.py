"""ORM models for API playground."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from runledger_api.core.db import Base


class PlaygroundSession(Base):
    __tablename__ = "playground_sessions"
    __table_args__ = (sa.Index("ix_playground_sessions_workspace", "workspace_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    name: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    system_prompt: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    mode: Mapped[str] = mapped_column(sa.Text, nullable=False, server_default=sa.text("'single'"))
    is_favorite: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'{}'")
    )
    created_by: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class PlaygroundRequest(Base):
    __tablename__ = "playground_requests"
    __table_args__ = (
        sa.Index("ix_playground_requests_workspace", "workspace_id"),
        sa.Index("ix_playground_requests_session", "session_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    session_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    model: Mapped[str] = mapped_column(sa.Text, nullable=False)
    provider: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    system_prompt: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    user_prompt: Mapped[str] = mapped_column(sa.Text, nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'{}'")
    )
    response_text: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    cost_usd: Mapped[Decimal | None] = mapped_column(
        sa.Numeric(precision=12, scale=6), nullable=True
    )
    latency_ms: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default=sa.text("'pending'")
    )
    route_decision: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    error: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    gateway_request_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
