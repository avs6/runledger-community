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
import math
import time
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any
from urllib.parse import urlencode

import httpx
import sqlalchemy as sa
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_api_key, get_current_workspace, require_org_admin
from runledger_api.core.ratelimit import ingest_rate_limit, management_rate_limit
from runledger_api.models.gateway import (
    GatewayPassThroughEndpoint,
    GatewayRequest,
    GatewayRoute,
    GatewayRoutingGroup,
    RoutingPolicy,
)
from runledger_api.models.tenant import ApiKey, TenantUser, User, Workspace
from runledger_api.schemas.gateway import (
    GatewayCompletionRequest,
    GatewayDeploymentHealthItem,
    GatewayDeploymentHealthList,
    GatewayPassThroughEndpointCreate,
    GatewayPassThroughEndpointList,
    GatewayPassThroughEndpointResponse,
    GatewayPassThroughEndpointStats,
    GatewayPassThroughEndpointStatsList,
    GatewayPassThroughTestRequest,
    GatewayPassThroughTestResponse,
    GatewayPassThroughEndpointUpdate,
    GatewayBenchmarkComparisonItem,
    GatewayBenchmarkComparisonList,
    GatewayRequestList,
    GatewayRequestResponse,
    GatewayRoutingGroupCreate,
    GatewayRoutingGroupList,
    GatewayRoutingGroupResponse,
    GatewayRoutingGroupRouteSummary,
    GatewayRoutingGroupUpdate,
    GatewayRoutingStrategyComparison,
    GatewayRoutingStrategyComparisonItem,
    GatewayRouteCreate,
    GatewayRouteList,
    GatewayRouteResponse,
    GatewayRouteStats,
    GatewayRouteUpdate,
    GatewayStats,
    RoutingPolicyActionResponse,
    RoutingPolicyAnalysisResponse,
    RoutingPolicyCreate,
    RoutingPolicyList,
    RoutingPolicyPromotionRequest,
    RoutingPolicyResponse,
    RoutingPolicyUpdate,
)
from runledger_api.services import context_compiler, intelligent_router, semantic_cache
from runledger_api.services.auth import verify_api_key
from runledger_api.services.gateway import (
    check_cache,
    choose_route_for_alias,
    increment_hit_count,
    make_cache_key,
    record_gateway_request,
    resolve_request_tags,
    route_and_forward,
    store_cache,
    stream_request,
)
from runledger_api.services.gateway_controls import check_cost_cap, check_per_user_rpm
from runledger_api.services.gateway_redact import redact_messages
from runledger_api.services.guardrails import evaluate_guardrails
from runledger_api.services.routing import analyze_routing_policy
from runledger_api.services.security import (
    authenticate_oidc_token,
    enforce_required_metadata,
    evaluate_ip_acl,
    get_client_ip,
)

log = logging.getLogger(__name__)

router = APIRouter(
    prefix="/gateway",
    tags=["gateway"],
    dependencies=[Depends(ingest_rate_limit)],
)

DbDep = Annotated[AsyncSession, Depends(get_db)]
WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]
OrgAdminDep = Annotated[tuple[Workspace, User, TenantUser | None], Depends(require_org_admin)]


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


def _serialize_gateway_route(
    route: GatewayRoute,
    *,
    routing_group_name: str | None = None,
) -> GatewayRouteResponse:
    payload = GatewayRouteResponse.model_validate(route).model_dump()
    payload["routing_group_name"] = routing_group_name
    return GatewayRouteResponse(**payload)


def _serialize_routing_group(
    group: GatewayRoutingGroup,
    routes: list[GatewayRoute],
) -> GatewayRoutingGroupResponse:
    payload = GatewayRoutingGroupResponse.model_validate(group).model_dump()
    payload["route_count"] = len(routes)
    payload["routes"] = [
        GatewayRoutingGroupRouteSummary.model_validate(route).model_dump() for route in routes
    ]
    return GatewayRoutingGroupResponse(**payload)


# ── Chat completions ────────────────────────────────────────────────────────────


ApiKeyDep = Annotated[ApiKey, Depends(get_current_api_key)]

_PASSTHROUGH_ALLOWED_REQUEST_HEADERS = {
    "accept",
    "accept-encoding",
    "content-type",
    "if-match",
    "if-none-match",
    "user-agent",
    "x-correlation-id",
    "x-request-id",
}
_PASSTHROUGH_ALLOWED_RESPONSE_HEADERS = {
    "cache-control",
    "content-length",
    "content-type",
    "etag",
    "last-modified",
}


async def _resolve_gateway_workspace(
    request: Request,
    db: AsyncSession,
) -> tuple[Workspace, ApiKey | None]:
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    raw_bearer = auth_header.split(" ", 1)[1].strip()
    api_key = await verify_api_key(raw_bearer, db)
    oidc_auth = None if api_key is not None else await authenticate_oidc_token(raw_bearer, db)
    if api_key is None and oidc_auth is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    workspace = (
        (await db.execute(select(Workspace).where(Workspace.id == api_key.workspace_id))).scalar_one()
        if api_key is not None
        else oidc_auth.workspace
    )
    return workspace, api_key


def _build_passthrough_headers(
    endpoint: GatewayPassThroughEndpoint,
    request: Request | None = None,
    source_headers: dict[str, str] | None = None,
) -> dict[str, str]:
    headers: dict[str, str] = {}
    if request is not None:
        for key, value in request.headers.items():
            lowered = key.lower()
            if lowered in _PASSTHROUGH_ALLOWED_REQUEST_HEADERS:
                headers[key] = value
    for key, value in (source_headers or {}).items():
        lowered = key.lower()
        if lowered in _PASSTHROUGH_ALLOWED_REQUEST_HEADERS:
            headers[key] = value

    for key, value in (endpoint.header_config or {}).items():
        if value is not None:
            headers[str(key)] = str(value)

    auth_type = (endpoint.auth_type or "").lower()
    auth_config = endpoint.auth_config or {}
    if auth_type == "bearer" and auth_config.get("token"):
        headers["Authorization"] = f"Bearer {auth_config['token']}"
    elif auth_type == "api_key" and auth_config.get("value"):
        header_name = str(auth_config.get("header_name") or "x-api-key")
        headers[header_name] = str(auth_config["value"])

    return headers


