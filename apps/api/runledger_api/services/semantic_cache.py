"""
Client for the external semantic-cache service (Phase 1).

Fail-open by design: every function swallows errors and returns a no-op result, so the gateway
hot path is never broken by the cache being slow or down. The stage is only invoked when the
request opts in (`body.semantic_cache=True`).

Scope key = {tenant, model, system_prompt_hash, knowledge_version, security_scope}. All scope
fields are matched exactly by the service so a hit can never cross a permission/version boundary.
"""

from __future__ import annotations

import hashlib
import logging
import os
from typing import Any

import httpx

from runledger_api.core.config import settings

log = logging.getLogger(__name__)

_SVC_URL = os.getenv("SEMANTIC_CACHE_SVC_URL", "").rstrip("/")
_TIMEOUT = float(os.getenv("SEMANTIC_CACHE_TIMEOUT_SECONDS", "2.0"))


_client: httpx.AsyncClient | None = None


def _http() -> httpx.AsyncClient:
    """One pooled client per process: no TCP/TLS setup per lookup (review cd:gw-perf)."""
    global _client  # noqa: PLW0603
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=_TIMEOUT, headers=settings.internal_service_headers)
    return _client


def enabled() -> bool:
    """True only if a semantic-cache service URL is configured."""
    return bool(_SVC_URL)


def _system_prompt_hash(messages: list[dict[str, Any]]) -> str:
    system = "\n".join(str(m.get("content", "")) for m in messages if m.get("role") == "system")
    return hashlib.sha256(system.encode()).hexdigest()[:16]


def _canonical_text(messages: list[dict[str, Any]]) -> str:
    """Text used to compute the similarity embedding (non-system turns)."""
    return "\n".join(
        f"{m.get('role')}: {m.get('content', '')}" for m in messages if m.get("role") != "system"
    )


def _scope(
    workspace_id: Any, model: str, messages: list[dict[str, Any]], security_scope: str = ""
) -> dict[str, str]:
    return {
        "tenant": str(workspace_id),
        "model": model,
        "system_prompt_hash": _system_prompt_hash(messages),
        "knowledge_version": "",
        # Caller identity (API key + end user) and request parameters: answers are only
        # reused for the same caller and settings, never across users (review G-06).
        "security_scope": security_scope,
    }


async def lookup(
    workspace_id: Any,
    model: str,
    messages: list[dict[str, Any]],
    security_scope: str = "",
    threshold: float | None = None,
) -> dict[str, Any] | None:
    """Return a cached response dict on a semantic hit, else None. Never raises.

    ``threshold`` is the workspace cache profile's ``similarity_threshold`` (G-09);
    None lets the service use its default."""
    if not _SVC_URL:
        return None
    try:
        payload: dict[str, Any] = {
            "text": _canonical_text(messages),
            "scope": _scope(workspace_id, model, messages, security_scope),
        }
        if threshold is not None:
            payload["threshold"] = threshold
        resp = await _http().post(f"{_SVC_URL}/lookup", json=payload)
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        if data.get("hit") and data.get("payload"):
            hit_payload: dict[str, Any] = data["payload"]
            return hit_payload
    except Exception as exc:  # noqa: BLE001 — fail-open
        log.warning("semantic_cache_lookup_skipped error=%s", str(exc))
    return None


async def store(
    workspace_id: Any,
    model: str,
    messages: list[dict[str, Any]],
    response_json: dict[str, Any],
    prompt_tokens: int | None,
    completion_tokens: int | None,
    security_scope: str = "",
) -> None:
    """Store a response for future semantic hits. Never raises."""
    if not _SVC_URL:
        return
    try:
        payload = {
            "text": _canonical_text(messages),
            "scope": _scope(workspace_id, model, messages, security_scope),
            "response": response_json,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }
        resp = await _http().post(f"{_SVC_URL}/store", json=payload)
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001 — fail-open
        log.warning("semantic_cache_store_skipped error=%s", str(exc))
