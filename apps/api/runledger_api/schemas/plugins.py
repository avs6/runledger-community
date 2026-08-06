"""Pydantic schemas for the custom plugin system."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class PluginCreate(BaseModel):
    name: str
    description: str | None = None
    plugin_type: str
    hooks: list[str] = []
    config: dict[str, Any] = {}
    priority: int = 100
    version: str | None = None
    author: str | None = None


class PluginUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    hooks: list[str] | None = None
    config: dict[str, Any] | None = None
    priority: int | None = None
    is_active: bool | None = None


class PluginResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str | None
    plugin_type: str
    hooks: list[str]
    config: dict[str, Any]
    priority: int
    is_active: bool
    version: str | None
    author: str | None
    install_count: int
    created_at: datetime
    updated_at: datetime


class PluginList(BaseModel):
    items: list[PluginResponse]


class PluginExecutionResponse(BaseModel):
    id: uuid.UUID
    plugin_id: uuid.UUID
    hook: str
    latency_ms: int | None
    status: str
    error: str | None
    created_at: datetime


class PluginExecutionList(BaseModel):
    items: list[PluginExecutionResponse]
