"""Pydantic schemas for the Model Gateway endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


# ── Route schemas ──────────────────────────────────────────────────────────────


class GatewayRouteCreate(BaseModel):
    alias: str = Field(..., min_length=1, max_length=128, description="Model alias clients use")
    provider: str = Field(
        ..., pattern="^(openai|anthropic|ollama|groq|mistral|custom)$"
    )
    target_model: str = Field(..., min_length=1, max_length=128)
    base_url: str | None = None
    api_key_env_var: str | None = None
    priority: int = Field(10, ge=1, le=100)


class GatewayRouteUpdate(BaseModel):
    alias: str | None = None
    target_model: str | None = None
    base_url: str | None = None
    api_key_env_var: str | None = None
    priority: int | None = Field(None, ge=1, le=100)
    is_active: bool | None = None


class GatewayRouteResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    alias: str
    provider: str
    target_model: str
    base_url: str | None
    api_key_env_var: str | None
    priority: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class GatewayRouteList(BaseModel):
    items: list[GatewayRouteResponse]


# ── Completion request / response ──────────────────────────────────────────────


class GatewayMessage(BaseModel):
    role: str
    content: str


class GatewayCompletionRequest(BaseModel):
    model: str = Field(..., description="Alias or model name to route")
    messages: list[GatewayMessage]
    temperature: float | None = None
    max_tokens: int | None = None
    stream: bool = False
    cache: bool = Field(True, description="Enable prompt cache lookup for this request")


# ── Stats schema ───────────────────────────────────────────────────────────────


class GatewayRouteStats(BaseModel):
    route_id: uuid.UUID | None
    alias: str
    total_requests: int
    cache_hits: int
    cache_hit_rate: Decimal
    avg_latency_ms: Decimal | None
    error_count: int


class GatewayStats(BaseModel):
    total_requests: int
    cache_hits: int
    cache_hit_rate: Decimal
    avg_latency_ms: Decimal | None
    routes: list[GatewayRouteStats]


# ── Request log schema ─────────────────────────────────────────────────────────


class GatewayRequestResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    route_id: uuid.UUID | None
    model_requested: str
    model_used: str | None
    cache_hit: bool
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
