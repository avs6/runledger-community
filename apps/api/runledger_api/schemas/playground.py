"""Pydantic schemas for API playground."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field

PlaygroundMode = Literal["single", "conversation", "compare"]
RequestStatus = Literal["pending", "completed", "failed"]


class PlaygroundSessionCreate(BaseModel):
    name: str | None = Field(None, max_length=200)
    system_prompt: str | None = Field(None, max_length=100_000)
    mode: PlaygroundMode = "single"
    config: dict[str, Any] = Field(default_factory=dict)


class PlaygroundSessionUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    system_prompt: str | None = Field(None, max_length=100_000)
    is_favorite: bool | None = None
    config: dict[str, Any] | None = None


class PlaygroundSessionResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str | None = None
    system_prompt: str | None = None
    mode: str
    is_favorite: bool
    config: dict[str, Any]
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime


class PlaygroundSessionListResponse(BaseModel):
    sessions: list[PlaygroundSessionResponse]
    total: int


class PlaygroundSendRequest(BaseModel):
    model: str = Field(..., max_length=200)
    provider: str | None = Field(None, max_length=200)
    system_prompt: str | None = Field(None, max_length=100_000)
    user_prompt: str = Field(..., max_length=100_000)
    session_id: uuid.UUID | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class PlaygroundRequestResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    session_id: uuid.UUID | None = None
    model: str
    provider: str | None = None
    system_prompt: str | None = None
    user_prompt: str
    parameters: dict[str, Any]
    response_text: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: Decimal | None = None
    latency_ms: int | None = None
    status: str
    route_decision: str | None = None
    error: str | None = None
    gateway_request_id: uuid.UUID | None = None
    created_at: datetime


class PlaygroundRequestListResponse(BaseModel):
    requests: list[PlaygroundRequestResponse]
    total: int


class PlaygroundCompareRequest(BaseModel):
    models: list[str] = Field(..., min_length=2, max_length=5)
    system_prompt: str | None = Field(None, max_length=100_000)
    user_prompt: str = Field(..., max_length=100_000)
    parameters: dict[str, Any] = Field(default_factory=dict)


class PlaygroundCompareResponse(BaseModel):
    results: list[PlaygroundRequestResponse]