def _build_passthrough_target_url(
    endpoint: GatewayPassThroughEndpoint,
    *,
    upstream_path: str = "",
    query_params: dict[str, Any] | None = None,
) -> str:
    upstream_base = endpoint.upstream_base_url.rstrip("/")
    path_prefix = (endpoint.path_prefix or "/").strip("/")
    upstream_suffix = upstream_path.strip("/")
    path_parts = [part for part in (path_prefix, upstream_suffix) if part]
    target_url = upstream_base
    if path_parts:
        target_url = f"{upstream_base}/{'/'.join(path_parts)}"

    merged_query: dict[str, Any] = {}
    for key, value in (endpoint.default_query or {}).items():
        if value is not None:
            merged_query[str(key)] = str(value)
    for key, value in (query_params or {}).items():
        if value is not None:
            merged_query[str(key)] = str(value)
    if merged_query:
        target_url = f"{target_url}?{urlencode(merged_query, doseq=True)}"
    return target_url


@router.post("/chat/completions")
async def gateway_chat_completions(
    body: GatewayCompletionRequest,
    request: Request,
    db: DbDep,
    x_runledger_end_user_id: str | None = Header(default=None, alias="X-RunLedger-End-User-Id"),
    x_runledger_tags: str | None = Header(default=None, alias="X-RunLedger-Tags"),
    x_runledger_region: str | None = Header(default=None, alias="X-RunLedger-Region"),
    x_runledger_timeout_ms: int | None = Header(default=None, alias="X-RunLedger-Timeout-Ms"),
    x_runledger_completion_timeout_ms: int | None = Header(default=None, alias="X-RunLedger-Completion-Timeout-Ms"),
    x_runledger_stream_timeout_ms: int | None = Header(default=None, alias="X-RunLedger-Stream-Timeout-Ms"),
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
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    raw_bearer = auth_header.split(" ", 1)[1].strip()
    api_key = await verify_api_key(raw_bearer, db)
    oidc_auth = None if api_key is not None else await authenticate_oidc_token(raw_bearer, db)
    if api_key is None and oidc_auth is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    workspace = (
        (await db.execute(select(Workspace).where(Workspace.id == api_key.workspace_id))).scalar_one()
        if api_key is not None
        else oidc_auth.workspace
    )
    metadata = body.metadata or {}
    team_name = str(metadata.get("team")) if metadata.get("team") else None
    await evaluate_ip_acl(
        db,
        workspace_id=workspace.id,
        api_key_id=api_key.id if api_key is not None else None,
        team_name=team_name,
        client_ip=get_client_ip(request.headers.get("x-forwarded-for"), request.client.host if request.client else None),
    )
    missing_metadata = await enforce_required_metadata(db, workspace_id=workspace.id, metadata=metadata)
    messages = [{"role": m.role, "content": m.content} for m in body.messages]
    request_tags = [str(tag).strip() for tag in metadata.get("tags", [])] if isinstance(metadata.get("tags"), list) else []
    if x_runledger_tags:
        request_tags.extend(tag.strip() for tag in x_runledger_tags.split(",") if tag.strip())
    request_tags = await resolve_request_tags(db, workspace.id, body.model, request_tags)
    preferred_region = x_runledger_region.strip() if x_runledger_region else None

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

        _sc_routes = await select_routes(db, workspace.id, body.model, request_tags, preferred_region)
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

        _cc_routes = await select_routes(db, workspace.id, body.model, request_tags, preferred_region)
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

        _ir_routes = await select_routes(db, workspace.id, body.model, request_tags, preferred_region)
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
        route, decision_reason = await choose_route_for_alias(
            db,
            workspace.id,
            route_alias,
            messages,
            request_tags=request_tags,
            preferred_region=preferred_region,
        )
        if route is None:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"No active gateway routes for alias '{route_alias}'",
            )
        if ir_decision and ir_decision.get("alias"):
            decision_reason = ir_decision["reason"]

        # Runtime controls
        await check_cost_cap(db, route, workspace.id)
        if x_runledger_end_user_id and route.per_user_rpm_limit:
            from runledger_api.core.redis import get_redis  # noqa: PLC0415

            redis = await get_redis()
            await check_per_user_rpm(
                redis, workspace.id, x_runledger_end_user_id, route.id, route.per_user_rpm_limit
            )

        # Guardrails — pre_call
        _guardrail_bypass = getattr(workspace, "guardrail_bypass", False)
        _key_gr_config = getattr(api_key, "guardrail_config", {}) or {}
        _key_gr_disabled = _key_gr_config.get("disabled", False)
        _key_gr_ids = _key_gr_config.get("guardrail_ids")

        if not _guardrail_bypass and not _key_gr_disabled:
            guardrail_ids = (
                [uuid.UUID(g) for g in body.guardrails]
                if body.guardrails
                else ([uuid.UUID(g) for g in _key_gr_ids] if _key_gr_ids else None)
            )
            pre_texts: list[str] = [str(m.get("content", "")) for m in messages if m.get("content")]
            gr_decision, gr_results, gr_latency = await evaluate_guardrails(
                db,
                workspace.id,
                "pre_call",
                texts=pre_texts,
                structured_messages=messages,
                model=body.model,
                end_user_id=x_runledger_end_user_id,
                guardrail_ids=guardrail_ids,
            )
            if gr_decision == "block":
                blocked_reason = next(
                    (r["reason"] for r in gr_results if r["decision"] == "block"),
                    "Blocked by guardrail",
                )
                raise HTTPException(
                    status_code=status.HTTP_451_UNAVAILABLE_FOR_LEGAL_REASONS, detail=blocked_reason
                )
            if gr_decision == "modify":
                for r in gr_results:
                    if r.get("modified_texts") and r["decision"] == "modify":
                        for i, m in enumerate(messages):
                            if m.get("content") and i < len(r["modified_texts"]):
                                messages[i]["content"] = r["modified_texts"][i]

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
                timeout_override_ms=x_runledger_stream_timeout_ms or x_runledger_timeout_ms,
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
            request_tags=request_tags,
            preferred_region=preferred_region,
            timeout_override_ms=x_runledger_completion_timeout_ms or x_runledger_timeout_ms,
            fallback_aliases=body.fallback_aliases,
        )
        if ir_decision and ir_decision.get("alias"):
            decision_reason = ir_decision["reason"]
        elif missing_metadata:
            decision_reason = f"{decision_reason}|metadata_warn:{','.join(missing_metadata)}"
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

    # Guardrails — post_call + during_call
    if not _guardrail_bypass and not _key_gr_disabled:
        response_content = ""
        choices = response_json.get("choices", [])
        if choices:
            msg = choices[0].get("message", {})
            response_content = msg.get("content", "") or ""
        if response_content:
            import asyncio  # noqa: PLC0415

            post_coro = evaluate_guardrails(
                db,
                workspace.id,
                "post_call",
                texts=[response_content],
                structured_messages=messages,
                model=body.model,
                end_user_id=x_runledger_end_user_id,
            )
            input_texts: list[str] = [
                str(m.get("content", "")) for m in messages if m.get("content")
            ]
            during_coro = evaluate_guardrails(
                db,
                workspace.id,
                "during_call",
                texts=input_texts + [response_content],
                structured_messages=messages,
                model=body.model,
                end_user_id=x_runledger_end_user_id,
            )
            (
                (post_decision, post_results, _),
                (during_decision, during_results, _),
            ) = await asyncio.gather(post_coro, during_coro)

            for phase_decision, phase_results in [
                (post_decision, post_results),
                (during_decision, during_results),
            ]:
                if phase_decision == "block":
                    blocked_reason = next(
                        (r["reason"] for r in phase_results if r["decision"] == "block"),
                        "Response blocked by guardrail",
                    )
                    raise HTTPException(
                        status_code=status.HTTP_451_UNAVAILABLE_FOR_LEGAL_REASONS,
                        detail=blocked_reason,
                    )

    usage = response_json.get("usage") or {}
    input_tokens = usage.get("prompt_tokens")
    output_tokens = usage.get("completion_tokens")
    total_wall_ms = int((time.monotonic() - t0) * 1000)
    gateway_overhead_ms = max(total_wall_ms - (latency_ms or 0), 0)

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
        )
        | {
            "provider_latency_ms": latency_ms,
            "total_wall_ms": total_wall_ms,
            "gateway_overhead_ms": gateway_overhead_ms,
            "region": winning_route.region,
        },
        segment_key=_segment_key(body.model, ir_decision),
    )

    return response_json


