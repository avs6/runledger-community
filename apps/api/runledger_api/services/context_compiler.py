"""
Client for the external context-compiler service (Phase 2).

Fail-open by design: any error returns the original messages unchanged, so the gateway hot path
is never broken by the compiler being slow or down. Invoked only when the request opts in
(body.context_compiler) or the route has context_compiler_enabled=True.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

log = logging.getLogger(__name__)

_SVC_URL = os.getenv("CONTEXT_COMPILER_SVC_URL", "").rstrip("/")
_TIMEOUT = float(os.getenv("CONTEXT_COMPILER_TIMEOUT_SECONDS", "25"))


def enabled() -> bool:
    return bool(_SVC_URL)


async def compile_messages(
    messages: list[dict[str, Any]],
    config: dict[str, Any] | None,
    workspace: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """
    Return (compiled_messages, token_report). On any failure returns the original
    messages and a None report. Never raises.
    """
    if not _SVC_URL:
        return messages, None
    try:
        payload: dict[str, Any] = {"messages": messages}
        if config:
            payload["config"] = config
        if workspace:
            payload["workspace"] = workspace
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(f"{_SVC_URL}/compile", json=payload)
            resp.raise_for_status()
            data = resp.json()
        compiled = data.get("messages")
        if isinstance(compiled, list) and compiled:
            return compiled, data.get("token_report")
    except Exception as exc:  # noqa: BLE001 — fail-open
        log.warning("context_compiler_skipped error=%s", str(exc))
    return messages, None
