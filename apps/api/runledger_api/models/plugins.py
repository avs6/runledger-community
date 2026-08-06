"""ORM models for the custom plugin system."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from runledger_api.core.db import Base


class Plugin(Base):
    __tablename__ = "plugins"
    __table_args__ = (sa.Index("ix_plugins_workspace", "workspace_id"),)

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    plugin_type: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    hooks: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default=sa.text("'[]'"))
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=sa.text("'{}'"))
    priority: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("100"))
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text("true"))
    version: Mapped[str | None] = mapped_column(sa.String(32), nullable=True)
    author: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)
    install_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("0"))
    created_at: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False)


class PluginExecution(Base):
    __tablename__ = "plugin_executions"
    __table_args__ = (
        sa.Index("ix_plugin_exec_workspace", "workspace_id"),
        sa.Index("ix_plugin_exec_plugin", "plugin_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    plugin_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    hook: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    status: Mapped[str] = mapped_column(sa.String(16), nullable=False, server_default=sa.text("'success'"))
    error: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False)