# ── Routes CRUD ────────────────────────────────────────────────────────────────


@router.post(
    "/routing-groups",
    response_model=GatewayRoutingGroupResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_gateway_routing_group(
    body: GatewayRoutingGroupCreate,
    auth: OrgAdminDep,
    db: DbDep,
) -> GatewayRoutingGroupResponse:
    workspace = auth[0]
    group = GatewayRoutingGroup(
        workspace_id=workspace.id,
        alias=body.alias,
        name=body.name,
        description=body.description,
        match_tags=body.match_tags,
        default_tags=body.default_tags,
        strategy_type=body.strategy_type,
        strategy_config=body.strategy_config,
        is_active=body.is_active,
    )
    db.add(group)
    await db.commit()
    await db.refresh(group)
    return _serialize_routing_group(group, [])


@router.get("/routing-groups", response_model=GatewayRoutingGroupList)
async def list_gateway_routing_groups(
    auth: OrgAdminDep,
    db: DbDep,
    alias: str | None = Query(default=None),
    include_inactive: bool = Query(default=False),
) -> GatewayRoutingGroupList:
    workspace = auth[0]
    stmt = select(GatewayRoutingGroup).where(GatewayRoutingGroup.workspace_id == workspace.id)
    if alias:
        stmt = stmt.where(GatewayRoutingGroup.alias == alias)
    if not include_inactive:
        stmt = stmt.where(GatewayRoutingGroup.is_active.is_(True))
    stmt = stmt.order_by(
        GatewayRoutingGroup.alias.asc(),
        GatewayRoutingGroup.name.asc(),
        GatewayRoutingGroup.created_at.asc(),
    )
    groups = list((await db.execute(stmt)).scalars().all())
    routes = list(
        (
            await db.execute(
                select(GatewayRoute)
                .where(GatewayRoute.workspace_id == workspace.id)
                .order_by(GatewayRoute.alias.asc(), GatewayRoute.priority.asc())
            )
        )
        .scalars()
        .all()
    )
    routes_by_group: dict[uuid.UUID, list[GatewayRoute]] = {}
    for route in routes:
        if route.routing_group_id is not None:
            routes_by_group.setdefault(route.routing_group_id, []).append(route)
    return GatewayRoutingGroupList(
        items=[_serialize_routing_group(group, routes_by_group.get(group.id, [])) for group in groups]
    )


@router.get(
    "/routing-groups/strategy-comparison",
    response_model=GatewayRoutingStrategyComparison,
)
async def gateway_routing_strategy_comparison(
    auth: OrgAdminDep,
    db: DbDep,
) -> GatewayRoutingStrategyComparison:
    workspace = auth[0]
    groups = list(
        (
            await db.execute(
                select(GatewayRoutingGroup).where(GatewayRoutingGroup.workspace_id == workspace.id)
            )
        )
        .scalars()
        .all()
    )
    group_map = {group.id: group for group in groups}
    routes = list(
        (await db.execute(select(GatewayRoute).where(GatewayRoute.workspace_id == workspace.id)))
        .scalars()
        .all()
    )
    routes_by_group: dict[uuid.UUID | None, list[GatewayRoute]] = {}
    for route in routes:
        routes_by_group.setdefault(route.routing_group_id, []).append(route)

    rows = (
        await db.execute(
            select(
                GatewayRoute.routing_group_id,
                GatewayRoute.alias,
                func.count(GatewayRequest.id).label("total_requests"),
                func.avg(GatewayRequest.latency_ms).label("avg_latency_ms"),
                func.count(GatewayRequest.id)
                .filter(GatewayRequest.cache_hit.is_(True))
                .label("cache_hits"),
                func.count(GatewayRequest.id)
                .filter(GatewayRequest.status == "error")
                .label("error_count"),
            )
            .select_from(GatewayRequest)
            .join(GatewayRoute, GatewayRequest.route_id == GatewayRoute.id, isouter=True)
            .where(GatewayRequest.workspace_id == workspace.id)
            .group_by(GatewayRoute.routing_group_id, GatewayRoute.alias)
        )
    ).all()
    items: list[GatewayRoutingStrategyComparisonItem] = []
    for row in rows:
        total_requests = int(row.total_requests or 0)
        cache_hits = int(row.cache_hits or 0)
        error_count = int(row.error_count or 0)
        group = group_map.get(row.routing_group_id)
        group_routes = routes_by_group.get(row.routing_group_id, [])
        items.append(
            GatewayRoutingStrategyComparisonItem(
                routing_group_id=row.routing_group_id,
                alias=row.alias or "ungrouped",
                group_name=group.name if group is not None else "Ungrouped",
                strategy_type=group.strategy_type if group is not None else "manual",
                total_requests=total_requests,
                cache_hit_rate=Decimal(str(round(cache_hits / total_requests, 4))) if total_requests else Decimal("0"),
                avg_latency_ms=(
                    Decimal(str(row.avg_latency_ms)).quantize(Decimal("0.01"))
                    if row.avg_latency_ms is not None
                    else None
                ),
                error_rate=Decimal(str(round(error_count / total_requests, 4))) if total_requests else Decimal("0"),
                active_routes=sum(1 for route in group_routes if route.is_active),
                default_tags=list(group.default_tags or []) if group is not None else [],
                match_tags=list(group.match_tags or []) if group is not None else [],
            )
        )
    return GatewayRoutingStrategyComparison(items=items)


@router.put("/routing-groups/{group_id}", response_model=GatewayRoutingGroupResponse)
async def update_gateway_routing_group(
    group_id: uuid.UUID,
    body: GatewayRoutingGroupUpdate,
    auth: OrgAdminDep,
    db: DbDep,
) -> GatewayRoutingGroupResponse:
    workspace = auth[0]
    group = await db.get(GatewayRoutingGroup, group_id)
    if group is None or group.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gateway routing group not found")

    if body.alias is not None:
        group.alias = body.alias
    if body.name is not None:
        group.name = body.name
    if "description" in body.model_fields_set:
        group.description = body.description
    if body.match_tags is not None:
        group.match_tags = body.match_tags
    if body.default_tags is not None:
        group.default_tags = body.default_tags
    if body.strategy_type is not None:
        group.strategy_type = body.strategy_type
    if "strategy_config" in body.model_fields_set:
        group.strategy_config = body.strategy_config
    if body.is_active is not None:
        group.is_active = body.is_active
    group.updated_at = func.now()

    await db.commit()
    await db.refresh(group)
    routes = list(
        (
            await db.execute(
                select(GatewayRoute)
                .where(GatewayRoute.routing_group_id == group.id)
                .order_by(GatewayRoute.priority.asc())
            )
        )
        .scalars()
        .all()
    )
    return _serialize_routing_group(group, routes)


@router.delete("/routing-groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_gateway_routing_group(
    group_id: uuid.UUID,
    auth: OrgAdminDep,
    db: DbDep,
) -> None:
    workspace = auth[0]
    group = await db.get(GatewayRoutingGroup, group_id)
    if group is None or group.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gateway routing group not found")

    grouped_routes = list(
        (await db.execute(select(GatewayRoute).where(GatewayRoute.routing_group_id == group.id)))
        .scalars()
        .all()
    )
    for route in grouped_routes:
        route.routing_group_id = None
    await db.delete(group)
    await db.commit()


@router.post("/routes", response_model=GatewayRouteResponse, status_code=status.HTTP_201_CREATED)
async def create_gateway_route(
    body: GatewayRouteCreate,
    auth: OrgAdminDep,
    db: DbDep,
) -> GatewayRouteResponse:
    workspace = auth[0]
    routing_group_name: str | None = None
    if body.routing_group_id is not None:
        group = await db.get(GatewayRoutingGroup, body.routing_group_id)
        if group is None or group.workspace_id != workspace.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Gateway routing group not found")
        if group.alias != body.alias:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Routing group alias must match route alias")
        routing_group_name = group.name
    route = GatewayRoute(
        workspace_id=workspace.id,
        routing_group_id=body.routing_group_id,
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
        fallback_config=body.fallback_config,
        required_tags=body.required_tags,
        excluded_tags=body.excluded_tags,
        retry_count=body.retry_count,
        timeout_ms=body.timeout_ms,
        cooldown_seconds=body.cooldown_seconds,
        region=body.region,
        mirror_config=body.mirror_config,
        health_auto_disable=body.health_auto_disable,
    )
    db.add(route)
    await db.flush()
    await db.commit()
    await db.refresh(route)
    return _serialize_gateway_route(route, routing_group_name=routing_group_name)


@router.get("/routes", response_model=GatewayRouteList)
async def list_gateway_routes(
    auth: OrgAdminDep,
    db: DbDep,
    include_inactive: bool = Query(False),
) -> GatewayRouteList:
    workspace = auth[0]
    stmt = select(GatewayRoute).where(GatewayRoute.workspace_id == workspace.id)
    if not include_inactive:
        stmt = stmt.where(GatewayRoute.is_active.is_(True))
    stmt = stmt.order_by(GatewayRoute.priority.asc(), GatewayRoute.created_at.asc())
    result = await db.execute(stmt)
    routes = list(result.scalars().all())
    group_names: dict[uuid.UUID, str] = {}
    group_ids = [route.routing_group_id for route in routes if route.routing_group_id is not None]
    if group_ids:
        group_result = await db.execute(
            select(GatewayRoutingGroup.id, GatewayRoutingGroup.name).where(
                GatewayRoutingGroup.id.in_(group_ids)
            )
        )
        group_names = {row.id: row.name for row in group_result.all()}
    return GatewayRouteList(
        items=[
            _serialize_gateway_route(route, routing_group_name=group_names.get(route.routing_group_id))
            for route in routes
        ]
    )


@router.put("/routes/{route_id}", response_model=GatewayRouteResponse)
async def update_gateway_route(
    route_id: uuid.UUID,
    body: GatewayRouteUpdate,
    auth: OrgAdminDep,
    db: DbDep,
) -> GatewayRouteResponse:
    workspace = auth[0]
    route = await db.get(GatewayRoute, route_id)
    if route is None or route.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gateway route not found")
    routing_group_name: str | None = None

    if body.alias is not None:
        route.alias = body.alias
    if "routing_group_id" in body.model_fields_set:
        if body.routing_group_id is None:
            route.routing_group_id = None
        else:
            group = await db.get(GatewayRoutingGroup, body.routing_group_id)
            if group is None or group.workspace_id != workspace.id:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Gateway routing group not found")
            target_alias = body.alias or route.alias
            if group.alias != target_alias:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "Routing group alias must match route alias",
                )
            route.routing_group_id = group.id
            routing_group_name = group.name
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
    if "fallback_config" in body.model_fields_set:
        route.fallback_config = body.fallback_config
    if body.required_tags is not None:
        route.required_tags = body.required_tags
    if body.excluded_tags is not None:
        route.excluded_tags = body.excluded_tags
    if body.retry_count is not None:
        route.retry_count = body.retry_count
    if "timeout_ms" in body.model_fields_set:
        route.timeout_ms = body.timeout_ms
    if body.cooldown_seconds is not None:
        route.cooldown_seconds = body.cooldown_seconds
    if "region" in body.model_fields_set:
        route.region = body.region
    if "mirror_config" in body.model_fields_set:
        route.mirror_config = body.mirror_config
    if body.health_auto_disable is not None:
        route.health_auto_disable = body.health_auto_disable

    await db.commit()
    await db.refresh(route)
    if route.routing_group_id is not None and routing_group_name is None:
        group = await db.get(GatewayRoutingGroup, route.routing_group_id)
        routing_group_name = group.name if group is not None else None
    return _serialize_gateway_route(route, routing_group_name=routing_group_name)


