"""
Vector Store Management API.

Prefix: /vector-stores
Auth: Bearer API key (workspace-scoped)

Endpoints
---------
POST   /vector-stores                           Register a collection
GET    /vector-stores                           List collections
GET    /vector-stores/{id}                      Get collection detail
PUT    /vector-stores/{id}                      Update collection
DELETE /vector-stores/{id}                      Delete (soft) collection
GET    /vector-stores/{id}/stats                Collection cost/usage stats
GET    /vector-stores/{id}/queries              Recent queries
POST   /vector-stores/{id}/search-test          Test a search query
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace
from runledger_api.core.ratelimit import analytics_rate_limit, management_rate_limit
from runledger_api.models.tenant import Workspace
from runledger_api.models.vector_stores import VectorStoreCollection, VectorStoreQuery
from runledger_api.schemas.vector_stores import (
    VectorCollectionCreate,
    VectorCollectionListResponse,
    VectorCollectionResponse,
    VectorCollectionStats,
    VectorCollectionUpdate,
    VectorQueryListResponse,
    VectorQueryResponse,
    VectorSearchTestRequest,
    VectorSearchTestResponse,
)

log = structlog.get_logger()
router = APIRouter(prefix="/vector-stores", tags=["vector-stores"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]


def _collection_to_response(c: VectorStoreCollection) -> VectorCollectionResponse:
    return VectorCollectionResponse(
        id=c.id,
        workspace_id=c.workspace_id,
        name=c.name,
        description=c.description,
        qdrant_collection=c.qdrant_collection,
        embedding_model=c.embedding_model,
        dimensions=c.dimensions,
        distance_metric=c.distance_metric,
        document_count=c.document_count,
        size_bytes=c.size_bytes,
        total_queries=c.total_queries,
        total_query_cost=c.total_query_cost,
        total_embed_cost=c.total_embed_cost,
        status=c.status,
        config=c.config or {},
        last_queried_at=c.last_queried_at,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


def _query_to_response(q: VectorStoreQuery) -> VectorQueryResponse:
    return VectorQueryResponse(
        id=q.id,
        workspace_id=q.workspace_id,
        collection_id=q.collection_id,
        query_text=q.query_text,
        top_k=q.top_k,
        threshold=q.threshold,
        result_count=q.result_count,
        best_score=q.best_score,
        latency_ms=q.latency_ms,
        embed_cost=q.embed_cost,
        query_cost=q.query_cost,
        results=q.results,
        created_at=q.created_at,
    )


# ── CRUD ────────────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=VectorCollectionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(management_rate_limit)],
)
async def create_collection(
    body: VectorCollectionCreate, ws: WorkspaceDep, db: DbDep
) -> VectorCollectionResponse:
    coll = VectorStoreCollection(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        name=body.name,
        description=body.description,
        qdrant_collection=body.qdrant_collection,
        embedding_model=body.embedding_model,
        dimensions=body.dimensions,
        distance_metric=body.distance_metric,
        config=body.config,
    )
    db.add(coll)
    await db.commit()
    await db.refresh(coll)
    return _collection_to_response(coll)


@router.get(
    "",
    response_model=VectorCollectionListResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def list_collections(
    ws: WorkspaceDep,
    db: DbDep,
    collection_status: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> VectorCollectionListResponse:
    q = select(VectorStoreCollection).where(VectorStoreCollection.workspace_id == ws.id)
    count_q = select(func.count(VectorStoreCollection.id)).where(
        VectorStoreCollection.workspace_id == ws.id
    )
    if collection_status:
        q = q.where(VectorStoreCollection.status == collection_status)
        count_q = count_q.where(VectorStoreCollection.status == collection_status)

    total = (await db.execute(count_q)).scalar() or 0
    rows = (
        (
            await db.execute(
                q.order_by(VectorStoreCollection.created_at.desc()).offset(offset).limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return VectorCollectionListResponse(
        collections=[_collection_to_response(c) for c in rows],
        total=total,
    )


@router.get(
    "/{collection_id}",
    response_model=VectorCollectionResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def get_collection(
    collection_id: uuid.UUID, ws: WorkspaceDep, db: DbDep
) -> VectorCollectionResponse:
    result = await db.execute(
        select(VectorStoreCollection).where(
            VectorStoreCollection.id == collection_id,
            VectorStoreCollection.workspace_id == ws.id,
        )
    )
    coll = result.scalar_one_or_none()
    if not coll:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Collection not found")
    return _collection_to_response(coll)


@router.put(
    "/{collection_id}",
    response_model=VectorCollectionResponse,
    dependencies=[Depends(management_rate_limit)],
)
async def update_collection(
    collection_id: uuid.UUID,
    body: VectorCollectionUpdate,
    ws: WorkspaceDep,
    db: DbDep,
) -> VectorCollectionResponse:
    result = await db.execute(
        select(VectorStoreCollection).where(
            VectorStoreCollection.id == collection_id,
            VectorStoreCollection.workspace_id == ws.id,
        )
    )
    coll = result.scalar_one_or_none()
    if not coll:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Collection not found")

    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(coll, field, val)
    coll.updated_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(coll)
    return _collection_to_response(coll)


@router.delete(
    "/{collection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(management_rate_limit)],
)
async def delete_collection(collection_id: uuid.UUID, ws: WorkspaceDep, db: DbDep) -> None:
    result = await db.execute(
        select(VectorStoreCollection).where(
            VectorStoreCollection.id == collection_id,
            VectorStoreCollection.workspace_id == ws.id,
        )
    )
    coll = result.scalar_one_or_none()
    if not coll:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Collection not found")
    coll.status = "deleted"
    coll.updated_at = datetime.now(UTC)
    await db.commit()


# ── Stats ──────────────────────────────────────────────────────────────────


@router.get(
    "/{collection_id}/stats",
    response_model=VectorCollectionStats,
    dependencies=[Depends(analytics_rate_limit)],
)
async def collection_stats(
    collection_id: uuid.UUID, ws: WorkspaceDep, db: DbDep
) -> VectorCollectionStats:
    result = await db.execute(
        select(VectorStoreCollection).where(
            VectorStoreCollection.id == collection_id,
            VectorStoreCollection.workspace_id == ws.id,
        )
    )
    coll = result.scalar_one_or_none()
    if not coll:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Collection not found")

    agg = (
        await db.execute(
            select(
                func.avg(VectorStoreQuery.latency_ms).label("avg_latency"),
                func.avg(VectorStoreQuery.result_count).label("avg_results"),
            ).where(VectorStoreQuery.collection_id == collection_id)
        )
    ).one()

    return VectorCollectionStats(
        collection_id=coll.id,
        name=coll.name,
        document_count=coll.document_count,
        size_bytes=coll.size_bytes,
        total_queries=coll.total_queries,
        total_query_cost=coll.total_query_cost,
        total_embed_cost=coll.total_embed_cost,
        total_cost=coll.total_query_cost + coll.total_embed_cost,
        avg_query_latency_ms=float(agg.avg_latency) if agg.avg_latency else None,
        avg_results_per_query=float(agg.avg_results) if agg.avg_results else None,
    )


# ── Queries ────────────────────────────────────────────────────────────────


@router.get(
    "/{collection_id}/queries",
    response_model=VectorQueryListResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def list_queries(
    collection_id: uuid.UUID,
    ws: WorkspaceDep,
    db: DbDep,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> VectorQueryListResponse:
    count_q = select(func.count(VectorStoreQuery.id)).where(
        VectorStoreQuery.collection_id == collection_id,
        VectorStoreQuery.workspace_id == ws.id,
    )
    total = (await db.execute(count_q)).scalar() or 0

    rows = (
        (
            await db.execute(
                select(VectorStoreQuery)
                .where(
                    VectorStoreQuery.collection_id == collection_id,
                    VectorStoreQuery.workspace_id == ws.id,
                )
                .order_by(VectorStoreQuery.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return VectorQueryListResponse(
        queries=[_query_to_response(q) for q in rows],
        total=total,
    )


# ── Search Test ────────────────────────────────────────────────────────────


@router.post(
    "/{collection_id}/search-test",
    response_model=VectorSearchTestResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def search_test(
    collection_id: uuid.UUID,
    body: VectorSearchTestRequest,
    ws: WorkspaceDep,
    db: DbDep,
) -> VectorSearchTestResponse:
    result = await db.execute(
        select(VectorStoreCollection).where(
            VectorStoreCollection.id == collection_id,
            VectorStoreCollection.workspace_id == ws.id,
        )
    )
    coll = result.scalar_one_or_none()
    if not coll:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Collection not found")

    query_record = VectorStoreQuery(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        collection_id=collection_id,
        query_text=body.query,
        top_k=body.top_k,
        threshold=body.threshold,
        result_count=0,
        latency_ms=0,
    )
    db.add(query_record)

    coll.total_queries += 1
    coll.last_queried_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(query_record)

    return VectorSearchTestResponse(
        query=body.query,
        results=[],
        result_count=0,
        latency_ms=0,
        embed_cost=Decimal("0"),
        query_cost=Decimal("0"),
    )
