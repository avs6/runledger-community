"""
Model Gateway API.

Prefix: /gateway
Auth: Bearer API key (workspace-scoped)

Endpoints
---------
POST   /gateway/chat/completions          OpenAI-compatible proxy (non-streaming + SSE streaming)
POST   /gateway/routes                    Create a route
GET    /gateway/routes                    List routes
PUT    /gateway/routes/{id}               Update / disable route
DELETE /gateway/routes/{id}               Delete route
GET    /gateway/stats                     Request statistics
GET    /gateway/requests                  Routing log with decision_reason
POST   /gateway/policies                  Create a routing policy
GET    /gateway/policies                  List routing policies
PUT    /gateway/policies/{id}             Update a routing policy
DELETE /gateway/policies/{id}             Delete a routing policy
"""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace
from runledger_api.core.ratelimit import management_rate_limit
from runledger_api.models.gateway import GatewayRequest, GatewayRoute, RoutingPolicy
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.gateway import (
    GatewayCompletionRequest,
    GatewayRequestList,
    GatewayRequestResponse,
    GatewayRouteCreate,
    GatewayRouteList,
    GatewayRouteResponse,
    GatewayRouteStats,
    GatewayRouteUpdate,
    GatewayStats,
    RoutingPolicyCreate,
    RoutingPolicyList,
    RoutingPolicyResponse,
    RoutingPolicyUpdate,
    RoutingRecommendationModel,
    RoutingRecommendationResponse,
)
from runledger_api.core.feature_gate import require_cloud
from runledger_api.services.gateway import (
    check_cache,
    increment_hit_count,
    make_cache_key,
    record_gateway_request,
    route_and_forward,
    store_cache,
    stream_request,
)
from runledger_api.services.gateway_controls import check_cost_cap, check_per_user_rpm
from runledger_api.services.gateway_redact import redact_messages

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
    x_runledger_end_user_id: str | None = Header(default=None, alias="X-RunLedger-End-User-Id"),
) -> Any:
    """
    OpenAI-compatible chat completions proxy.

    Flow:
      1. Check prompt cache (if body.cache=True)
      2. If cache hit: record + return cached response
      3. Apply routing policy to select target route
      4. Check runtime controls: cost cap + per-user rate limit
      5. Apply PII redaction (if enabled on route)
      6. Forward to provider (with retry + fallback)
      7. Store result in cache + record GatewayRequest with decision_reason
      8. If body.stream=True: return SSE StreamingResponse
    """
    messages = [{"role": m.role, "content": m.content} for m in body.messages]

    # ── 1. Cache lookup ──────────────────────────────────────────────────────
    cache_entry = None
    if body.cache and not body.stream:
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
            decision_reason="cache_hit",
        )
        return cache_entry.response_json

    # ── 2. Streaming path ────────────────────────────────────────────────────
    if body.stream:
        from runledger_api.services.routing import select_route_with_policy

        try:
            route, decision_reason = await select_route_with_policy(
                db,
                workspace.id,
                body.model,
                messages,
            )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"No active gateway routes for alias '{body.model}'",
            ) from None

        # Runtime controls
        await check_cost_cap(db, route, workspace.id)
        if x_runledger_end_user_id and route.per_user_rpm_limit:
            from runledger_api.core.redis import get_redis  # noqa: PLC0415

            redis = await get_redis()
            await check_per_user_rpm(
                redis, workspace.id, x_runledger_end_user_id, route.id, route.per_user_rpm_limit
            )

        fwd_messages = redact_messages(messages) if route.pii_redaction_enabled else messages

        async def _sse_gen() -> AsyncGenerator[bytes]:
            async for chunk in stream_request(
                route=route,
                messages=fwd_messages,
                temperature=body.temperature,
                max_tokens=body.max_tokens,
                top_p=body.top_p,
                frequency_penalty=body.frequency_penalty,
                presence_penalty=body.presence_penalty,
                seed=body.seed,
                stop=body.stop,
                response_format=body.response_format,
                tools=body.tools,
                tool_choice=body.tool_choice,
            ):
                yield chunk

        # Record the streaming request (no token counts available until stream ends)
        await record_gateway_request(
            db=db,
            workspace_id=workspace.id,
            model_requested=body.model,
            route=route,
            model_used=route.target_model,
            cache_hit=False,
            input_tokens=None,
            output_tokens=None,
            latency_ms=None,
            req_status="success",
            decision_reason=decision_reason,
        )
        return StreamingResponse(
            _sse_gen(),
            media_type="text/event-stream",
            headers={"X-Decision-Reason": decision_reason},
        )

    # ── 3. Non-streaming forward ─────────────────────────────────────────────
    t0 = time.monotonic()
    try:
        response_json, winning_route, latency_ms, decision_reason = await route_and_forward(
            db=db,
            workspace_id=workspace.id,
            model_alias=body.model,
            messages=messages,
            temperature=body.temperature,
            max_tokens=body.max_tokens,
            top_p=body.top_p,
            frequency_penalty=body.frequency_penalty,
            presence_penalty=body.presence_penalty,
            seed=body.seed,
            stop=body.stop,
            response_format=body.response_format,
            tools=body.tools,
            tool_choice=body.tool_choice,
        )
    except HTTPException:
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
            decision_reason=None,
        )
        raise

    # Runtime controls on the winning route
    await check_cost_cap(db, winning_route, workspace.id)
    if x_runledger_end_user_id and winning_route.per_user_rpm_limit:
        from runledger_api.core.redis import get_redis  # noqa: PLC0415

        redis = await get_redis()
        await check_per_user_rpm(
            redis,
            workspace.id,
            x_runledger_end_user_id,
            winning_route.id,
            winning_route.per_user_rpm_limit,
        )

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
        decision_reason=decision_reason,
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
        config=body.config,
        daily_cost_limit_usd=body.daily_cost_limit_usd,
        monthly_cost_limit_usd=body.monthly_cost_limit_usd,
        pii_redaction_enabled=body.pii_redaction_enabled,
        per_user_rpm_limit=body.per_user_rpm_limit,
        health_auto_disable=body.health_auto_disable,
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
    if body.config is not None:
        route.config = body.config
    if "daily_cost_limit_usd" in body.model_fields_set:
        route.daily_cost_limit_usd = body.daily_cost_limit_usd
    if "monthly_cost_limit_usd" in body.model_fields_set:
        route.monthly_cost_limit_usd = body.monthly_cost_limit_usd
    if body.pii_redaction_enabled is not None:
        route.pii_redaction_enabled = body.pii_redaction_enabled
    if "per_user_rpm_limit" in body.model_fields_set:
        route.per_user_rpm_limit = body.per_user_rpm_limit
    if body.health_auto_disable is not None:
        route.health_auto_disable = body.health_auto_disable

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


