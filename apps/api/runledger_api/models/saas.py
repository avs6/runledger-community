"""SaaS Foundation ORM models: Subscription, UsageQuota."""

from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from runledger_api.core.db import Base

# Plan-level event quotas (events per month)
PLAN_QUOTAS: dict[str, int] = {
    "free": 10_000,
    "starter": 500_000,
    "growth": 5_000_000,
    "enterprise": 100_000_000,
}


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)
    plan: Mapped[str] = mapped_column(sa.String(32), nullable=False, default="free")
    status: Mapped[str] = mapped_column(sa.String(32), nullable=False, default="active")
    current_period_start: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    current_period_end: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.text("now()")
    )


class UsageQuota(Base):
    __tablename__ = "usage_quotas"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    events_limit: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=10_000)
    events_used: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    period_start: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.text("now()")
    )
