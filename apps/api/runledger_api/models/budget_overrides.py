"""
ORM model for temporary budget overrides (time-boxed increases).
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from runledger_api.core.db import Base


class OverrideStatusEnum(enum.StrEnum):
    pending = "pending"
    active = "active"
    expired = "expired"
    revoked = "revoked"


class BudgetOverride(Base):
    __tablename__ = "budget_overrides"
    __table_args__ = (sa.Index("ix_budget_overrides_budget", "budget_id", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    budget_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    original_limit_usd: Mapped[Decimal] = mapped_column(sa.Numeric(14, 6), nullable=False)
    override_limit_usd: Mapped[Decimal] = mapped_column(sa.Numeric(14, 6), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(
        sa.String(16), nullable=False, server_default=sa.text("'active'")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
