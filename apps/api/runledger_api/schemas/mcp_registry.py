"""Pydantic schemas for MCP server registry."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel


class McpServerCreate(BaseModel):
    name: str
    description: str | None = None
    transport: str = "http"
    url: str | None = None
    command: str | None = None
    args: list[str] = []
    env: dict[str, Any] = {}
    auth_type: str | None = None
    auth_config: dict[str, Any] = {}


class McpServerUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    transport: str | None = None
    url: str | None = None
    command: str | None = None
    args: list[str] | None = None
    env: dict[str, Any] | None = None
    auth_type: str | None = None
    auth_config: dict[str, Any] | None = None
    is_active: bool | None = None


class McpServerResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str | None
    transport: str
    url: str | None
    command: str | None
    args: list[str]
    env: dict[str, Any]
    auth_type: str | None
    discovered_tools: list[dict[str, Any]]
    discovered_resources: list[dict[str, Any]]
    discovered_prompts: list[dict[str, Any]]
    health_status: str
    last_health_check: datetime | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    tool_count: int = 0
    resource_count: int = 0
    prompt_count: int = 0


class McpServerList(BaseModel):
    items: list[McpServerResponse]


class McpPermissionCreate(BaseModel):
    mcp_server_id: uuid.UUID
    scope_type: str
    scope_id: uuid.UUID
    allowed_tools: list[str] | None = None


class McpPermissionResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    mcp_server_id: uuid.UUID
    scope_type: str
    scope_id: uuid.UUID
    allowed_tools: list[str] | None
    created_at: datetime


class McpPermissionList(BaseModel):
    items: list[McpPermissionResponse]


class McpToolCallRequest(BaseModel):
    server_id: uuid.UUID
    tool_name: str
    arguments: dict[str, Any] = {}


class McpToolCallResponse(BaseModel):
    id: uuid.UUID
    mcp_server_id: uuid.UUID
    tool_name: str
    arguments: dict[str, Any]
    result: dict[str, Any] | None
    cost_usd: Decimal | None
    latency_ms: int | None
    status: str
    error: str | None
    created_at: datetime


class McpToolCallList(BaseModel):
    items: list[McpToolCallResponse]


class McpToolListItem(BaseModel):
    server_id: uuid.UUID
    server_name: str
    tool_name: str
    description: str | None = None


class McpToolListResponse(BaseModel):
    items: list[McpToolListItem]
