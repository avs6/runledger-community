"""
ORM model for budget tiers — named spend/rate profiles assigned to API keys.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from runledger_api.core.db import Base


class BudgetTier(Base):
    __tablename__ = "budget_tiers"
    __table_args__ = (
        sa.UniqueConstraint("workspace_id", "name", name="uq_budget_tiers_ws_name"),
        sa.Index("ix_budget_tiers_workspace", "workspace_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    max_spend_usd: Mapped[Decimal | None] = mapped_column(sa.Numeric(14, 6), nullable=True)
    period_type: Mapped[str] = mapped_column(
        sa.String(16), nullable=False, server_default=sa.text("'monthly'")
    )
    rpm_limit: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    tpm_limit: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    allowed_models: Mapped[list[str] | None] = mapped_column(ARRAY(sa.Text), nullable=True)
    is_default: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
