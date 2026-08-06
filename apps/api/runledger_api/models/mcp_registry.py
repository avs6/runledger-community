"""ORM models for MCP server registry, permissions, and tool call tracking."""

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


class McpServer(Base):
    __tablename__ = "mcp_servers"
    __table_args__ = (sa.Index("ix_mcp_servers_workspace", "workspace_id"),)

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    transport: Mapped[str] = mapped_column(sa.String(16), nullable=False, server_default=sa.text("'http'"))
    url: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    command: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    args: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default=sa.text("'[]'"))
    env: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=sa.text("'{}'"))
    auth_type: Mapped[str | None] = mapped_column(sa.String(32), nullable=True)
    auth_config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=sa.text("'{}'"))
    discovered_tools: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, server_default=sa.text("'[]'"))
    discovered_resources: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, server_default=sa.text("'[]'"))
    discovered_prompts: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, server_default=sa.text("'[]'"))
    health_status: Mapped[str] = mapped_column(sa.String(16), nullable=False, server_default=sa.text("'unknown'"))
    last_health_check: Mapped[datetime | None] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text("true"))
    created_at: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False)


class McpPermission(Base):
    __tablename__ = "mcp_permissions"
    __table_args__ = (
        sa.Index("ix_mcp_perms_workspace", "workspace_id"),
        sa.Index("ix_mcp_perms_server", "mcp_server_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    mcp_server_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    scope_type: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    scope_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    allowed_tools: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False)


class McpToolCall(Base):
    __tablename__ = "mcp_tool_calls"
    __table_args__ = (
        sa.Index("ix_mcp_calls_workspace", "workspace_id"),
        sa.Index("ix_mcp_calls_server", "mcp_server_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    mcp_server_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    tool_name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    arguments: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=sa.text("'{}'"))
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    cost_usd: Mapped[Decimal | None] = mapped_column(sa.Numeric(12, 6), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    status: Mapped[str] = mapped_column(sa.String(16), nullable=False, server_default=sa.text("'success'"))
    error: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False)
