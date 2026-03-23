"""
Runtime tool policy check for the RunLedger SDK.

Called by SDK hooks (OpenAI wrapper, LangChain callback, LangGraph node wrapper)
*before* a tool executes, to enforce the workspace Tool Registry policy in real time.

Architecture
------------
- Primary check: GET /tools/check/{tool_name} → 200 (allowed) or 403 (blocked)
- In-memory TTL cache (60 s) avoids repeated API calls for the same tool
- Fail-open: any network/timeout error returns "allow" — never blocks the user
- ToolBlockedError is raised synchronously in the agent thread; the run
  shows status=failed with error_type=ToolBlockedError in RunLedger

Cache invalidation
------------------
The server invalidates its Redis cache on every registry update. The SDK-side
in-memory cache has a 60 s TTL — policy changes take effect within 60 s.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import httpx
import structlog

from runledger_sdk.exceptions import ToolBlockedError

if TYPE_CHECKING:
    from runledger_sdk.transport import SyncTransport

log = structlog.get_logger()

_CACHE_TTL = 60.0  # seconds

# In-memory cache: (api_key_prefix, tool_name) → (policy, runtime_enforcement, expires)
_cache: dict[tuple[str, str], tuple[str, bool, float]] = {}


def check_tool_sync(tool_name: str, transport: SyncTransport) -> str:
    """
    Check if a tool is allowed by workspace policy.

    Parameters
    ----------
    tool_name:
        The name of the tool about to be called.
    transport:
        The SDK's SyncTransport (carries API key + base URL).

    Returns
    -------
    str
        The policy string: "allow", "audit", or "block".

    Raises
    ------
    ToolBlockedError
        If the tool's policy is "block" and runtime_enforcement=True.
    """
    if transport._local or not transport._api_key:
        return "allow"

    # Cache key uses first 16 chars of the API key (enough to be workspace-unique)
    cache_key = (transport._api_key[:16], tool_name)
    now = time.monotonic()

    # Fast path: return from cache if still valid
    if cache_key in _cache:
        policy, enforced, expires = _cache[cache_key]
        if now < expires:
            if policy == "block" and enforced:
                raise ToolBlockedError(tool_name)
            return policy

    # Slow path: call the API
    try:
        response = httpx.get(
            f"{transport._base_url}/tools/check/{tool_name}",
            headers={"Authorization": f"Bearer {transport._api_key}"},
            timeout=3.0,
        )

        if response.status_code == 403:
            # Tool is blocked — cache the decision and raise
            _cache[cache_key] = ("block", True, now + _CACHE_TTL)
            raise ToolBlockedError(tool_name)

        if response.status_code == 200:
            data = response.json()
            policy = str(data.get("policy", "allow"))
            enforced = bool(data.get("runtime_enforcement", False))
            _cache[cache_key] = (policy, enforced, now + _CACHE_TTL)
            return policy

        # Unexpected status — fail open
        log.warning(
            "tool_check_unexpected_status",
            tool_name=tool_name,
            status=response.status_code,
        )
        return "allow"

    except ToolBlockedError:
        raise
    except Exception as exc:
        # Network error, timeout, etc. — fail open, never block the user's call
        log.warning("tool_check_error", tool_name=tool_name, error=str(exc))
        return "allow"


def invalidate_cache(api_key: str, tool_name: str) -> None:
    """Remove a cached policy entry (call after registry updates)."""
    _cache.pop((api_key[:16], tool_name), None)
