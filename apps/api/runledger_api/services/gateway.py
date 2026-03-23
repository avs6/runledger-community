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

import hashlib
import json
import logging
import os
import time
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


def make_cache_key(target_model: str, messages: list[dict[str, str]]) -> str:
    """Return a 64-char hex SHA-256 of the canonical request body."""
    payload = json.dumps({"model": target_model, "messages": messages}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


async def check_cache(
    db: AsyncSession, workspace_id: Any, cache_key: str
) -> PromptCache | None:
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
    db: AsyncSession, workspace_id: Any, alias: str
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
    return list(result.scalars().all())


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
) -> dict[str, Any]:
    """
    Forward the completion request to the provider (non-streaming).

    Returns the raw provider JSON response dict.
    Raises httpx.HTTPStatusError on 4xx/5xx from the provider.
    """
    # Resolve API key: env var lookup → fallback OPENAI_API_KEY → placeholder
    # A placeholder ("none") is used for local providers (Ollama) that don't
    # validate the key but still require a non-empty Authorization header.
    if route.api_key_env_var:
        api_key = os.getenv(route.api_key_env_var, "none")
    else:
        api_key = os.getenv("OPENAI_API_KEY", "none") or "none"
    base_url = (route.base_url or "https://api.openai.com/v1").rstrip("/")

    payload = _build_payload(
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
    )

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]


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
):  # type: ignore[return]
    """
    Stream SSE chunks from the provider, yielding raw bytes lines.

    Yields each b"data: ..." line verbatim so the caller can stream them
    directly to the client as a Server-Sent Events response.
    """
    if route.api_key_env_var:
        api_key = os.getenv(route.api_key_env_var, "none")
    else:
        api_key = os.getenv("OPENAI_API_KEY", "none") or "none"
    base_url = (route.base_url or "https://api.openai.com/v1").rstrip("/")

    payload = _build_payload(
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
        stream=True,
    )

    async with httpx.AsyncClient(timeout=300.0) as client, client.stream(
        "POST",
        f"{base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
    ) as resp:
        resp.raise_for_status()
        async for line in resp.aiter_lines():
            if line:
                yield (line + "\n\n").encode()


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
) -> tuple[dict[str, Any], GatewayRoute, int, str]:
    """
    Apply routing policy, then forward to the selected route.
    Retries once on transient errors, then falls back to next priority route.
    Returns (response_json, winning_route, latency_ms, decision_reason).
    Raises HTTPException 502 when all routes fail.
    """
    from runledger_api.services.routing import select_route_with_policy

    try:
        selected_route, decision_reason = await select_route_with_policy(
            db, workspace_id, model_alias, messages  # type: ignore[arg-type]
        )
        # Policy selected a single route; still fall back to priority order on failure
        candidate_routes = [selected_route]
        # Append remaining priority-order routes as fallbacks
        all_routes = await select_routes(db, workspace_id, model_alias)
        for r in all_routes:
            if r.id != selected_route.id:
                candidate_routes.append(r)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"No active gateway routes configured for alias '{model_alias}'",
        ) from None

    last_error: Exception | None = None
    for route in candidate_routes:
        for attempt in (1, 2):
            t0 = time.monotonic()
            try:
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
                )
                latency_ms = int((time.monotonic() - t0) * 1000)
                return response, route, latency_ms, decision_reason
            except httpx.HTTPStatusError as exc:
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
                if attempt == 1:
                    continue
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                log.warning(
                    "gateway_route_error route_id=%s error=%s attempt=%s",
                    str(route.id),
                    str(exc),
                    attempt,
                )
                if attempt == 1:
                    continue
            break

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"All gateway routes failed: {last_error}",
    )
