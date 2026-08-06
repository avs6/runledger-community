"""
ORM model for per-model budget limits on API keys.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from runledger_api.core.db import Base


class ModelBudget(Base):
    __tablename__ = "model_budgets"
    __table_args__ = (sa.Index("ix_model_budgets_key", "api_key_id", "is_active"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    api_key_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    model_pattern: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    max_spend_usd: Mapped[Decimal | None] = mapped_column(sa.Numeric(14, 6), nullable=True)
    period_type: Mapped[str] = mapped_column(
        sa.String(16), nullable=False, server_default=sa.text("'monthly'")
    )
    rpm_limit: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    tpm_limit: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    action: Mapped[str] = mapped_column(
        sa.String(16), nullable=False, server_default=sa.text("'block'")
    )
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