@router.delete("/routes/{route_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_gateway_route(
    route_id: uuid.UUID,
    auth: OrgAdminDep,
    db: DbDep,
) -> None:
    workspace = auth[0]
    route = await db.get(GatewayRoute, route_id)
    if route is None or route.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gateway route not found")
    await db.delete(route)
    await db.commit()


@router.post("/policies", response_model=RoutingPolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_routing_policy(
    body: RoutingPolicyCreate,
    auth: OrgAdminDep,
    db: DbDep,
) -> RoutingPolicyResponse:
    workspace = auth[0]
    existing = (
        await db.execute(
            select(RoutingPolicy).where(
                RoutingPolicy.workspace_id == workspace.id,
                RoutingPolicy.alias == body.alias,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Routing policy already exists for alias")
    policy = RoutingPolicy(
        workspace_id=workspace.id,
        alias=body.alias,
        policy_type=body.policy_type,
        config=body.config,
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return RoutingPolicyResponse.model_validate(policy)


@router.get("/policies", response_model=RoutingPolicyList)
async def list_routing_policies(
    auth: OrgAdminDep,
    db: DbDep,
) -> RoutingPolicyList:
    workspace = auth[0]
    items = list(
        (
            await db.execute(
                select(RoutingPolicy)
                .where(RoutingPolicy.workspace_id == workspace.id)
                .order_by(RoutingPolicy.alias.asc(), RoutingPolicy.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    return RoutingPolicyList(items=[RoutingPolicyResponse.model_validate(item) for item in items])


@router.put("/policies/{policy_id}", response_model=RoutingPolicyResponse)
async def update_routing_policy(
    policy_id: uuid.UUID,
    body: RoutingPolicyUpdate,
    auth: OrgAdminDep,
    db: DbDep,
) -> RoutingPolicyResponse:
    workspace = auth[0]
    policy = await db.get(RoutingPolicy, policy_id)
    if policy is None or policy.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Routing policy not found")
    if body.policy_type is not None:
        policy.policy_type = body.policy_type
    if "config" in body.model_fields_set:
        policy.config = body.config or {}
    if body.is_active is not None:
        policy.is_active = body.is_active
    policy.updated_at = func.now()
    await db.commit()
    await db.refresh(policy)
    return RoutingPolicyResponse.model_validate(policy)


@router.delete("/policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_routing_policy(
    policy_id: uuid.UUID,
    auth: OrgAdminDep,
    db: DbDep,
) -> None:
    workspace = auth[0]
    policy = await db.get(RoutingPolicy, policy_id)
    if policy is None or policy.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Routing policy not found")
    await db.delete(policy)
    await db.commit()


@router.get("/policies/{policy_id}/analysis", response_model=RoutingPolicyAnalysisResponse)
async def get_routing_policy_analysis(
    policy_id: uuid.UUID,
    auth: OrgAdminDep,
    db: DbDep,
) -> RoutingPolicyAnalysisResponse:
    workspace = auth[0]
    policy = await db.get(RoutingPolicy, policy_id)
    if policy is None or policy.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Routing policy not found")
    analysis = await analyze_routing_policy(db, workspace.id, policy)
    return RoutingPolicyAnalysisResponse(**analysis)


@router.post("/policies/{policy_id}/promote", response_model=RoutingPolicyActionResponse)
async def promote_routing_policy_variant(
    policy_id: uuid.UUID,
    body: RoutingPolicyPromotionRequest,
    auth: OrgAdminDep,
    db: DbDep,
) -> RoutingPolicyActionResponse:
    workspace = auth[0]
    policy = await db.get(RoutingPolicy, policy_id)
    if policy is None or policy.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Routing policy not found")
    analysis = await analyze_routing_policy(db, workspace.id, policy)
    if policy.policy_type == "ab_test":
        if analysis.get("confidence") == "insufficient_data":
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                analysis.get("summary") or "Not enough A/B test traffic to promote a winner",
            )
        significance_p_value = analysis.get("significance_p_value")
        significance_threshold = float((policy.config or {}).get("significance_threshold", 0.05))
        if significance_p_value is None or float(significance_p_value) >= significance_threshold:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"A/B result is not yet statistically significant at p<{significance_threshold:.4f}",
            )
    route_id = body.route_id or analysis.get("winner_route_id")
    if route_id is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "No winner available to promote")
    policy.policy_type = "weighted"
    policy.config = {
        "weights": {str(route_id): 1.0},
        "promoted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "promoted_from": analysis.get("policy_type"),
        "winner_label": analysis.get("winner_label"),
    }
    policy.updated_at = func.now()
    await db.commit()
    await db.refresh(policy)
    return RoutingPolicyActionResponse(
        policy_id=policy.id,
        policy_type=policy.policy_type,
        summary=f"Promoted {analysis.get('winner_label') or route_id} to 100% traffic.",
        config=policy.config or {},
    )


@router.post("/policies/{policy_id}/rollout/advance", response_model=RoutingPolicyActionResponse)
async def advance_canary_rollout(
    policy_id: uuid.UUID,
    auth: OrgAdminDep,
    db: DbDep,
) -> RoutingPolicyActionResponse:
    workspace = auth[0]
    policy = await db.get(RoutingPolicy, policy_id)
    if policy is None or policy.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Routing policy not found")
    if policy.policy_type != "canary":
        raise HTTPException(status.HTTP_409_CONFLICT, "Rollout advance is only supported for canary policies")
    config = dict(policy.config or {})
    stages = config.get("rollout_stages") if isinstance(config.get("rollout_stages"), list) else [5, 10, 25, 50, 100]
    current_pct = float(config.get("canary_pct", 0.0)) * 100
    next_stage = next((float(stage) for stage in stages if float(stage) > current_pct), None)
    if next_stage is None:
        next_stage = 100.0
    config["canary_pct"] = round(next_stage / 100.0, 4)
    config["last_advanced_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    policy.config = config
    policy.updated_at = func.now()
    await db.commit()
    return RoutingPolicyActionResponse(
        policy_id=policy.id,
        policy_type=policy.policy_type,
        summary=f"Advanced canary rollout to {next_stage:.0f}%.",
        config=config,
    )


@router.post("/policies/{policy_id}/rollback", response_model=RoutingPolicyActionResponse)
async def rollback_policy_rollout(
    policy_id: uuid.UUID,
    auth: OrgAdminDep,
    db: DbDep,
) -> RoutingPolicyActionResponse:
    workspace = auth[0]
    policy = await db.get(RoutingPolicy, policy_id)
    if policy is None or policy.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Routing policy not found")
    config = dict(policy.config or {})
    if policy.policy_type == "canary":
        config["canary_pct"] = 0.0
    elif policy.policy_type == "ab_test":
        config["auto_promote"] = False
    config["rollback_triggered_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    policy.config = config
    policy.updated_at = func.now()
    await db.commit()
    return RoutingPolicyActionResponse(
        policy_id=policy.id,
        policy_type=policy.policy_type,
        summary="Rollback applied to routing policy.",
        config=config,
    )


@router.post(
    "/passthrough",
    response_model=GatewayPassThroughEndpointResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_gateway_passthrough_endpoint(
    body: GatewayPassThroughEndpointCreate,
    auth: OrgAdminDep,
    db: DbDep,
) -> GatewayPassThroughEndpointResponse:
    workspace = auth[0]
    endpoint = GatewayPassThroughEndpoint(
        workspace_id=workspace.id,
        slug=body.slug,
        path_prefix=body.path_prefix,
        upstream_base_url=body.upstream_base_url,
        auth_type=body.auth_type,
        auth_config=body.auth_config,
        header_config=body.header_config,
        default_query=body.default_query,
        timeout_ms=body.timeout_ms,
        rate_limit_rpm=body.rate_limit_rpm,
        cost_per_call_usd=body.cost_per_call_usd,
        is_active=body.is_active,
    )
    db.add(endpoint)
    await db.commit()
    await db.refresh(endpoint)
    return GatewayPassThroughEndpointResponse.model_validate(endpoint)


@router.get("/passthrough", response_model=GatewayPassThroughEndpointList)
async def list_gateway_passthrough_endpoints(
    auth: OrgAdminDep,
    db: DbDep,
    include_inactive: bool = Query(False),
) -> GatewayPassThroughEndpointList:
    workspace = auth[0]
    stmt = select(GatewayPassThroughEndpoint).where(
        GatewayPassThroughEndpoint.workspace_id == workspace.id
    )
    if not include_inactive:
        stmt = stmt.where(GatewayPassThroughEndpoint.is_active.is_(True))
    stmt = stmt.order_by(GatewayPassThroughEndpoint.slug.asc())
    items = (await db.execute(stmt)).scalars().all()
    return GatewayPassThroughEndpointList(
        items=[GatewayPassThroughEndpointResponse.model_validate(item) for item in items]
    )


@router.put("/passthrough/{endpoint_id}", response_model=GatewayPassThroughEndpointResponse)
async def update_gateway_passthrough_endpoint(
    endpoint_id: uuid.UUID,
    body: GatewayPassThroughEndpointUpdate,
    auth: OrgAdminDep,
    db: DbDep,
) -> GatewayPassThroughEndpointResponse:
    workspace = auth[0]
    endpoint = await db.get(GatewayPassThroughEndpoint, endpoint_id)
    if endpoint is None or endpoint.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pass-through endpoint not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(endpoint, field, value)

    await db.commit()
    await db.refresh(endpoint)
    return GatewayPassThroughEndpointResponse.model_validate(endpoint)


@router.delete("/passthrough/{endpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_gateway_passthrough_endpoint(
    endpoint_id: uuid.UUID,
    auth: OrgAdminDep,
    db: DbDep,
) -> None:
    workspace = auth[0]
    endpoint = await db.get(GatewayPassThroughEndpoint, endpoint_id)
    if endpoint is None or endpoint.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pass-through endpoint not found")
    await db.delete(endpoint)
    await db.commit()


@router.post("/passthrough/{endpoint_id}/test", response_model=GatewayPassThroughTestResponse)
async def test_gateway_passthrough_endpoint(
    endpoint_id: uuid.UUID,
    body: GatewayPassThroughTestRequest,
    auth: OrgAdminDep,
    db: DbDep,
) -> GatewayPassThroughTestResponse:
    workspace = auth[0]
    endpoint = await db.get(GatewayPassThroughEndpoint, endpoint_id)
    if endpoint is None or endpoint.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pass-through endpoint not found")

    target_url = _build_passthrough_target_url(
        endpoint,
        upstream_path=body.path or "",
        query_params=body.query,
    )
    timeout_seconds = max(1.0, endpoint.timeout_ms / 1000)
    started = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
            upstream_response = await client.request(
                method=body.method.upper(),
                url=target_url,
                json=body.body_json if body.body_json is not None else None,
                headers=_build_passthrough_headers(endpoint, source_headers=body.headers),
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Upstream test failed: {exc!s}") from exc

    preview = upstream_response.text[:1000] if upstream_response.text else None
    return GatewayPassThroughTestResponse(
        ok=upstream_response.status_code < 400,
        status_code=upstream_response.status_code,
        latency_ms=int((time.monotonic() - started) * 1000),
        target_url=target_url,
        response_preview=preview,
        headers={
            key: value
            for key, value in upstream_response.headers.items()
            if key.lower() in _PASSTHROUGH_ALLOWED_RESPONSE_HEADERS
        },
    )


@router.get("/passthrough/stats", response_model=GatewayPassThroughEndpointStatsList)
async def list_gateway_passthrough_stats(
    auth: OrgAdminDep,
    db: DbDep,
) -> GatewayPassThroughEndpointStatsList:
    workspace = auth[0]
    endpoints = list(
        (
            await db.execute(
                select(GatewayPassThroughEndpoint)
                .where(GatewayPassThroughEndpoint.workspace_id == workspace.id)
                .order_by(GatewayPassThroughEndpoint.slug.asc())
            )
        )
        .scalars()
        .all()
    )
    items: list[GatewayPassThroughEndpointStats] = []
    for endpoint in endpoints:
        requested_model = f"passthrough:{endpoint.slug}"
        row = (
            await db.execute(
                select(
                    func.count(GatewayRequest.id).label("total_requests"),
                    func.count(GatewayRequest.id)
                    .filter(GatewayRequest.status != "error")
                    .label("success_count"),
                    func.count(GatewayRequest.id)
                    .filter(GatewayRequest.status == "error")
                    .label("error_count"),
                    func.avg(GatewayRequest.latency_ms).label("avg_latency_ms"),
                    func.percentile_cont(0.5).within_group(GatewayRequest.latency_ms).label("p50_latency_ms"),
                    func.percentile_cont(0.95).within_group(GatewayRequest.latency_ms).label("p95_latency_ms"),
                    func.percentile_cont(0.99).within_group(GatewayRequest.latency_ms).label("p99_latency_ms"),
                    func.count(GatewayRequest.id)
                    .filter(GatewayRequest.created_at >= func.now() - sa.text("INTERVAL '1 hour'"))
                    .label("last_hour_requests"),
                    func.count(GatewayRequest.id)
                    .filter(GatewayRequest.created_at >= func.now() - sa.text("INTERVAL '24 hours'"))
                    .label("last_24h_requests"),
                )
                .where(
                    GatewayRequest.workspace_id == workspace.id,
                    GatewayRequest.model_requested == requested_model,
                )
            )
        ).one()
        total_requests = int(row.total_requests or 0)
        last_hour_requests = int(row.last_hour_requests or 0)
        last_24h_requests = int(row.last_24h_requests or 0)
        estimated_total_cost = (
            (endpoint.cost_per_call_usd or Decimal("0")) * Decimal(total_requests)
            if endpoint.cost_per_call_usd is not None
            else None
        )
        estimated_24h_cost = (
            (endpoint.cost_per_call_usd or Decimal("0")) * Decimal(last_24h_requests)
            if endpoint.cost_per_call_usd is not None
            else None
        )
        utilization = None
        if endpoint.rate_limit_rpm:
            utilization = Decimal(str(round(last_hour_requests / (endpoint.rate_limit_rpm * 60), 4)))
        items.append(
            GatewayPassThroughEndpointStats(
                endpoint_id=endpoint.id,
                slug=endpoint.slug,
                total_requests=total_requests,
                success_count=int(row.success_count or 0),
                error_count=int(row.error_count or 0),
                avg_latency_ms=Decimal(str(round(float(row.avg_latency_ms), 2))) if row.avg_latency_ms is not None else None,
                p50_latency_ms=Decimal(str(round(float(row.p50_latency_ms), 2))) if row.p50_latency_ms is not None else None,
                p95_latency_ms=Decimal(str(round(float(row.p95_latency_ms), 2))) if row.p95_latency_ms is not None else None,
                p99_latency_ms=Decimal(str(round(float(row.p99_latency_ms), 2))) if row.p99_latency_ms is not None else None,
                last_hour_requests=last_hour_requests,
                rate_limit_rpm=endpoint.rate_limit_rpm,
                rate_limit_utilization_pct=utilization,
                estimated_total_cost_usd=estimated_total_cost,
                estimated_24h_cost_usd=estimated_24h_cost,
            )
        )
    return GatewayPassThroughEndpointStatsList(items=items)


@router.api_route(
    "/passthrough/{slug}",
    methods=["GET"],
    operation_id="execute_gateway_passthrough_endpoint_root_get",
)
@router.api_route(
    "/passthrough/{slug}",
    methods=["POST"],
    operation_id="execute_gateway_passthrough_endpoint_root_post",
)
@router.api_route(
    "/passthrough/{slug}",
    methods=["PUT"],
    operation_id="execute_gateway_passthrough_endpoint_root_put",
)
@router.api_route(
    "/passthrough/{slug}",
    methods=["PATCH"],
    operation_id="execute_gateway_passthrough_endpoint_root_patch",
)
@router.api_route(
    "/passthrough/{slug}",
    methods=["DELETE"],
    operation_id="execute_gateway_passthrough_endpoint_root_delete",
)
@router.api_route(
    "/passthrough/{slug}/{upstream_path:path}",
    methods=["GET"],
    operation_id="execute_gateway_passthrough_endpoint_path_get",
)
@router.api_route(
    "/passthrough/{slug}/{upstream_path:path}",
    methods=["POST"],
    operation_id="execute_gateway_passthrough_endpoint_path_post",
)
@router.api_route(
    "/passthrough/{slug}/{upstream_path:path}",
    methods=["PUT"],
    operation_id="execute_gateway_passthrough_endpoint_path_put",
)
@router.api_route(
    "/passthrough/{slug}/{upstream_path:path}",
    methods=["PATCH"],
    operation_id="execute_gateway_passthrough_endpoint_path_patch",
)
@router.api_route(
    "/passthrough/{slug}/{upstream_path:path}",
    methods=["DELETE"],
    operation_id="execute_gateway_passthrough_endpoint_path_delete",
)
async def execute_gateway_passthrough_endpoint(
    slug: str,
    request: Request,
    db: DbDep,
    upstream_path: str = "",
) -> Response:
    workspace, api_key = await _resolve_gateway_workspace(request, db)
    await evaluate_ip_acl(
        db,
        workspace_id=workspace.id,
        api_key_id=api_key.id if api_key is not None else None,
        team_name=None,
        client_ip=get_client_ip(
            request.headers.get("x-forwarded-for"),
            request.client.host if request.client else None,
        ),
    )

    stmt = select(GatewayPassThroughEndpoint).where(
        GatewayPassThroughEndpoint.workspace_id == workspace.id,
        GatewayPassThroughEndpoint.slug == slug,
        GatewayPassThroughEndpoint.is_active.is_(True),
    )
    endpoint = (await db.execute(stmt)).scalar_one_or_none()
    if endpoint is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pass-through endpoint not found")

    merged_query = {key: value for key, value in request.query_params.multi_items()}
    target_url = _build_passthrough_target_url(
        endpoint,
        upstream_path=upstream_path,
        query_params=merged_query,
    )

    raw_body = await request.body()
    timeout_seconds = max(1.0, endpoint.timeout_ms / 1000)
    if endpoint.rate_limit_rpm:
        from runledger_api.core.redis import get_redis  # noqa: PLC0415

        redis = await get_redis()
        now = int(time.time())
        bucket = now // 60
        key = f"gateway:passthrough:rpm:{workspace.id}:{endpoint.id}:{bucket}"
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 120)
        if count > endpoint.rate_limit_rpm:
            await record_gateway_request(
                db=db,
                workspace_id=workspace.id,
                model_requested=f"passthrough:{slug}",
                route=None,
                model_used=endpoint.upstream_base_url,
                cache_hit=False,
                input_tokens=None,
                output_tokens=None,
                latency_ms=0,
                req_status="error",
                decision_reason=f"passthrough:{slug}|rate_limited",
                config_fingerprint={
                    "assigned_cost_usd": str(endpoint.cost_per_call_usd or Decimal("0")),
                    "endpoint_slug": slug,
                    "passthrough": True,
                },
                segment_key=slug,
            )
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Pass-through endpoint rate limit exceeded")
    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
            upstream_response = await client.request(
                method=request.method,
                url=target_url,
                content=raw_body if raw_body else None,
                headers=_build_passthrough_headers(endpoint, request),
            )
    except httpx.HTTPError as exc:
        await record_gateway_request(
            db=db,
            workspace_id=workspace.id,
            model_requested=f"passthrough:{slug}",
            route=None,
            model_used=endpoint.upstream_base_url,
            cache_hit=False,
            input_tokens=None,
            output_tokens=None,
            latency_ms=int((time.monotonic() - t0) * 1000),
            req_status="error",
            decision_reason=f"passthrough:{slug}|upstream_error",
            config_fingerprint={
                "assigned_cost_usd": str(endpoint.cost_per_call_usd or Decimal("0")),
                "endpoint_slug": slug,
                "passthrough": True,
            },
            segment_key=slug,
        )
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Upstream request failed: {exc!s}") from exc

    await record_gateway_request(
        db=db,
        workspace_id=workspace.id,
        model_requested=f"passthrough:{slug}",
        route=None,
        model_used=endpoint.upstream_base_url,
        cache_hit=False,
        input_tokens=None,
        output_tokens=None,
        latency_ms=int((time.monotonic() - t0) * 1000),
        req_status="success" if upstream_response.status_code < 400 else "error",
        decision_reason=f"passthrough:{slug}",
        config_fingerprint={
            "assigned_cost_usd": str(endpoint.cost_per_call_usd or Decimal("0")),
            "endpoint_slug": slug,
            "passthrough": True,
            "rate_limit_rpm": endpoint.rate_limit_rpm,
        },
        segment_key=slug,
    )

    response_headers = {
        key: value
        for key, value in upstream_response.headers.items()
        if key.lower() in _PASSTHROUGH_ALLOWED_RESPONSE_HEADERS
    }
    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        headers=response_headers,
        media_type=upstream_response.headers.get("content-type"),
    )


@router.get("/deployments/health", response_model=GatewayDeploymentHealthList)
async def list_gateway_deployment_health(
    auth: OrgAdminDep,
    db: DbDep,
) -> GatewayDeploymentHealthList:
    workspace = auth[0]
    rows = (
        (
            await db.execute(
                select(GatewayRoute)
                .where(GatewayRoute.workspace_id == workspace.id)
                .order_by(GatewayRoute.alias.asc(), GatewayRoute.priority.asc())
            )
        )
        .scalars()
        .all()
    )
    return GatewayDeploymentHealthList(
        items=[
            GatewayDeploymentHealthItem(
                route_id=row.id,
                alias=row.alias,
                provider=row.provider,
                target_model=row.target_model,
                deployment_status=row.deployment_status,
                health_summary=row.health_summary,
                last_health_check_at=row.last_health_check_at,
                consecutive_health_failures=row.consecutive_health_failures,
            )
            for row in rows
        ]
    )


# ── Request log (routing log) ─────────────────────────────────────────────────


@router.get("/requests", response_model=GatewayRequestList)
async def list_gateway_requests(
    auth: OrgAdminDep,
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
    workspace = auth[0]
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
    auth: OrgAdminDep,
    db: DbDep,
) -> GatewayStats:
    """Aggregate gateway request stats per route for the workspace."""
    workspace = auth[0]
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


@router.get("/benchmarks/compare", response_model=GatewayBenchmarkComparisonList)
async def gateway_benchmark_comparison(
    auth: OrgAdminDep,
    db: DbDep,
    days: int = Query(7, ge=1, le=30),
    alias: str | None = Query(default=None),
) -> GatewayBenchmarkComparisonList:
    workspace = auth[0]
    since = datetime.now(UTC) - timedelta(days=days)
    stmt = select(GatewayRequest).where(
        GatewayRequest.workspace_id == workspace.id,
        GatewayRequest.created_at >= since,
        GatewayRequest.status != "cache_hit",
    )
    if alias:
        stmt = stmt.where(GatewayRequest.model_requested == alias)
    items = list((await db.execute(stmt)).scalars().all())
    buckets: dict[str, dict[str, Any]] = {}
    for item in items:
        alias_key = item.model_requested
        bucket = buckets.setdefault(
            alias_key,
            {
                "request_count": 0,
                "provider_latencies": [],
                "end_to_end": [],
                "overheads": [],
                "timestamps": [],
            },
        )
        cfg = item.config_fingerprint or {}
        provider_latency = cfg.get("provider_latency_ms")
        total_wall = cfg.get("total_wall_ms")
        gateway_overhead = cfg.get("gateway_overhead_ms")
        if provider_latency is not None:
            bucket["provider_latencies"].append(float(provider_latency))
        if total_wall is not None:
            bucket["end_to_end"].append(float(total_wall))
        if gateway_overhead is not None:
            bucket["overheads"].append(float(gateway_overhead))
        bucket["request_count"] += 1
        bucket["timestamps"].append(item.created_at)

    def _percentile(values: list[float], q: float) -> Decimal | None:
        if not values:
            return None
        ordered = sorted(values)
        index = min(len(ordered) - 1, max(0, math.ceil(q * len(ordered)) - 1))
        return Decimal(str(round(ordered[index], 2)))

    rows: list[GatewayBenchmarkComparisonItem] = []
    for alias_key, bucket in sorted(buckets.items()):
        timestamps = sorted(bucket["timestamps"])
        minutes = max(((timestamps[-1] - timestamps[0]).total_seconds() / 60.0) if len(timestamps) > 1 else 1.0, 1.0)
        provider_avg = (
            Decimal(str(round(sum(bucket["provider_latencies"]) / len(bucket["provider_latencies"]), 2)))
            if bucket["provider_latencies"]
            else None
        )
        end_to_end_avg = (
            Decimal(str(round(sum(bucket["end_to_end"]) / len(bucket["end_to_end"]), 2)))
            if bucket["end_to_end"]
            else None
        )
        overhead_avg = (
            Decimal(str(round(sum(bucket["overheads"]) / len(bucket["overheads"]), 2)))
            if bucket["overheads"]
            else None
        )
        overhead_pct = None
        if provider_avg is not None and provider_avg > 0 and overhead_avg is not None:
            overhead_pct = Decimal(str(round(float(overhead_avg / provider_avg), 4)))
        rows.append(
            GatewayBenchmarkComparisonItem(
                alias=alias_key,
                request_count=bucket["request_count"],
                throughput_rpm=Decimal(str(round(bucket["request_count"] / minutes, 4))),
                p50_gateway_overhead_ms=_percentile(bucket["overheads"], 0.50),
                p95_gateway_overhead_ms=_percentile(bucket["overheads"], 0.95),
                p99_gateway_overhead_ms=_percentile(bucket["overheads"], 0.99),
                avg_provider_latency_ms=provider_avg,
                avg_end_to_end_latency_ms=end_to_end_avg,
                avg_gateway_overhead_ms=overhead_avg,
                overhead_vs_provider_pct=overhead_pct,
            )
        )
    return GatewayBenchmarkComparisonList(items=rows)
