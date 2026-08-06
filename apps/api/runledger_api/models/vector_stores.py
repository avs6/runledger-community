"""ORM models for vector store management."""

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


class VectorStoreCollection(Base):
    __tablename__ = "vector_store_collections"
    __table_args__ = (sa.Index("ix_vector_collections_workspace", "workspace_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    qdrant_collection: Mapped[str] = mapped_column(sa.Text, nullable=False)
    embedding_model: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    dimensions: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    distance_metric: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default=sa.text("'cosine'")
    )
    document_count: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default=sa.text("0")
    )
    size_bytes: Mapped[int] = mapped_column(
        sa.BigInteger, nullable=False, server_default=sa.text("0")
    )
    total_queries: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default=sa.text("0")
    )
    total_query_cost: Mapped[Decimal] = mapped_column(
        sa.Numeric(precision=12, scale=6), server_default=sa.text("0")
    )
    total_embed_cost: Mapped[Decimal] = mapped_column(
        sa.Numeric(precision=12, scale=6), server_default=sa.text("0")
    )
    status: Mapped[str] = mapped_column(sa.Text, nullable=False, server_default=sa.text("'active'"))
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'{}'")
    )
    last_queried_at: Mapped[datetime | None] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class VectorStoreQuery(Base):
    __tablename__ = "vector_store_queries"
    __table_args__ = (
        sa.Index("ix_vector_queries_workspace", "workspace_id"),
        sa.Index("ix_vector_queries_collection", "collection_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    collection_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    query_text: Mapped[str] = mapped_column(sa.Text, nullable=False)
    top_k: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("5"))
    threshold: Mapped[Decimal | None] = mapped_column(
        sa.Numeric(precision=5, scale=4), nullable=True
    )
    result_count: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default=sa.text("0")
    )
    best_score: Mapped[Decimal | None] = mapped_column(
        sa.Numeric(precision=5, scale=4), nullable=True
    )
    latency_ms: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    embed_cost: Mapped[Decimal] = mapped_column(
        sa.Numeric(precision=12, scale=6), server_default=sa.text("0")
    )
    query_cost: Mapped[Decimal] = mapped_column(
        sa.Numeric(precision=12, scale=6), server_default=sa.text("0")
    )
    results: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
