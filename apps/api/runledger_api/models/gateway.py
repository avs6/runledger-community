"""
ORM models for the Model Gateway: routes, request log, and prompt cache.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from runledger_api.core.db import Base


class GatewayRoute(Base):
    """
    A configured provider route that the gateway can forward requests to.

    alias        — model name clients send (e.g. "gpt-4o")
    provider     — provider slug (e.g. "openai", "anthropic", "ollama")
    target_model — actual model name sent to the provider
    base_url     — provider API base URL (override for custom/Ollama endpoints)
    api_key_env_var — env var name holding the API key (e.g. "OPENAI_API_KEY")
    priority     — lower number = higher priority (tried first)
    is_active    — soft-disable without deletion
    """

    __tablename__ = "gateway_routes"
    __table_args__ = (
        sa.Index("ix_gateway_routes_workspace", "workspace_id", "alias", "priority"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    alias: Mapped[str] = mapped_column(sa.Text, nullable=False)
    provider: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    target_model: Mapped[str] = mapped_column(sa.Text, nullable=False)
    base_url: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    api_key_env_var: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    priority: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default="10")
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class GatewayRequest(Base):
    """
    Log entry for each request forwarded through the gateway.

    status values: success | error | cache_hit
    """

    __tablename__ = "gateway_requests"
    __table_args__ = (
        sa.Index("ix_gateway_requests_workspace", "workspace_id", "created_at"),
        sa.Index("ix_gateway_requests_route", "route_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    route_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("gateway_routes.id", ondelete="SET NULL"),
        nullable=True,
    )
    model_requested: Mapped[str] = mapped_column(sa.Text, nullable=False)
    model_used: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    cache_hit: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )
    input_tokens: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    status: Mapped[str] = mapped_column(sa.String(16), nullable=False, server_default="success")
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class PromptCache(Base):
    """
    SHA-256 keyed cache of provider responses for identical prompts.

    cache_key    — SHA-256 of (model + messages JSON, sorted)
    hit_count    — incremented on each cache hit
    expires_at   — TTL; worker can prune expired rows
    """

    __tablename__ = "prompt_cache"
    __table_args__ = (
        sa.UniqueConstraint("workspace_id", "cache_key", name="uq_prompt_cache_key"),
        sa.Index("ix_prompt_cache_expires", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    cache_key: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    model: Mapped[str] = mapped_column(sa.Text, nullable=False)
    response_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    prompt_tokens: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    hit_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True
    )
