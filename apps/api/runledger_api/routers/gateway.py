"""
Model Gateway API.

Prefix: /gateway
Auth: Bearer API key (workspace-scoped)

Endpoints
---------
POST   /gateway/chat/completions   OpenAI-compatible proxy endpoint
POST   /gateway/routes             Create a route
GET    /gateway/routes             List routes
PUT    /gateway/routes/{id}        Update / disable route
DELETE /gateway/routes/{id}        Delete route
GET    /gateway/stats              Request statistics
"""

from __future__ import annotations

import time
import uuid
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace
from runledger_api.core.ratelimit import management_rate_limit
from runledger_api.models.gateway import GatewayRequest, GatewayRoute, PromptCache
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.gateway import (
    GatewayCompletionRequest,
    GatewayRouteCreate,
    GatewayRouteList,
    GatewayRouteResponse,
    GatewayRouteStats,
    GatewayRouteUpdate,
    GatewayStats,
)
from runledger_api.services.gateway import (
    check_cache,
    increment_hit_count,
    record_gateway_request,
    route_and_forward,
    store_cache,
)

router = APIRouter(
    prefix="/gateway",
    tags=["gateway"],
    dependencies=[Depends(management_rate_limit)],
)

DbDep = Annotated[AsyncSession, Depends(get_db)]
WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]

# ── Chat completions ────────────────────────────────────────────────────────────


@router.post("/chat/completions")
async def gateway_chat_completions(
    body: GatewayCompletionRequest,
    workspace: WorkspaceDep,
    db: DbDep,
) -> dict[str, Any]:
    """
    OpenAI-compatible chat completions proxy.

    Flow:
      1. Check prompt cache (if body.cache=True)
      2. If cache hit: record + return cached response
      3. Else: forward to provider via configured routes (with fallback)
      4. Store result in cache + record GatewayRequest
    """
    from runledger_api.services.gateway import make_cache_key

    messages = [{"role": m.role, "content": m.content} for m in body.messages]

    # ── 1. Cache lookup ──────────────────────────────────────────────────────
    cache_entry = None
    if body.cache:
        # We need the target_model for the cache key; use alias for now,
        # actual target resolved when forwarding. Use alias as surrogate.
        cache_key = make_cache_key(body.model, messages)
        cache_entry = await check_cache(db, workspace.id, cache_key)

    if cache_entry is not None:
        await increment_hit_count(db, cache_entry)
        await record_gateway_request(
            db=db,
            workspace_id=workspace.id,
            model_requested=body.model,
            route=None,
            model_used=cache_entry.model,
            cache_hit=True,
            input_tokens=cache_entry.prompt_tokens,
            output_tokens=cache_entry.completion_tokens,
            latency_ms=0,
            req_status="cache_hit",
        )
        return cache_entry.response_json

    # ── 2. Forward to provider ────────────────────────────────────────────────
    t0 = time.monotonic()
    try:
        response_json, winning_route, latency_ms = await route_and_forward(
            db=db,
            workspace_id=workspace.id,
            model_alias=body.model,
            messages=messages,
            temperature=body.temperature,
            max_tokens=body.max_tokens,
        )
    except HTTPException:
        # Record the failed attempt before re-raising
        await record_gateway_request(
            db=db,
            workspace_id=workspace.id,
            model_requested=body.model,
            route=None,
            model_used=None,
            cache_hit=False,
            input_tokens=None,
            output_tokens=None,
            latency_ms=int((time.monotonic() - t0) * 1000),
            req_status="error",
        )
        raise

    # ── 3. Extract token usage ───────────────────────────────────────────────
    usage = response_json.get("usage") or {}
    input_tokens = usage.get("prompt_tokens")
    output_tokens = usage.get("completion_tokens")

    # ── 4. Store in cache ────────────────────────────────────────────────────
    if body.cache:
        cache_key = make_cache_key(body.model, messages)
        await store_cache(
            db=db,
            workspace_id=workspace.id,
            cache_key=cache_key,
            model=winning_route.target_model,
            response_json=response_json,
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
        )

    # ── 5. Record request log ────────────────────────────────────────────────
    await record_gateway_request(
        db=db,
        workspace_id=workspace.id,
        model_requested=body.model,
        route=winning_route,
        model_used=winning_route.target_model,
        cache_hit=False,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
        req_status="success",
    )

    return response_json


# ── Routes CRUD ────────────────────────────────────────────────────────────────


@router.post("/routes", response_model=GatewayRouteResponse, status_code=status.HTTP_201_CREATED)
async def create_gateway_route(
    body: GatewayRouteCreate,
    workspace: WorkspaceDep,
    db: DbDep,
) -> GatewayRouteResponse:
    route = GatewayRoute(
        workspace_id=workspace.id,
        alias=body.alias,
        provider=body.provider,
        target_model=body.target_model,
        base_url=body.base_url,
        api_key_env_var=body.api_key_env_var,
        priority=body.priority,
    )
    db.add(route)
    await db.flush()
    await db.commit()
    await db.refresh(route)
    return GatewayRouteResponse.model_validate(route)


