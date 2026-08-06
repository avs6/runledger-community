from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from runledger_api.core.db import Base


class SearchTool(Base):
    __tablename__ = "search_tools"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_type: Mapped[str] = mapped_column(String(50), nullable=False)
    endpoint_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    auth_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    auth_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    rate_limit_rpm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_per_query: Mapped[Decimal] = mapped_column(Numeric(12, 6), server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true")
    total_queries: Mapped[int] = mapped_column(Integer, server_default="0")
    total_cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), server_default="0")
    avg_quality_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 3), nullable=True)
    config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
