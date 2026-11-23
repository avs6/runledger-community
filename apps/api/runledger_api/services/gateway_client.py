"""
In-cluster client for the RunLedger gateway runtime (gateway-rs).

Build features (Playground, experiments, the LLM judge) send their model calls
through the same gateway path as production traffic, so every call gets
preflight governance (budgets, guardrails, RPM), routing, metering and a recorded
run. Nothing here talks to a provider directly (review B-08, B-09, B-10).

The gateway authenticates with a RunLedger API key. Interactive callers forward
their own bearer token; the background judge uses a key stored as a secret ref on
the evaluator (see ``services/evaluators.py``).
"""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.events import AgentRun
from runledger_api.models.gateway import GatewayRoute

DEFAULT_TIMEOUT_S = 120.0


def gateway_base_url() -> str:
    """gateway-rs base URL (``GATEWAY_RS_URL``; docker-compose sets it for the API)."""
    return os.environ.get("GATEWAY_RS_URL", "http://localhost:8210").rstrip("/")


@dataclass
class GatewayCallResult:
    """Outcome of one chat completion sent through the gateway."""

    ok: bool
    status_code: int
    model: str
    request_ref: str
    text: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    error: str | None = None
    response_id: str | None = None
    cache: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)
    run_id: uuid.UUID | None = None
    cost_usd: Decimal | None = None


def _detail(payload: Any, fallback: str) -> str:
    if isinstance(payload, dict):
        detail = payload.get("detail") or payload.get("error")
        if isinstance(detail, dict):
            detail = detail.get("message") or str(detail)
        if detail:
            return str(detail)[:500]
    return fallback[:500]


def _message_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices or not isinstance(choices[0], dict):
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, list):  # content parts
        return "".join(str(p.get("text", "")) for p in content if isinstance(p, dict))
    return str(content or "")


async def chat_completion(
    authorization: str,
    *,
    model: str,
    messages: list[dict[str, Any]],
    params: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    tags: list[str] | None = None,
    end_user_id: str | None = None,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    client: httpx.AsyncClient | None = None,
) -> GatewayCallResult:
    """POST one non-streaming completion to ``/gateway/chat/completions``.

    ``metadata`` lands on the recorded run (``feature_tag``, ``deployment_version``…);
    a ``runledger.request_ref`` is added so the caller can find the run afterwards.
    Never raises for HTTP or transport errors: the result carries ``ok=False``.
    """
    request_ref = str(uuid.uuid4())
    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
        **{k: v for k, v in (params or {}).items() if v is not None},
        "metadata": {**(metadata or {}), "runledger.request_ref": request_ref},
    }
    headers = {"Authorization": authorization, "Content-Type": "application/json"}
    if tags:
        headers["X-RunLedger-Tags"] = ",".join(tags)
    if end_user_id:
        headers["X-RunLedger-End-User-Id"] = end_user_id

    url = f"{gateway_base_url()}/gateway/chat/completions"
    started = time.monotonic()
    own_client = client is None
    http = client or httpx.AsyncClient(timeout=timeout_s)
    try:
        resp = await http.post(url, json=body, headers=headers)
    except httpx.HTTPError as exc:
        return GatewayCallResult(
            ok=False,
            status_code=503,
            model=model,
            request_ref=request_ref,
            latency_ms=int((time.monotonic() - started) * 1000),
            error=f"Gateway unreachable at {gateway_base_url()}: {exc.__class__.__name__}",
        )
    finally:
        if own_client:
            await http.aclose()
    latency_ms = int((time.monotonic() - started) * 1000)
    try:
        payload: Any = resp.json()
    except ValueError:
        payload = {}
    if resp.status_code >= 400 or not isinstance(payload, dict):
        return GatewayCallResult(
            ok=False,
            status_code=resp.status_code,
            model=model,
            request_ref=request_ref,
            latency_ms=latency_ms,
            error=_detail(payload, resp.text or f"Gateway returned {resp.status_code}"),
        )
    usage = payload.get("usage") or {}
    return GatewayCallResult(
        ok=True,
        status_code=resp.status_code,
        model=str(payload.get("model") or model),
        request_ref=request_ref,
        text=_message_text(payload),
        input_tokens=int(usage.get("prompt_tokens") or 0),
        output_tokens=int(usage.get("completion_tokens") or 0),
        latency_ms=latency_ms,
        response_id=payload.get("id"),
        cache=resp.headers.get("x-runledger-cache"),
        raw=payload,
    )


async def attach_run(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    result: GatewayCallResult,
    *,
    attempts: int = 3,
    delay_s: float = 0.2,
) -> GatewayCallResult:
    """Fill ``run_id`` and ``cost_usd`` from the run the gateway recorded for this call."""
    if not result.ok:
        return result
    for attempt in range(attempts):
        run = (
            await db.execute(
                select(AgentRun)
                .where(
                    AgentRun.workspace_id == workspace_id,
                    AgentRun.run_metadata["runledger.request_ref"].astext == result.request_ref,
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if run is not None:
            result.run_id = run.id
            result.cost_usd = run.total_cost_usd
            return result
        if attempt < attempts - 1:
            await asyncio.sleep(delay_s)
    return result


async def list_route_aliases(db: AsyncSession, workspace_id: uuid.UUID) -> list[dict[str, Any]]:
    """Active gateway route aliases for a workspace: what a model picker should offer."""
    rows = (
        (
            await db.execute(
                select(GatewayRoute)
                .where(
                    GatewayRoute.workspace_id == workspace_id,
                    GatewayRoute.is_active.is_(True),
                )
                .order_by(GatewayRoute.alias, GatewayRoute.priority)
            )
        )
        .scalars()
        .all()
    )
    aliases: dict[str, dict[str, Any]] = {}
    for route in rows:
        entry = aliases.setdefault(
            route.alias,
            {"alias": route.alias, "provider": route.provider, "targets": []},
        )
        if route.target_model not in entry["targets"]:
            entry["targets"].append(route.target_model)
    return list(aliases.values())


def bearer_from_headers(headers: Any) -> str | None:
    """The caller's ``Authorization: Bearer`` header, forwarded verbatim to the gateway."""
    value = headers.get("authorization") if headers is not None else None
    if value and value.lower().startswith("bearer "):
        return str(value)
    return None