@router.get("/routes", response_model=GatewayRouteList)
async def list_gateway_routes(
    workspace: WorkspaceDep,
    db: DbDep,
    include_inactive: bool = Query(False),
) -> GatewayRouteList:
    stmt = select(GatewayRoute).where(GatewayRoute.workspace_id == workspace.id)
    if not include_inactive:
        stmt = stmt.where(GatewayRoute.is_active.is_(True))
    stmt = stmt.order_by(GatewayRoute.priority.asc(), GatewayRoute.created_at.asc())
    result = await db.execute(stmt)
    routes = list(result.scalars().all())
    return GatewayRouteList(items=[GatewayRouteResponse.model_validate(r) for r in routes])


@router.put("/routes/{route_id}", response_model=GatewayRouteResponse)
async def update_gateway_route(
    route_id: uuid.UUID,
    body: GatewayRouteUpdate,
    workspace: WorkspaceDep,
    db: DbDep,
) -> GatewayRouteResponse:
    route = await db.get(GatewayRoute, route_id)
    if route is None or route.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gateway route not found")

    if body.alias is not None:
        route.alias = body.alias
    if body.target_model is not None:
        route.target_model = body.target_model
    if body.priority is not None:
        route.priority = body.priority
    if body.is_active is not None:
        route.is_active = body.is_active
    if "base_url" in body.model_fields_set:
        route.base_url = body.base_url
    if "api_key_env_var" in body.model_fields_set:
        route.api_key_env_var = body.api_key_env_var

    await db.commit()
    await db.refresh(route)
    return GatewayRouteResponse.model_validate(route)


@router.delete("/routes/{route_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_gateway_route(
    route_id: uuid.UUID,
    workspace: WorkspaceDep,
    db: DbDep,
) -> None:
    route = await db.get(GatewayRoute, route_id)
    if route is None or route.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gateway route not found")
    await db.delete(route)
    await db.commit()


# ── Stats ──────────────────────────────────────────────────────────────────────


@router.get("/stats", response_model=GatewayStats)
async def gateway_stats(
    workspace: WorkspaceDep,
    db: DbDep,
) -> GatewayStats:
    """Aggregate gateway request stats per route for the workspace."""
    stmt = (
        select(
            GatewayRequest.route_id,
            func.count(GatewayRequest.id).label("total"),
            func.count(GatewayRequest.id).filter(GatewayRequest.cache_hit.is_(True)).label("cache_hits"),
            func.avg(GatewayRequest.latency_ms).label("avg_latency"),
            func.count(GatewayRequest.id).filter(GatewayRequest.status == "error").label("errors"),
        )
        .where(GatewayRequest.workspace_id == workspace.id)
        .group_by(GatewayRequest.route_id)
    )
    result = await db.execute(stmt)
    rows = result.all()

    # Load route aliases for joining
    route_ids = [r.route_id for r in rows if r.route_id]
    alias_map: dict[uuid.UUID, str] = {}
    if route_ids:
        route_stmt = select(GatewayRoute.id, GatewayRoute.alias).where(
            GatewayRoute.id.in_(route_ids)
        )
        route_result = await db.execute(route_stmt)
        alias_map = {row.id: row.alias for row in route_result.all()}

    route_stats: list[GatewayRouteStats] = []
    total_requests = 0
    total_cache_hits = 0
    latencies: list[Decimal] = []

    for row in rows:
        total = int(row.total)
        cache_hits = int(row.cache_hits)
        errors = int(row.errors)
        avg_lat = Decimal(str(row.avg_latency)).quantize(Decimal("0.01")) if row.avg_latency else None
        alias = alias_map.get(row.route_id, "unknown") if row.route_id else "cache_only"
        hit_rate = Decimal(str(round(cache_hits / total, 4))) if total else Decimal("0")

        route_stats.append(
            GatewayRouteStats(
                route_id=row.route_id,
                alias=alias,
                total_requests=total,
                cache_hits=cache_hits,
                cache_hit_rate=hit_rate,
                avg_latency_ms=avg_lat,
                error_count=errors,
            )
        )
        total_requests += total
        total_cache_hits += cache_hits
        if avg_lat is not None:
            latencies.append(avg_lat)

    overall_hit_rate = (
        Decimal(str(round(total_cache_hits / total_requests, 4))) if total_requests else Decimal("0")
    )
    overall_latency = (
        Decimal(str(round(sum(latencies) / len(latencies), 2))) if latencies else None
    )

    return GatewayStats(
        total_requests=total_requests,
        cache_hits=total_cache_hits,
        cache_hit_rate=overall_hit_rate,
        avg_latency_ms=overall_latency,
        routes=route_stats,
    )