# ── Routing policies CRUD ──────────────────────────────────────────────────────


@router.post(
    "/policies",
    response_model=RoutingPolicyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_routing_policy(
    body: RoutingPolicyCreate,
    workspace: WorkspaceDep,
    db: DbDep,
) -> RoutingPolicyResponse:
    """
    Create or replace a routing policy for the given alias.
    Only one active policy per alias is allowed (unique constraint on workspace+alias).
    """
    require_cloud("Advanced routing policies")
    # Check for existing policy on this alias
    existing_stmt = select(RoutingPolicy).where(
        RoutingPolicy.workspace_id == workspace.id,
        RoutingPolicy.alias == body.alias,
    )
    existing = (await db.execute(existing_stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"A routing policy for alias '{body.alias}' already exists. "
            "Use PUT /gateway/policies/{id} to update it.",
        )

    policy = RoutingPolicy(
        workspace_id=workspace.id,
        alias=body.alias,
        policy_type=body.policy_type,
        config=body.config,
    )
    db.add(policy)
    await db.flush()
    await db.commit()
    await db.refresh(policy)
    return RoutingPolicyResponse.model_validate(policy)


@router.get("/policies", response_model=RoutingPolicyList)
async def list_routing_policies(
    workspace: WorkspaceDep,
    db: DbDep,
    include_inactive: bool = Query(False),
) -> RoutingPolicyList:
    require_cloud("Advanced routing policies")
    stmt = select(RoutingPolicy).where(RoutingPolicy.workspace_id == workspace.id)
    if not include_inactive:
        stmt = stmt.where(RoutingPolicy.is_active.is_(True))
    stmt = stmt.order_by(RoutingPolicy.alias.asc())
    result = await db.execute(stmt)
    policies = list(result.scalars().all())
    return RoutingPolicyList(items=[RoutingPolicyResponse.model_validate(p) for p in policies])


@router.put("/policies/{policy_id}", response_model=RoutingPolicyResponse)
async def update_routing_policy(
    policy_id: uuid.UUID,
    body: RoutingPolicyUpdate,
    workspace: WorkspaceDep,
    db: DbDep,
) -> RoutingPolicyResponse:
    require_cloud("Advanced routing policies")
    policy = await db.get(RoutingPolicy, policy_id)
    if policy is None or policy.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Routing policy not found")

    if body.policy_type is not None:
        policy.policy_type = body.policy_type
    if body.config is not None:
        policy.config = body.config
    if body.is_active is not None:
        policy.is_active = body.is_active
    policy.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(policy)
    return RoutingPolicyResponse.model_validate(policy)


@router.delete("/policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_routing_policy(
    policy_id: uuid.UUID,
    workspace: WorkspaceDep,
    db: DbDep,
) -> None:
    require_cloud("Advanced routing policies")
    policy = await db.get(RoutingPolicy, policy_id)
    if policy is None or policy.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Routing policy not found")
    await db.delete(policy)
    await db.commit()


# ── Request log (routing log) ─────────────────────────────────────────────────


@router.get("/requests", response_model=GatewayRequestList)
async def list_gateway_requests(
    workspace: WorkspaceDep,
    db: DbDep,
    alias: str | None = Query(None, description="Filter by model alias"),
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> GatewayRequestList:
    """
    Return recent gateway requests with routing decision reasons.
    Useful for auditing which policy selected which route and why.
    """
    stmt = select(GatewayRequest).where(GatewayRequest.workspace_id == workspace.id)

    if alias:
        stmt = stmt.where(GatewayRequest.model_requested == alias)
    if status_filter:
        stmt = stmt.where(GatewayRequest.status == status_filter)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = stmt.order_by(GatewayRequest.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    items = list(result.scalars().all())

    return GatewayRequestList(
        items=[GatewayRequestResponse.model_validate(r) for r in items],
        total=total,
    )


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
            func.count(GatewayRequest.id)
            .filter(GatewayRequest.cache_hit.is_(True))
            .label("cache_hits"),
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
    latency_weighted_sum = Decimal("0")
    latency_weight = 0

    for row in rows:
        total = int(row.total)
        cache_hits = int(row.cache_hits)
        errors = int(row.errors)
        avg_lat = (
            Decimal(str(row.avg_latency)).quantize(Decimal("0.01")) if row.avg_latency else None
        )
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
            latency_weighted_sum += avg_lat * Decimal(total)
            latency_weight += total

    overall_hit_rate = (
        Decimal(str(round(total_cache_hits / total_requests, 4)))
        if total_requests
        else Decimal("0")
    )
    overall_latency = (
        (latency_weighted_sum / Decimal(latency_weight)).quantize(Decimal("0.01"))
        if latency_weight
        else None
    )

    return GatewayStats(
        total_requests=total_requests,
        cache_hits=total_cache_hits,
        cache_hit_rate=overall_hit_rate,
        avg_latency_ms=overall_latency,
        routes=route_stats,
    )


# ── Routing recommendations ────────────────────────────────────────────────────


@router.get("/recommendations/{alias}", response_model=RoutingRecommendationResponse)
async def get_routing_recommendation(
    alias: str,
    workspace: WorkspaceDep,
    db: DbDep,
    window_days: int = Query(30, ge=1, le=365, description="Outcome lookback window in days"),
    workflow_type: str | None = Query(None, description="Filter outcomes by outcome_type"),
    min_sample_size: int = Query(5, ge=1, description="Minimum outcomes per model to include"),
) -> RoutingRecommendationResponse:
    """
    Outcome-based routing recommendation for an alias.

    Aggregates success rate and cost-per-success from the outcomes ledger,
    grouped by the primary model used in each linked agent run.  Returns a
    ranked list of routes with improvement percentages and a plain-English
    recommendation message.

    Example response message:
      "Based on the last 150 outcomes, gpt-4o-mini has a 12% better
       cost-per-success ($0.0023 vs $0.0026) than gpt-4o"
    """
    from runledger_api.services.routing import get_outcome_stats_by_model  # noqa: PLC0415

    # Fetch active routes for this alias
    routes = list(
        (
            await db.execute(
                select(GatewayRoute)
                .where(
                    GatewayRoute.workspace_id == workspace.id,
                    GatewayRoute.alias == alias,
                    GatewayRoute.is_active.is_(True),
                )
                .order_by(GatewayRoute.priority.asc())
            )
        ).scalars().all()
    )
    if not routes:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No active routes for alias '{alias}'")

    models = [r.target_model for r in routes]
    model_to_route = {r.target_model: r for r in routes}

    stats = await get_outcome_stats_by_model(
        db,
        workspace.id,
        models,
        lookback_days=window_days,
        workflow_type=workflow_type,
        min_sample_size=min_sample_size,
    )

    # Build recommendation items — one per route, with stats where available
    items: list[RoutingRecommendationModel] = []
    for route in routes:
        s = stats.get(route.target_model)
        items.append(
            RoutingRecommendationModel(
                model=route.target_model,
                route_id=route.id,
                sample_count=s["sample_count"] if s else 0,
                success_rate=s["success_rate"] if s else 0.0,
                cost_per_success=s["cost_per_success"] if s else None,
                improvement_vs_current=None,  # filled below
            )
        )

    # Sort by cost_per_success ascending (None = worst)
    items.sort(
        key=lambda x: (x.cost_per_success is None, x.cost_per_success or float("inf"))
    )

    # Compute improvement_vs_current: % cheaper than the current top-priority route
    # "current" = highest-priority route (routes[0] before sort, = routes[0] by priority)
    current_model = routes[0].target_model
    current_cps = stats.get(current_model, {}).get("cost_per_success")

    for item in items:
        if current_cps and item.cost_per_success is not None and current_cps > 0:
            item.improvement_vs_current = (current_cps - item.cost_per_success) / current_cps
        else:
            item.improvement_vs_current = None

    total_sampled = sum(i.sample_count for i in items)

    # Determine best
    best_item = items[0] if items and items[0].cost_per_success is not None else None
    best_model = best_item.model if best_item else None
    recommended_route_id = model_to_route[best_model].id if best_model else None

    # Build human-readable message
    if best_item and len(items) > 1 and best_item.improvement_vs_current is not None:
        second = next((i for i in items if i.model != best_model), None)
        improvement_pct = best_item.improvement_vs_current * 100
        cps_best = f"${best_item.cost_per_success:.4f}" if best_item.cost_per_success else "N/A"
        if second and second.cost_per_success:
            cps_second = f"${second.cost_per_success:.4f}"
            message = (
                f"Based on the last {total_sampled} outcomes"
                + (f" of type '{workflow_type}'" if workflow_type else "")
                + f", {best_model} has a {abs(improvement_pct):.1f}% better cost-per-success"
                + f" ({cps_best} vs {cps_second}) than {second.model}"
            )
        else:
            message = (
                f"Based on the last {total_sampled} outcomes"
                + (f" of type '{workflow_type}'" if workflow_type else "")
                + f", {best_model} has the best cost-per-success at {cps_best}"
            )
    elif total_sampled == 0:
        message = (
            f"No outcome data found for alias '{alias}'"
            + (f" (workflow_type='{workflow_type}')" if workflow_type else "")
            + f" in the last {window_days} days. Record outcomes via POST /outcomes to enable this."
        )
    else:
        message = (
            f"Collected {total_sampled} outcomes for '{alias}' over {window_days} days"
            + (f" (workflow_type='{workflow_type}')" if workflow_type else "")
            + ". Need more data per model to make a recommendation."
        )

    return RoutingRecommendationResponse(
        alias=alias,
        window_days=window_days,
        workflow_type=workflow_type,
        total_outcomes_sampled=total_sampled,
        models=items,
        best_model=best_model,
        recommended_route_id=recommended_route_id,
        message=message,
    )
