"""
ORM models for the Model Gateway: routes, routing policies, request log, and prompt cache.
"""

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
    __table_args__ = (sa.Index("ix_gateway_routes_workspace", "workspace_id", "alias", "priority"),)

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
    config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )
    # ── Phase 30: Runtime controls ─────────────────────────────────────────────
    daily_cost_limit_usd: Mapped[Decimal | None] = mapped_column(sa.NUMERIC(12, 4), nullable=True)
    monthly_cost_limit_usd: Mapped[Decimal | None] = mapped_column(sa.NUMERIC(12, 4), nullable=True)
    pii_redaction_enabled: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )
    # When enabled, requests to this alias also consult the semantic (near-duplicate) cache.
    semantic_cache_enabled: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )
    # When enabled, the Context Compiler shrinks the request before routing.
    context_compiler_enabled: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )
    # Compiler settings: model, reranker_model, token_threshold, token_budget, stages{}.
    context_compiler_config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    per_user_rpm_limit: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    health_auto_disable: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )
    last_health_check_at: Mapped[datetime | None] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True
    )
    consecutive_health_failures: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default="0"
    )
    disabled_reason: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
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
    decision_reason: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class RoutingPolicy(Base):
    """
    A routing policy that governs how the gateway selects routes for a given alias.

    policy_type values:
      manual            — priority order (default, existing behaviour)
      cost_optimized    — cheapest route above a quality floor
      latency_optimized — lowest p95 latency from recent gateway_requests
      quality_optimized — highest avg score from score_events
      weighted          — weighted random split across routes
      canary            — send X% to a canary route, rest via priority
      budget_aware      — downgrade to cheaper alias when budget threshold hit
      complexity_based  — branch to different alias based on input token count

    config keys (by type):
      cost_optimized:    quality_floor (0–1), lookback_days
      latency_optimized: max_p95_ms, quality_floor, lookback_hours
      quality_optimized: metric ("quality"|"relevance"), lookback_days
      weighted:          weights {route_id: float, ...}
      canary:            canary_route_id, canary_pct (0–1)
      budget_aware:      budget_id, threshold_pct (0–1), fallback_alias
      complexity_based:  token_threshold, simple_alias, complex_alias
    """

    __tablename__ = "routing_policies"
    __table_args__ = (
        sa.UniqueConstraint("workspace_id", "alias", name="uq_routing_policies_workspace_alias"),
        sa.Index("ix_routing_policies_workspace", "workspace_id", "alias"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    alias: Mapped[str] = mapped_column(sa.Text, nullable=False)
    policy_type: Mapped[str] = mapped_column(sa.String(32), nullable=False, server_default="manual")
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'{}'")
    )
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
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
    response_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    prompt_tokens: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    hit_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=True)
