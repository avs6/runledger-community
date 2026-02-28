"""
ORM models for Phase 11: ledger_keys, ledger_snapshots, tool_registry,
security_events, capture_policies.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from runledger_api.core.db import Base


class LedgerKey(Base):
    __tablename__ = "ledger_keys"
    __table_args__ = (
        sa.Index("ix_ledger_keys_workspace", "workspace_id", "active", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    key_value: Mapped[str] = mapped_column(sa.Text, nullable=False)
    active: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("TRUE")
    )
    expires_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class LedgerSnapshot(Base):
    __tablename__ = "ledger_snapshots"
    __table_args__ = (
        sa.Index(
            "ix_ledger_snapshots_workspace_date",
            "workspace_id",
            "snapshot_date",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(sa.Date, nullable=False)
    total_cost_usd: Mapped[Decimal] = mapped_column(sa.Numeric(14, 8), nullable=False)
    model_breakdown: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'{}'")
    )
    call_count: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default=sa.text("0")
    )
    hash: Mapped[str] = mapped_column(sa.Text, nullable=False)
    key_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class ToolRegistry(Base):
    __tablename__ = "tool_registry"
    __table_args__ = (
        sa.Index(
            "ix_tool_registry_workspace_name",
            "workspace_id",
            "tool_name",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    tool_name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    policy: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default=sa.text("'audit'")
    )
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class SecurityEvent(Base):
    __tablename__ = "security_events"
    __table_args__ = (
        sa.Index(
            "ix_security_events_workspace_detected",
            "workspace_id",
            "detected_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(sa.Text, nullable=False)
    tool_name: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    end_user_id: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    run_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'{}'")
    )
    detected_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class CapturePolicy(Base):
    __tablename__ = "capture_policies"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, unique=True
    )
    privacy_mode: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default=sa.text("'METADATA_ONLY'")
    )
    sampled_rate: Mapped[Decimal | None] = mapped_column(sa.Numeric(5, 4), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
