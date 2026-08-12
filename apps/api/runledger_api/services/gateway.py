"""
Gateway service: cache key generation, route selection, and request forwarding.

Design
------
* Cache key = SHA-256 of JSON({"model": target_model, "messages": [...]}, sort_keys=True)
  Keyed per workspace so tenants can't share each other's cached responses.
* Routes are sorted by priority ASC (lower = higher priority).
* Forward: httpx async POST to provider base_url/chat/completions.
  Retry once on 429 or 5xx before moving to the next route (fallback).
* Fail open: if all routes fail, raise HTTPException 502.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
import random
import time
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.gateway import (
    GatewayRequest,
    GatewayRoute,
    GatewayRoutingGroup,
    PromptCache,
)
from runledger_api.services import kafka_export

log = logging.getLogger(__name__)

# Default prompt cache TTL: 24 hours
_CACHE_TTL_HOURS = 24


def _clone_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [dict(message) for message in messages]


def _normalize_tags(tags: list[str] | None) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for tag in tags or []:
        value = str(tag).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return normalized


async def list_routing_groups_for_alias(
    db: AsyncSession,
    workspace_id: Any,
    alias: str,
) -> list[GatewayRoutingGroup]:
    stmt = (
        select(GatewayRoutingGroup)
        .where(
            GatewayRoutingGroup.workspace_id == workspace_id,
            GatewayRoutingGroup.alias == alias,
            GatewayRoutingGroup.is_active.is_(True),
        )
        .order_by(GatewayRoutingGroup.created_at.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def resolve_request_tags(
    db: AsyncSession,
    workspace_id: Any,
    alias: str,
    request_tags: list[str] | None = None,
) -> list[str]:
    normalized = _normalize_tags(request_tags)
    if normalized:
        return normalized
    groups = await list_routing_groups_for_alias(db, workspace_id, alias)
    default_tags: list[str] = []
    for group in groups:
        default_tags.extend(group.default_tags or [])
    return _normalize_tags(default_tags)


def _matching_group_ids(
    groups: list[GatewayRoutingGroup],
    request_tags: list[str] | None,
) -> set[Any]:
    positive_tags = {tag for tag in _normalize_tags(request_tags) if not tag.startswith("!")}
    if not positive_tags:
        return set()
    matching: set[Any] = set()
    for group in groups:
        required = {tag for tag in (group.match_tags or []) if tag}
        if required and required.issubset(positive_tags):
            matching.add(group.id)
    return matching


def make_cache_key(target_model: str, messages: list[dict[str, Any]]) -> str:
    """Return a 64-char hex SHA-256 of the canonical request body."""
    payload = json.dumps({"model": target_model, "messages": messages}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def _route_timeout_ms(route: GatewayRoute, *, stream: bool) -> int | None:
    cfg = route.config or {}
    key = "stream_timeout_ms" if stream else "completion_timeout_ms"
    value = cfg.get(key) if isinstance(cfg, dict) else None
    if value is not None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return route.timeout_ms
    return route.timeout_ms


def _apply_timeout_override(route: GatewayRoute, *, stream: bool, timeout_ms: int | None) -> tuple[int | None, dict[str, Any] | None]:
    original_timeout = route.timeout_ms
    original_config = dict(route.config) if isinstance(route.config, dict) else None
    if timeout_ms is None:
        return original_timeout, original_config
    cfg = dict(route.config or {})
    cfg["stream_timeout_ms" if stream else "completion_timeout_ms"] = timeout_ms
    route.config = cfg
    route.timeout_ms = timeout_ms if not stream else route.timeout_ms
    return original_timeout, original_config


def _restore_timeout_override(
    route: GatewayRoute,
    original_timeout: int | None,
    original_config: dict[str, Any] | None,
) -> None:
    route.timeout_ms = original_timeout
    route.config = original_config


def _classify_fallback_triggers(exc: Exception) -> set[str]:
    triggers: set[str] = set()
    if isinstance(exc, httpx.TimeoutException):
        triggers.add("timeout")
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        body_text = ""
        try:
            body_text = exc.response.text.lower()
        except Exception:  # noqa: BLE001
            body_text = ""
        if status_code in {400, 403} and any(
            token in body_text for token in ("content policy", "content_filter", "safety", "moderation", "policy")
        ):
            triggers.add("content_policy")
        if status_code in {400, 413} and any(
            token in body_text
            for token in ("context", "maximum context", "context length", "too many tokens", "prompt too long")
        ):
            triggers.add("context_window")
    return triggers


def _apply_prompt_overrides(
    messages: list[dict[str, Any]],
    overrides: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not overrides:
        return messages
    patched = _clone_messages(messages)
    system_message = overrides.get("system_message")
    if isinstance(system_message, str) and system_message.strip():
        patched.insert(0, {"role": "system", "content": system_message.strip()})
    prompt_prefix = overrides.get("prompt_prefix")
    prompt_suffix = overrides.get("prompt_suffix")
    for message in reversed(patched):
        if message.get("role") == "user" and isinstance(message.get("content"), str):
            content = str(message["content"])
            if isinstance(prompt_prefix, str) and prompt_prefix:
                content = f"{prompt_prefix}\n{content}"
            if isinstance(prompt_suffix, str) and prompt_suffix:
                content = f"{content}\n{prompt_suffix}"
            message["content"] = content
            break
    return patched


def _override_value(base: Any, overrides: dict[str, Any] | None, key: str) -> Any:
    if overrides and key in overrides:
        return overrides[key]
    return base


def _response_text(response_json: dict[str, Any]) -> str:
    choices = response_json.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content")
    return content if isinstance(content, str) else ""


def _shadow_similarity(primary_text: str, mirror_text: str) -> float:
    if not primary_text and not mirror_text:
        return 1.0
    primary_tokens = set(primary_text.lower().split())
    mirror_tokens = set(mirror_text.lower().split())
    if not primary_tokens and not mirror_tokens:
        return 1.0
    union = primary_tokens.union(mirror_tokens)
    if not union:
        return 0.0
    return len(primary_tokens.intersection(mirror_tokens)) / len(union)


async def check_cache(db: AsyncSession, workspace_id: Any, cache_key: str) -> PromptCache | None:
    """Return a live (not-expired) cache entry if caching is enabled for workspace."""
    from runledger_api.models.cache_config import ResponseCacheConfig  # noqa: PLC0415

    cfg_stmt = select(ResponseCacheConfig).where(
        ResponseCacheConfig.workspace_id == workspace_id
    ).limit(1)
    cfg = (await db.execute(cfg_stmt)).scalar_one_or_none()
    if cfg and not cfg.is_enabled:
        return None

    now = datetime.now(UTC)
    stmt = select(PromptCache).where(
        PromptCache.workspace_id == workspace_id,
        PromptCache.cache_key == cache_key,
        (PromptCache.expires_at.is_(None)) | (PromptCache.expires_at > now),
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def increment_hit_count(db: AsyncSession, cache_entry: PromptCache) -> None:
    """Bump hit_count without fetching the row again."""
    await db.execute(
        update(PromptCache)
        .where(PromptCache.id == cache_entry.id)
        .values(hit_count=PromptCache.hit_count + 1)
    )
    await db.commit()


async def store_cache(
    db: AsyncSession,
    workspace_id: Any,
    cache_key: str,
    model: str,
    response_json: dict[str, Any],
    prompt_tokens: int | None,
    completion_tokens: int | None,
) -> None:
    """Upsert a prompt cache entry (insert or skip if key already exists)."""
    existing = await check_cache(db, workspace_id, cache_key)
    if existing:
        return  # already cached by a concurrent request

    from runledger_api.models.cache_config import ResponseCacheConfig  # noqa: PLC0415

    cfg_stmt = select(ResponseCacheConfig.ttl_seconds).where(
        ResponseCacheConfig.workspace_id == workspace_id
    ).limit(1)
    ttl = (await db.execute(cfg_stmt)).scalar_one_or_none() or (_CACHE_TTL_HOURS * 3600)

    expires_at = datetime.now(UTC) + timedelta(seconds=int(ttl))
    entry = PromptCache(
        workspace_id=workspace_id,
        cache_key=cache_key,
        model=model,
        response_json=response_json,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        hit_count=0,
        expires_at=expires_at,
    )
    db.add(entry)
    try:
        await db.commit()
    except Exception:
        await db.rollback()


async def select_routes(
    db: AsyncSession,
    workspace_id: Any,
    alias: str,
    request_tags: list[str] | None = None,
    preferred_region: str | None = None,
) -> list[GatewayRoute]:
    """Return active routes for alias ordered by priority ASC."""
    groups = await list_routing_groups_for_alias(db, workspace_id, alias)
    matched_group_ids = _matching_group_ids(groups, request_tags)
    stmt = (
        select(GatewayRoute)
        .where(
            GatewayRoute.workspace_id == workspace_id,
            GatewayRoute.alias == alias,
            GatewayRoute.is_active.is_(True),
        )
        .order_by(GatewayRoute.priority.asc())
    )
    result = await db.execute(stmt)
    routes = list(result.scalars().all())
    if matched_group_ids:
        routes = [route for route in routes if route.routing_group_id in matched_group_ids]
    filtered = routes
    if request_tags:
        tag_set = set(request_tags)
        filtered = []
        for route in routes:
            required = set(route.required_tags or [])
            excluded = set(route.excluded_tags or [])
            dynamic_excluded = {tag[1:] for tag in tag_set if tag.startswith("!")}
            if required and not required.issubset({tag for tag in tag_set if not tag.startswith("!")}):
                continue
            if excluded and (excluded.intersection(tag_set) or excluded.intersection(dynamic_excluded)):
                continue
            filtered.append(route)
    if preferred_region:
        region_matches = [
            route for route in filtered if (route.region or "").lower() == preferred_region.lower()
        ]
        if region_matches:
            remainder = [route for route in filtered if route not in region_matches]
            return region_matches + remainder
    return filtered


async def _rank_routes_by_region_latency(
    db: AsyncSession,
    workspace_id: Any,
    routes: list[GatewayRoute],
) -> list[GatewayRoute]:
    region_routes = [route for route in routes if route.region]
    if len(region_routes) < 2:
        return routes
    rows = await db.execute(
        select(
            GatewayRoute.region,
            func.avg(GatewayRequest.latency_ms).label("avg_latency"),
        )
        .select_from(GatewayRequest)
        .join(GatewayRoute, GatewayRequest.route_id == GatewayRoute.id)
        .where(
            GatewayRequest.workspace_id == workspace_id,
            GatewayRoute.id.in_([route.id for route in region_routes]),
            GatewayRequest.latency_ms.is_not(None),
            GatewayRequest.created_at >= datetime.now(UTC) - timedelta(hours=24),
        )
        .group_by(GatewayRoute.region)
    )
    latency_map = {
        str(row.region).lower(): float(row.avg_latency)
        for row in rows.all()
        if row.region and row.avg_latency is not None
    }
    if not latency_map:
        return routes
    ranked = sorted(
        routes,
        key=lambda route: (
            latency_map.get((route.region or "").lower(), float("inf")),
            route.priority,
        ),
    )
    return ranked


async def choose_route_for_alias(
    db: AsyncSession,
    workspace_id: Any,
    alias: str,
    messages: list[dict[str, Any]],
    request_tags: list[str] | None = None,
    preferred_region: str | None = None,
) -> tuple[GatewayRoute | None, str]:
    """
    Return the best route and decision reason for an alias.

    Uses the routing policy engine when available, then filters the result through
    tag/region/active state checks. Falls back to plain route ordering if a policy
    candidate is unavailable after filtering.
    """
    from runledger_api.services.routing import select_route_with_policy  # noqa: PLC0415

    filtered = await select_routes(
        db,
        workspace_id,
        alias,
        request_tags=request_tags,
        preferred_region=preferred_region,
    )
    if not filtered:
        from runledger_api.models.projects import TeamModel  # noqa: PLC0415
        tm_stmt = select(TeamModel).where(
            TeamModel.workspace_id == workspace_id,
            sa.or_(TeamModel.model_name == alias, TeamModel.team_name == alias),
        ).limit(1)
        tm = (await db.execute(tm_stmt)).scalar_one_or_none()
        if tm and tm.api_base_url:
            dynamic_route = GatewayRoute(
                id=tm.id,
                workspace_id=workspace_id,
                alias=tm.model_name,
                target_model=tm.model_name,
                provider=tm.provider or "custom",
                endpoint_url=tm.api_base_url,
                is_active=True,
            )
            return dynamic_route, f"team_model:{tm.team_name}"
        return None, "no-routes"

    groups = await list_routing_groups_for_alias(db, workspace_id, alias)
    group_map = {group.id: group for group in groups}
    top_group = group_map.get(filtered[0].routing_group_id) if filtered else None
    latency_region_ranked = await _rank_routes_by_region_latency(db, workspace_id, filtered)
    if preferred_region:
        preferred_matches = [
            route for route in filtered if (route.region or "").lower() == preferred_region.lower()
        ]
        if not preferred_matches and latency_region_ranked:
            fallback_route = latency_region_ranked[0]
            return fallback_route, (
                f"cross_region_fallback:{preferred_region}->{fallback_route.region or 'default'}|priority"
            )
    elif latency_region_ranked and latency_region_ranked[0].region and latency_region_ranked != filtered:
        filtered = latency_region_ranked
    if top_group and top_group.strategy_type == "latency_optimized":
        route_ids = [route.id for route in filtered if route.routing_group_id == top_group.id]
        if route_ids:
            stats_stmt = (
                select(
                    GatewayRequest.route_id,
                    func.avg(GatewayRequest.latency_ms).label("avg_latency"),
                )
                .where(
                    GatewayRequest.workspace_id == workspace_id,
                    GatewayRequest.route_id.in_(route_ids),
                    GatewayRequest.latency_ms.is_not(None),
                )
                .group_by(GatewayRequest.route_id)
            )
            stats_result = await db.execute(stats_stmt)
            latency_map = {
                row.route_id: float(row.avg_latency) for row in stats_result.all() if row.avg_latency is not None
            }
            if latency_map:
                ranked = sorted(
                    [route for route in filtered if route.id in latency_map],
                    key=lambda route: (latency_map[route.id], route.priority),
                )
                if ranked:
                    return ranked[0], f"routing_group:{top_group.name}|latency_optimized"
    if top_group and top_group.strategy_type == "round_robin":
        group_routes = [route for route in filtered if route.routing_group_id == top_group.id]
        if group_routes:
            selected = random.choice(group_routes)
            return selected, f"routing_group:{top_group.name}|round_robin"

    try:
        policy_route, decision_reason = await select_route_with_policy(
            db,
            workspace_id,
            alias,
            messages,
        )
        if any(route.id == policy_route.id for route in filtered):
            return policy_route, decision_reason
    except Exception:  # noqa: BLE001
        log.exception("gateway_policy_selection_failed alias=%s", alias)

    fallback = filtered[0]
    reason = "priority"
    if top_group:
        reason = f"routing_group:{top_group.name}|{top_group.strategy_type}|{reason}"
    if preferred_region and fallback.region and fallback.region.lower() == preferred_region.lower():
        reason = f"region_preferred:{preferred_region}|priority"
    return fallback, reason


def _build_payload(
    route: GatewayRoute,
    messages: list[dict[str, Any]],
    temperature: float | None,
    max_tokens: int | None,
    top_p: float | None = None,
    frequency_penalty: float | None = None,
    presence_penalty: float | None = None,
    seed: int | None = None,
    stop: str | list[str] | None = None,
    response_format: dict[str, Any] | None = None,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str | dict[str, Any] | None = None,
    stream: bool = False,
) -> dict[str, Any]:
    """Build the provider-bound JSON payload, omitting None fields."""
    payload: dict[str, Any] = {
        "model": route.target_model,
        "messages": messages,
    }
    optional = {
        "temperature": temperature,
        "max_tokens": max_tokens,
        "top_p": top_p,
        "frequency_penalty": frequency_penalty,
        "presence_penalty": presence_penalty,
        "seed": seed,
        "stop": stop,
        "response_format": response_format,
        "tools": tools,
        "tool_choice": tool_choice,
    }
    for k, v in optional.items():
        if v is not None:
            payload[k] = v
    if stream:
        payload["stream"] = True
    return payload


async def forward_request(
    route: GatewayRoute,
    messages: list[dict[str, Any]],
    temperature: float | None,
    max_tokens: int | None,
    top_p: float | None = None,
    frequency_penalty: float | None = None,
    presence_penalty: float | None = None,
    seed: int | None = None,
    stop: str | list[str] | None = None,
    response_format: dict[str, Any] | None = None,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str | dict[str, Any] | None = None,
    reasoning_effort: str | None = None,
) -> dict[str, Any]:
    """
    Forward the completion request to the provider (non-streaming).

    Returns the raw provider JSON response dict.
    Raises httpx.HTTPStatusError on 4xx/5xx from the provider.
    Dispatches to the appropriate provider adapter based on route.provider.
    """
    from runledger_api.services.gateway_providers import get_adapter  # noqa: PLC0415

    adapter = get_adapter(route.provider)
    return await adapter.forward(
        route,
        messages,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        frequency_penalty=frequency_penalty,
        presence_penalty=presence_penalty,
        seed=seed,
        stop=stop,
        response_format=response_format,
        tools=tools,
        tool_choice=tool_choice,
        reasoning_effort=reasoning_effort,
    )


async def stream_request(
    route: GatewayRoute,
    messages: list[dict[str, Any]],
    temperature: float | None,
    max_tokens: int | None,
    top_p: float | None = None,
    frequency_penalty: float | None = None,
    presence_penalty: float | None = None,
    seed: int | None = None,
    stop: str | list[str] | None = None,
    response_format: dict[str, Any] | None = None,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str | dict[str, Any] | None = None,
    reasoning_effort: str | None = None,
    timeout_override_ms: int | None = None,
) -> AsyncGenerator[bytes]:
    """
    Stream SSE chunks from the provider, yielding raw bytes lines.

    Yields each b"data: ..." line verbatim so the caller can stream them
    directly to the client as a Server-Sent Events response.
    Dispatches to the appropriate provider adapter based on route.provider.
    """
    from runledger_api.services.gateway_providers import get_adapter  # noqa: PLC0415

    adapter = get_adapter(route.provider)
    original_timeout, original_config = _apply_timeout_override(
        route,
        stream=True,
        timeout_ms=timeout_override_ms,
    )
    try:
        async for chunk in adapter.stream(
            route,
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            seed=seed,
            stop=stop,
            response_format=response_format,
            tools=tools,
            tool_choice=tool_choice,
            reasoning_effort=reasoning_effort,
        ):
            yield chunk
    finally:
        _restore_timeout_override(route, original_timeout, original_config)


async def record_gateway_request(
    db: AsyncSession,
    workspace_id: Any,
    model_requested: str,
    route: GatewayRoute | None,
    model_used: str | None,
    cache_hit: bool,
    input_tokens: int | None,
    output_tokens: int | None,
    latency_ms: int | None,
    req_status: str,
    decision_reason: str | None = None,
    config_fingerprint: dict[str, Any] | None = None,
    segment_key: str | None = None,
) -> None:
    """Insert a GatewayRequest log entry."""
    entry = GatewayRequest(
        workspace_id=workspace_id,
        route_id=route.id if route else None,
        model_requested=model_requested,
        model_used=model_used,
        cache_hit=cache_hit,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
        status=req_status,
        decision_reason=decision_reason,
        config_fingerprint=config_fingerprint,
        segment_key=segment_key,
    )
    db.add(entry)
    await db.flush()
    kafka_event_type = "gateway.request.completed" if req_status in {"success", "cache_hit"} else "gateway.request.rejected"
    try:
        await kafka_export.publish_event(
            db,
            workspace_id=workspace_id,
            event_type=kafka_event_type,
            payload={
                "run_id": str(entry.id),
                "gateway_request_id": str(entry.id),
                "route_id": str(route.id) if route else None,
                "model_requested": model_requested,
                "model_used": model_used,
                "cache_hit": cache_hit,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "latency_ms": latency_ms,
                "status": req_status,
                "decision_reason": decision_reason,
                "source": "runledger.gateway",
                "event_summary": f"Gateway request {req_status}",
                "idempotency_key": f"gateway-request:{entry.id}:{req_status}",
            },
        )
        if route is not None and (
            route.target_model != model_requested
            or route.alias != model_requested
            or (decision_reason and "fallback" in decision_reason)
        ):
            await kafka_export.publish_event(
                db,
                workspace_id=workspace_id,
                event_type="route.changed",
                payload={
                    "run_id": str(entry.id),
                    "gateway_request_id": str(entry.id),
                    "route_id": str(route.id),
                    "requested_alias": model_requested,
                    "selected_alias": route.alias,
                    "selected_model": route.target_model,
                    "decision_reason": decision_reason,
                    "source": "runledger.gateway",
                    "event_summary": "Gateway route changed",
                    "idempotency_key": f"route-changed:{entry.id}:{route.id}",
                },
            )
    except Exception:
        log.exception("kafka_export.gateway_request_failed", gateway_request_id=str(entry.id))
    await db.commit()


async def route_and_forward(
    db: AsyncSession,
    workspace_id: Any,
    model_alias: str,
    messages: list[dict[str, Any]],
    temperature: float | None,
    max_tokens: int | None,
    top_p: float | None = None,
    frequency_penalty: float | None = None,
    presence_penalty: float | None = None,
    seed: int | None = None,
    stop: str | list[str] | None = None,
    response_format: dict[str, Any] | None = None,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str | dict[str, Any] | None = None,
    reasoning_effort: str | None = None,
    request_tags: list[str] | None = None,
    fallback_aliases: list[str] | None = None,
    preferred_region: str | None = None,
    timeout_override_ms: int | None = None,
) -> tuple[dict[str, Any], GatewayRoute, int, str]:
    """
    Select route by priority, then forward to the provider.
    Retries once on transient errors, then falls back to next priority route.
    Returns (response_json, winning_route, latency_ms, decision_reason).
    Raises HTTPException 502 when all routes fail.
    """
    primary_route, primary_reason = await choose_route_for_alias(
        db,
        workspace_id,
        model_alias,
        messages,
        request_tags=request_tags,
        preferred_region=preferred_region,
    )
    candidate_routes = await select_routes(
        db,
        workspace_id,
        model_alias,
        request_tags=request_tags,
        preferred_region=preferred_region,
    )
    if not candidate_routes or primary_route is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"No active gateway routes configured for alias '{model_alias}'",
        )
    decision_reason = primary_reason

    queue: list[dict[str, Any]] = [{"alias": model_alias, "rule": None, "trigger": "primary"}]
    visited_aliases = {model_alias}
    first_fallback_cfg = primary_route.fallback_config or {}
    fallback_rules = []
    if isinstance(first_fallback_cfg, dict):
        fallback_rules = [
            rule for rule in first_fallback_cfg.get("fallbacks", [])
            if isinstance(rule, dict) and isinstance(rule.get("alias"), str) and rule.get("alias")
        ]
    for alias in first_fallback_cfg.get("aliases", []) if isinstance(first_fallback_cfg, dict) else []:
        if isinstance(alias, str) and alias and alias not in visited_aliases:
            queue.append({"alias": alias, "rule": None, "trigger": "configured"})
            visited_aliases.add(alias)
    for alias in fallback_aliases or []:
        if isinstance(alias, str) and alias and alias not in visited_aliases:
            queue.append({"alias": alias, "rule": None, "trigger": "request"})
            visited_aliases.add(alias)

    last_error: Exception | None = None
    queue_index = 0
    while queue_index < len(queue):
        step = queue[queue_index]
        queue_index += 1
        alias_to_try = str(step["alias"])
        rule = step.get("rule") if isinstance(step.get("rule"), dict) else None
        trigger = str(step.get("trigger") or "fallback")
        step_messages = _apply_prompt_overrides(messages, rule)
        step_temperature = _override_value(temperature, rule, "temperature")
        step_max_tokens = _override_value(max_tokens, rule, "max_tokens")
        step_top_p = _override_value(top_p, rule, "top_p")
        step_frequency_penalty = _override_value(frequency_penalty, rule, "frequency_penalty")
        step_presence_penalty = _override_value(presence_penalty, rule, "presence_penalty")
        step_seed = _override_value(seed, rule, "seed")
        step_stop = _override_value(stop, rule, "stop")
        step_response_format = _override_value(response_format, rule, "response_format")
        step_tools = _override_value(tools, rule, "tools")
        step_tool_choice = _override_value(tool_choice, rule, "tool_choice")
        step_reasoning_effort = _override_value(reasoning_effort, rule, "reasoning_effort")
        completion_timeout_override = timeout_override_ms
        if rule and rule.get("completion_timeout_ms") is not None:
            completion_timeout_override = int(rule["completion_timeout_ms"])
        selected_route, selected_reason = await choose_route_for_alias(
            db,
            workspace_id,
            alias_to_try,
            step_messages,
            request_tags=request_tags,
            preferred_region=preferred_region,
        )
        routes_for_alias = (
            candidate_routes
            if alias_to_try == model_alias
            else await select_routes(
                db,
                workspace_id,
                alias_to_try,
                request_tags,
                preferred_region=preferred_region,
            )
        )
        if not routes_for_alias or selected_route is None:
            continue
        ordered_routes = [selected_route] + [route for route in routes_for_alias if route.id != selected_route.id]
        for route in ordered_routes:
            if route.cooldown_until is not None and route.cooldown_until > datetime.now(UTC):
                continue
            max_attempts = max(1, (route.retry_count or 0) + 1)
            for attempt in range(1, max_attempts + 1):
                t0 = time.monotonic()
                try:
                    original_timeout, original_config = _apply_timeout_override(
                        route,
                        stream=False,
                        timeout_ms=completion_timeout_override,
                    )
                    response = await forward_request(
                        route=route,
                        messages=step_messages,
                        temperature=step_temperature,
                        max_tokens=step_max_tokens,
                        top_p=step_top_p,
                        frequency_penalty=step_frequency_penalty,
                        presence_penalty=step_presence_penalty,
                        seed=step_seed,
                        stop=step_stop,
                        response_format=step_response_format,
                        tools=step_tools,
                        tool_choice=step_tool_choice,
                        reasoning_effort=step_reasoning_effort,
                    )
                    _restore_timeout_override(route, original_timeout, original_config)
                    latency_ms = int((time.monotonic() - t0) * 1000)
                    route.last_health_check_at = datetime.now(UTC)
                    route.consecutive_health_failures = 0
                    route.disabled_reason = None
                    route.cooldown_until = None
                    await db.commit()
                    mirror_cfg = route.mirror_config or {}
                    mirror_alias = mirror_cfg.get("alias") if isinstance(mirror_cfg, dict) else None
                    mirror_pct = float(mirror_cfg.get("sample_pct", 0)) if isinstance(mirror_cfg, dict) and mirror_cfg.get("sample_pct") is not None else 0.0
                    if mirror_alias and mirror_pct > 0:
                        sampled = random.random() < mirror_pct
                        mirror_route, _mirror_reason = await choose_route_for_alias(
                            db,
                            workspace_id,
                            str(mirror_alias),
                            step_messages,
                            request_tags=request_tags,
                            preferred_region=preferred_region,
                        ) if sampled else (None, "mirror_skipped")
                        if mirror_route is not None:
                            mirror_success = False
                            mirror_decision_reason = f"mirror:{route.alias}->{mirror_alias}"
                            try:
                                mirror_started = time.monotonic()
                                mirror_response = await forward_request(
                                    route=mirror_route,
                                    messages=step_messages,
                                    temperature=step_temperature,
                                    max_tokens=step_max_tokens,
                                    top_p=step_top_p,
                                    frequency_penalty=step_frequency_penalty,
                                    presence_penalty=step_presence_penalty,
                                    seed=step_seed,
                                    stop=step_stop,
                                    response_format=step_response_format,
                                    tools=step_tools,
                                    tool_choice=step_tool_choice,
                                    reasoning_effort=step_reasoning_effort,
                                )
                                mirror_success = True
                                similarity = _shadow_similarity(
                                    _response_text(response),
                                    _response_text(mirror_response),
                                )
                                mirror_decision_reason = (
                                    f"{mirror_decision_reason}|shadow_compare:{similarity:.3f}"
                                )
                                mirror_usage = mirror_response.get("usage") or {}
                                await record_gateway_request(
                                    db=db,
                                    workspace_id=workspace_id,
                                    model_requested=f"mirror:{model_alias}",
                                    route=mirror_route,
                                    model_used=mirror_route.target_model,
                                    cache_hit=False,
                                    input_tokens=mirror_usage.get("prompt_tokens"),
                                    output_tokens=mirror_usage.get("completion_tokens"),
                                    latency_ms=int((time.monotonic() - mirror_started) * 1000),
                                    req_status="success",
                                    decision_reason=mirror_decision_reason,
                                )
                            except Exception as mirror_exc:  # noqa: BLE001
                                log.warning("gateway_mirror_failed route_id=%s error=%s", str(route.id), str(mirror_exc))
                                await record_gateway_request(
                                    db=db,
                                    workspace_id=workspace_id,
                                    model_requested=f"mirror:{model_alias}",
                                    route=mirror_route,
                                    model_used=mirror_route.target_model,
                                    cache_hit=False,
                                    input_tokens=None,
                                    output_tokens=None,
                                    latency_ms=None,
                                    req_status="error",
                                    decision_reason=f"{mirror_decision_reason}|shadow_error",
                                )
                            if mirror_success:
                                decision_reason = f"{selected_reason}|shadow_compared"
                    if alias_to_try != model_alias:
                        decision_reason = (
                            f"fallback_chain:{model_alias}->{alias_to_try}"
                            f"|trigger:{trigger}|{selected_reason}"
                        )
                    else:
                        decision_reason = decision_reason if "shadow_compared" in decision_reason else selected_reason
                    return response, route, latency_ms, decision_reason
                except httpx.HTTPStatusError as exc:
                    _restore_timeout_override(route, original_timeout, original_config)
                    last_error = exc
                    status_code = exc.response.status_code
                    transient = status_code in (429, 500, 502, 503, 504)
                    matched_triggers = _classify_fallback_triggers(exc)
                    for fallback_rule in fallback_rules:
                        rule_triggers = {
                            str(item).strip()
                            for item in fallback_rule.get("on", [])
                            if str(item).strip()
                        }
                        if matched_triggers.intersection(rule_triggers):
                            rule_alias = str(fallback_rule.get("alias") or "").strip()
                            if rule_alias and rule_alias not in visited_aliases:
                                queue.append(
                                    {
                                        "alias": rule_alias,
                                        "rule": fallback_rule,
                                        "trigger": ",".join(sorted(matched_triggers)),
                                    }
                                )
                                visited_aliases.add(rule_alias)
                    if not transient:
                        raise HTTPException(
                            status_code=status.HTTP_502_BAD_GATEWAY,
                            detail=f"Provider returned {status_code}",
                        ) from exc
                    log.warning(
                        "gateway_route_failed route_id=%s provider=%s status_code=%s attempt=%s",
                        str(route.id),
                        route.provider,
                        status_code,
                        attempt,
                    )
                    route.last_health_check_at = datetime.now(UTC)
                    route.consecutive_health_failures = (route.consecutive_health_failures or 0) + 1
                    if route.cooldown_seconds:
                        route.cooldown_until = datetime.now(UTC) + timedelta(seconds=route.cooldown_seconds)
                    route.disabled_reason = f"Transient provider error {status_code}"
                    await db.commit()
                    if attempt < max_attempts:
                        backoff = min(4.0, 0.35 * (2 ** (attempt - 1))) + random.uniform(0.0, 0.2)
                        await asyncio.sleep(backoff)
                        continue
                except Exception as exc:  # noqa: BLE001
                    _restore_timeout_override(route, original_timeout, original_config)
                    last_error = exc
                    matched_triggers = _classify_fallback_triggers(exc)
                    for fallback_rule in fallback_rules:
                        rule_triggers = {
                            str(item).strip()
                            for item in fallback_rule.get("on", [])
                            if str(item).strip()
                        }
                        if matched_triggers.intersection(rule_triggers):
                            rule_alias = str(fallback_rule.get("alias") or "").strip()
                            if rule_alias and rule_alias not in visited_aliases:
                                queue.append(
                                    {
                                        "alias": rule_alias,
                                        "rule": fallback_rule,
                                        "trigger": ",".join(sorted(matched_triggers)),
                                    }
                                )
                                visited_aliases.add(rule_alias)
                    log.warning(
                        "gateway_route_error route_id=%s error=%s attempt=%s",
                        str(route.id),
                        str(exc),
                        attempt,
                    )
                    route.last_health_check_at = datetime.now(UTC)
                    route.consecutive_health_failures = (route.consecutive_health_failures or 0) + 1
                    if route.cooldown_seconds:
                        route.cooldown_until = datetime.now(UTC) + timedelta(seconds=route.cooldown_seconds)
                    route.disabled_reason = str(exc)
                    await db.commit()
                    if attempt < max_attempts:
                        backoff = min(4.0, 0.35 * (2 ** (attempt - 1))) + random.uniform(0.0, 0.2)
                        await asyncio.sleep(backoff)
                        continue
                break

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"All gateway routes failed: {last_error}",
    )
