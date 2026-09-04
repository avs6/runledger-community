"""
Client for the intelligent routing classifier.

The classifier now runs inside runledger-gateway-rs (the Rust data plane).
ROUTER_SVC_URL defaults to the gateway-rs /classify endpoint.  The former
standalone runledger-router sidecar is deprecated — set ROUTER_SVC_URL to
the gateway-rs base URL (e.g. http://runledger-gateway-rs:8210).

Fail-open: any error returns None (no routing decision), so the gateway
falls back to the requested alias.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

log = logging.getLogger(__name__)

_GATEWAY_RS_URL = os.getenv("GATEWAY_RS_URL", "http://runledger-gateway-rs:8210").rstrip("/")
_SVC_URL = os.getenv("ROUTER_SVC_URL", _GATEWAY_RS_URL).rstrip("/")
_TIMEOUT = float(os.getenv("ROUTER_TIMEOUT_SECONDS", "25"))


def enabled() -> bool:
    return bool(_SVC_URL)


async def classify(
    messages: list[dict[str, Any]], config: dict[str, Any] | None
) -> dict[str, Any] | None:
    """
    Return the router decision dict (complexity, risk, reasoning_effort, tier, alias, reason)
    or None on any failure. Never raises.
    """
    if not _SVC_URL:
        return None
    try:
        payload: dict[str, Any] = {"messages": messages}
        if config:
            payload["config"] = config
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(f"{_SVC_URL}/classify", json=payload)
            resp.raise_for_status()
            decision: dict[str, Any] = resp.json()
            return decision
    except Exception as exc:  # noqa: BLE001 — fail-open
        log.warning("intelligent_router_skipped error=%s", str(exc))
    return None
