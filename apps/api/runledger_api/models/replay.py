"""ORM model for user anomaly detection.

The replay harness tables were merged into experiments (``mode="replay"``,
review B-07); see ``models/eval_experiments.py``.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from runledger_api.core.db import Base


class UserAnomaly(Base):
    """Nightly anomaly flag: a user whose daily spend exceeds 3σ above their 30d mean."""

    __tablename__ = "user_anomalies"
    __table_args__ = (sa.Index("ix_user_anomalies_workspace_date", "workspace_id", "detected_at"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    end_user_id: Mapped[str] = mapped_column(sa.Text, nullable=False)
    detected_at: Mapped[date] = mapped_column(sa.Date, nullable=False)
    daily_spend: Mapped[Decimal] = mapped_column(sa.Numeric(14, 8), nullable=False)
    mean_spend: Mapped[Decimal] = mapped_column(sa.Numeric(14, 8), nullable=False)
    zscore: Mapped[Decimal] = mapped_column(sa.Numeric(8, 4), nullable=False)
    reason: Mapped[str] = mapped_column(sa.Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
