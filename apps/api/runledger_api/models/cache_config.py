from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from runledger_api.core.db import Base


class ResponseCacheConfig(Base):
    __tablename__ = "response_cache_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, server_default="true")
    ttl_seconds: Mapped[int] = mapped_column(Integer, server_default="3600")
    max_entries: Mapped[int] = mapped_column(Integer, server_default="10000")
    eviction_policy: Mapped[str] = mapped_column(String(20), server_default="'lru'")
    similarity_threshold: Mapped[Decimal] = mapped_column(Numeric(5, 4), server_default="0.95")
    embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    scope_models: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    total_hits: Mapped[int] = mapped_column(Integer, server_default="0")
    total_misses: Mapped[int] = mapped_column(Integer, server_default="0")
    total_savings_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), server_default="0")
    config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
