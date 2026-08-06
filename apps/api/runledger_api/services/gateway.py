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
import random
import time
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.gateway import GatewayRequest, GatewayRoute, PromptCache

log = logging.getLogger(__name__)

# Default prompt cache TTL: 24 hours
_CACHE_TTL_HOURS = 24


def make_cache_key(target_model: str, messages: list[dict[str, Any]]) -> str:
    """Return a 64-char hex SHA-256 of the canonical request body."""
    payload = json.dumps({"model": target_model, "messages": messages}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


async def check_cache(db: AsyncSession, workspace_id: Any, cache_key: str) -> PromptCache | None:
    """Return a live (not-expired) cache entry, or None."""
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

    expires_at = datetime.now(UTC) + timedelta(hours=_CACHE_TTL_HOURS)
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
        await db.rollback()  # duplicate key from concurrent insert — safe to ignore


async def select_routes(
    db: AsyncSession,
    workspace_id: Any,
    alias: str,
    request_tags: list[str] | None = None,
    preferred_region: str | None = None,
) -> list[GatewayRoute]:
    """Return active routes for alias ordered by priority ASC."""
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
        return None, "no-routes"

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
) -> AsyncGenerator[bytes]:
    """
    Stream SSE chunks from the provider, yielding raw bytes lines.

    Yields each b"data: ..." line verbatim so the caller can stream them
    directly to the client as a Server-Sent Events response.
    Dispatches to the appropriate provider adapter based on route.provider.
    """
    from runledger_api.services.gateway_providers import get_adapter  # noqa: PLC0415

    adapter = get_adapter(route.provider)
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

    aliases_to_try: list[str] = [model_alias]
    visited_aliases = {model_alias}
    first_fallback_cfg = primary_route.fallback_config or {}
    for alias in first_fallback_cfg.get("aliases", []) if isinstance(first_fallback_cfg, dict) else []:
        if isinstance(alias, str) and alias and alias not in visited_aliases:
            aliases_to_try.append(alias)
            visited_aliases.add(alias)
    for alias in fallback_aliases or []:
        if isinstance(alias, str) and alias and alias not in visited_aliases:
            aliases_to_try.append(alias)
            visited_aliases.add(alias)

    last_error: Exception | None = None
    for alias_index, alias_to_try in enumerate(aliases_to_try):
        selected_route, selected_reason = await choose_route_for_alias(
            db,
            workspace_id,
            alias_to_try,
            messages,
            request_tags=request_tags,
            preferred_region=preferred_region,
        )
        routes_for_alias = (
            candidate_routes
            if alias_index == 0
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
                    original_timeout = route.timeout_ms
                    if timeout_override_ms is not None:
                        route.timeout_ms = timeout_override_ms
                    response = await forward_request(
                        route=route,
                        messages=messages,
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
                    route.timeout_ms = original_timeout
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
                            messages,
                            request_tags=request_tags,
                            preferred_region=preferred_region,
                        ) if sampled else (None, "mirror_skipped")
                        async def _mirror() -> None:
                            try:
                                if mirror_route is None:
                                    return
                                await forward_request(
                                    route=mirror_route,
                                    messages=messages,
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
                            except Exception:
                                return
                        asyncio.create_task(_mirror())
                    if alias_index > 0:
                        decision_reason = f"fallback_chain:{model_alias}->{alias_to_try}|{selected_reason}"
                    else:
                        decision_reason = selected_reason
                    return response, route, latency_ms, decision_reason
                except httpx.HTTPStatusError as exc:
                    route.timeout_ms = original_timeout
                    last_error = exc
                    status_code = exc.response.status_code
                    transient = status_code in (429, 500, 502, 503, 504)
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
                    route.timeout_ms = original_timeout
                    last_error = exc
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
