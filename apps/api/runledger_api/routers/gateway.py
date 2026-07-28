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
GET    /gateway/requests                  Routing log
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import AsyncGenerator
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace
from runledger_api.core.ratelimit import management_rate_limit
from runledger_api.models.gateway import GatewayRequest, GatewayRoute
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
)
from runledger_api.services import context_compiler, intelligent_router, semantic_cache
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

log = logging.getLogger(__name__)

router = APIRouter(
    prefix="/gateway",
    tags=["gateway"],
    dependencies=[Depends(management_rate_limit)],
)

DbDep = Annotated[AsyncSession, Depends(get_db)]
WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]


def _config_fingerprint(
    *,
    model_used: str | None,
    semantic_cache: bool,
    compiler_enabled: bool,
    compiler_config: dict[str, Any] | None,
    ir_decision: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    The optimization config a request ran under, captured so the flywheel can group
    traffic by (segment, config) and learn the cheapest config that holds the SLA.
    Only the *tunable* dimensions are recorded — the analyzer treats this as the key.
    """
    fp: dict[str, Any] = {
        "model": model_used,
        "semantic_cache": bool(semantic_cache),
        "context_compiler": bool(compiler_enabled),
        "routing": bool(ir_decision and ir_decision.get("alias")),
    }
    if compiler_enabled and isinstance(compiler_config, dict):
        stages = compiler_config.get("stages") or {}
        if isinstance(stages, dict):
            fp["stages"] = sorted(k for k, v in stages.items() if v)
        rate = compiler_config.get("compression_rate")
        if rate is not None and (stages.get("compress") if isinstance(stages, dict) else False):
            fp["compression_rate"] = rate
    if ir_decision and ir_decision.get("tier"):
        fp["tier"] = ir_decision.get("tier")
    return fp


def _segment_key(model_alias: str, ir_decision: dict[str, Any] | None) -> str:
    """Coarse label stamped at request time; the router's complexity×risk class when
    intelligent routing ran, otherwise the requested alias."""
    if ir_decision and ir_decision.get("complexity") and ir_decision.get("risk"):
        return f"{ir_decision['complexity']}x{ir_decision['risk']}"
    return model_alias


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
      3. Select target route by priority
      4. Check runtime controls: cost cap + per-user rate limit
      5. Apply PII redaction (if enabled on route)
      6. Forward to provider (with retry + fallback)
      7. Store result in cache + record GatewayRequest
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

    # ── 1b. Semantic cache lookup (opt-in, fail-open) ────────────────────────
    # Enabled per-request (body.semantic_cache) OR via the route's GUI toggle
    # (semantic_cache_enabled). Non-streaming only; never raises — a miss or an
    # unreachable service simply falls through to normal routing.
    semantic_enabled = body.semantic_cache
    if not semantic_enabled and not body.stream:
        from runledger_api.services.gateway import select_routes  # noqa: PLC0415

        _sc_routes = await select_routes(db, workspace.id, body.model)
        semantic_enabled = bool(_sc_routes and _sc_routes[0].semantic_cache_enabled)

    if semantic_enabled and not body.stream:
        sem_hit = await semantic_cache.lookup(workspace.id, body.model, messages)
        if sem_hit is not None:
            usage = sem_hit.get("usage") or {}
            await record_gateway_request(
                db=db,
                workspace_id=workspace.id,
                model_requested=body.model,
                route=None,
                model_used=body.model,
                cache_hit=True,
                input_tokens=usage.get("prompt_tokens"),
                output_tokens=usage.get("completion_tokens"),
                latency_ms=0,
                req_status="cache_hit",
                decision_reason="semantic_cache_hit",
            )
            return sem_hit

    # ── 1c. Context Compiler (opt-in, fail-open) ─────────────────────────────
    # Enabled per-request (body.context_compiler) OR via the route toggle
    # (context_compiler_enabled). Shrinks `messages` before routing; applies to
    # both streaming and non-streaming. Never raises — on any error the original
    # messages pass through untouched.
    compiler_enabled = body.context_compiler
    compiler_config: dict[str, Any] | None = None
    if context_compiler.enabled():
        from runledger_api.services.gateway import select_routes  # noqa: PLC0415

        _cc_routes = await select_routes(db, workspace.id, body.model)
        if _cc_routes:
            compiler_config = _cc_routes[0].context_compiler_config
            compiler_enabled = compiler_enabled or _cc_routes[0].context_compiler_enabled
    effective_tools = body.tools
    if compiler_enabled:
        messages, effective_tools, _cc_report = await context_compiler.compile_messages(
            messages, compiler_config, workspace=str(workspace.id), tools=body.tools
        )
        if _cc_report and _cc_report.get("saved"):
            log.info(
                "context_compiler alias=%s before=%s after=%s saved=%s",
                body.model,
                _cc_report.get("before"),
                _cc_report.get("after"),
                _cc_report.get("saved"),
            )

    # ── 1d. Intelligent routing (opt-in, fail-open) ──────────────────────────
    # Classify complexity × risk → model tier; forward to that tier's alias and set
    # reasoning_effort. Fail-open: on any error the requested alias is used unchanged.
    route_alias = body.model
    effective_reasoning_effort = body.reasoning_effort
    ir_decision: dict[str, Any] | None = None
    ir_enabled = body.intelligent_routing
    routing_config: dict[str, Any] | None = None
    if intelligent_router.enabled():
        from runledger_api.services.gateway import select_routes  # noqa: PLC0415

        _ir_routes = await select_routes(db, workspace.id, body.model)
        if _ir_routes:
            routing_config = _ir_routes[0].routing_config
            ir_enabled = ir_enabled or _ir_routes[0].intelligent_routing_enabled
    if ir_enabled:
        ir_decision = await intelligent_router.classify(messages, routing_config)
        if ir_decision and ir_decision.get("alias"):
            route_alias = ir_decision["alias"]
            if ir_decision.get("reasoning_effort") and effective_reasoning_effort is None:
                effective_reasoning_effort = ir_decision["reasoning_effort"]
            log.info(
                "intelligent_routing alias=%s -> %s (%s)",
                body.model,
                route_alias,
                ir_decision.get("reason"),
            )
        elif routing_config:
            # No decision → optional default-tier fallback (on_failure = a tier name)
            on_fail = routing_config.get("on_failure")
            if isinstance(on_fail, str) and on_fail != "passthrough":
                route_alias = (routing_config.get("tiers") or {}).get(on_fail, route_alias)

    # ── 2. Streaming path ────────────────────────────────────────────────────
    if body.stream:
        from runledger_api.services.gateway import select_routes  # noqa: PLC0415

        routes = await select_routes(db, workspace.id, route_alias)
        if not routes:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"No active gateway routes for alias '{route_alias}'",
            )
        route = routes[0]
        decision_reason = ir_decision["reason"] if ir_decision and ir_decision.get("alias") else "priority"

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
                tools=effective_tools,
                tool_choice=body.tool_choice,
                reasoning_effort=effective_reasoning_effort,
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
            config_fingerprint=_config_fingerprint(
                model_used=route.target_model,
                semantic_cache=semantic_enabled,
                compiler_enabled=compiler_enabled,
                compiler_config=compiler_config,
                ir_decision=ir_decision,
            ),
            segment_key=_segment_key(body.model, ir_decision),
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
            model_alias=route_alias,
            messages=messages,
            temperature=body.temperature,
            max_tokens=body.max_tokens,
            top_p=body.top_p,
            frequency_penalty=body.frequency_penalty,
            presence_penalty=body.presence_penalty,
            seed=body.seed,
            stop=body.stop,
            response_format=body.response_format,
            tools=effective_tools,
            tool_choice=body.tool_choice,
            reasoning_effort=effective_reasoning_effort,
        )
        if ir_decision and ir_decision.get("alias"):
            decision_reason = ir_decision["reason"]
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

    # Semantic cache store (opt-in, fail-open — bounded 2s timeout, mirrors exact-cache store)
    if body.semantic_cache or winning_route.semantic_cache_enabled:
        await semantic_cache.store(
            workspace_id=workspace.id,
            model=body.model,
            messages=messages,
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
        config_fingerprint=_config_fingerprint(
            model_used=winning_route.target_model,
            semantic_cache=body.semantic_cache or winning_route.semantic_cache_enabled,
            compiler_enabled=compiler_enabled,
            compiler_config=compiler_config,
            ir_decision=ir_decision,
        ),
        segment_key=_segment_key(body.model, ir_decision),
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
        semantic_cache_enabled=body.semantic_cache_enabled,
        context_compiler_enabled=body.context_compiler_enabled,
        context_compiler_config=body.context_compiler_config,
        intelligent_routing_enabled=body.intelligent_routing_enabled,
        routing_config=body.routing_config,
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
    if body.semantic_cache_enabled is not None:
        route.semantic_cache_enabled = body.semantic_cache_enabled
    if body.context_compiler_enabled is not None:
        route.context_compiler_enabled = body.context_compiler_enabled
    if "context_compiler_config" in body.model_fields_set:
        route.context_compiler_config = body.context_compiler_config
    if body.intelligent_routing_enabled is not None:
        route.intelligent_routing_enabled = body.intelligent_routing_enabled
    if "routing_config" in body.model_fields_set:
        route.routing_config = body.routing_config
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
