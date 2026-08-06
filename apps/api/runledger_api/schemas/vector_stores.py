"""Pydantic schemas for vector store management."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field

CollectionStatus = Literal["active", "inactive", "deleted"]
DistanceMetric = Literal["cosine", "euclidean", "dot"]


class VectorCollectionCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: str | None = Field(None, max_length=2000)
    qdrant_collection: str = Field(..., max_length=200)
    embedding_model: str | None = Field(None, max_length=200)
    dimensions: int | None = Field(None, ge=1, le=10000)
    distance_metric: DistanceMetric = "cosine"
    config: dict[str, Any] = Field(default_factory=dict)


class VectorCollectionUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    description: str | None = Field(None, max_length=2000)
    embedding_model: str | None = Field(None, max_length=200)
    status: CollectionStatus | None = None
    config: dict[str, Any] | None = None


class VectorCollectionResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str | None = None
    qdrant_collection: str
    embedding_model: str | None = None
    dimensions: int | None = None
    distance_metric: str
    document_count: int
    size_bytes: int
    total_queries: int
    total_query_cost: Decimal
    total_embed_cost: Decimal
    status: str
    config: dict[str, Any]
    last_queried_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class VectorCollectionListResponse(BaseModel):
    collections: list[VectorCollectionResponse]
    total: int


class VectorCollectionStats(BaseModel):
    collection_id: uuid.UUID
    name: str
    document_count: int
    size_bytes: int
    total_queries: int
    total_query_cost: Decimal
    total_embed_cost: Decimal
    total_cost: Decimal
    avg_query_latency_ms: float | None = None
    avg_results_per_query: float | None = None


class VectorSearchTestRequest(BaseModel):
    query: str = Field(..., max_length=10000)
    top_k: int = Field(5, ge=1, le=100)
    threshold: Decimal | None = Field(None, ge=0, le=1)


class VectorSearchResult(BaseModel):
    score: Decimal
    payload: dict[str, Any]


class VectorSearchTestResponse(BaseModel):
    query: str
    results: list[VectorSearchResult]
    result_count: int
    latency_ms: int | None = None
    embed_cost: Decimal = Decimal("0")
    query_cost: Decimal = Decimal("0")


class VectorQueryResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    collection_id: uuid.UUID
    query_text: str
    top_k: int
    threshold: Decimal | None = None
    result_count: int
    best_score: Decimal | None = None
    latency_ms: int | None = None
    embed_cost: Decimal
    query_cost: Decimal
    results: list[dict[str, Any]] | None = None
    created_at: datetime


class VectorQueryListResponse(BaseModel):
    queries: list[VectorQueryResponse]
    total: int
