"""API key scopes — what a workload key may do.

A workload API key (not a dashboard session) can be limited to any combination of:

  read     read workspace data (runs, analytics, budgets, prompts, policy checks …)
  write    create and change workspace content; implies ``read``
  ingest   send telemetry: SDK/ingest events, OTLP traces/metrics/logs, outcomes, scores
  gateway  call models through the RunLedger gateway (gateway-rs, pass-through endpoints)
  mcp      connect to the RunLedger MCP servers (``/mcp`` and the optimization MCP gateway)

A key with **no scopes has full access**, so keys minted before scopes existed keep
working. Dashboard session keys ignore scopes; they are governed by the user's role.

Scopes only narrow a key: they never grant what the key's workspace role would not.
Admin endpoints still require a dashboard session regardless of scopes.
"""

from __future__ import annotations

from collections.abc import Iterable

SCOPE_DESCRIPTIONS: dict[str, str] = {
    "read": "Read workspace data: runs, analytics, budgets, prompts, policy checks",
    "write": "Create and change workspace content (prompts, agents, workflows, evaluations …); includes read",
    "ingest": "Send telemetry: SDK/ingest events, OTLP traces, metrics and logs, outcomes and scores",
    "gateway": "Call models through the RunLedger gateway",
    "mcp": "Connect to the RunLedger MCP servers",
}
API_KEY_SCOPES: tuple[str, ...] = tuple(SCOPE_DESCRIPTIONS)
_IMPLIES: dict[str, frozenset[str]] = {"write": frozenset({"read"})}

READ = frozenset({"read"})
WRITE = frozenset({"write"})
INGEST = frozenset({"ingest"})
GATEWAY = frozenset({"gateway"})
MCP = frozenset({"mcp"})

_INGEST_PREFIXES = ("/ingest/", "/otlp/", "/v1/traces", "/v1/metrics", "/v1/logs")
# SDK telemetry that lands outside /ingest: accepted with either ingest or write.
_TELEMETRY_WRITES = {
    ("POST", "/outcomes"),
    ("POST", "/evaluations/scores"),
}
# POSTs that change nothing (checks, simulations, searches): read is enough.
_READ_LIKE_POSTS = {
    ("POST", "/policies/check"),
    ("POST", "/policies/simulate-finops"),
    ("POST", "/analytics/simulate-optimization"),
    ("POST", "/tags/auto-rules/simulate"),
    ("POST", "/tool-policies/simulate"),
    ("POST", "/agents/{agent_id}/memory/search"),
    ("POST", "/vector-stores/{collection_id}/search-test"),
}
# Always allowed for any valid key.
_ALWAYS = {("POST", "/auth/logout")}


def normalize_scopes(values: Iterable[str] | None) -> list[str]:
    """Validate and de-duplicate scopes (stable order). Raises ValueError on unknown values."""
    if not values:
        return []
    cleaned: list[str] = []
    for raw in values:
        scope = str(raw).strip().lower()
        if scope not in SCOPE_DESCRIPTIONS:
            allowed = ", ".join(API_KEY_SCOPES)
            raise ValueError(f"Unknown API key scope '{raw}'. Allowed: {allowed}")
        if scope not in cleaned:
            cleaned.append(scope)
    return [s for s in API_KEY_SCOPES if s in cleaned]


def effective_scopes(scopes: Iterable[str] | None) -> frozenset[str] | None:
    """Expanded scope set, or None for an unrestricted key (no scopes)."""
    granted = {s for s in (scopes or []) if s}
    if not granted:
        return None
    for scope in list(granted):
        granted |= _IMPLIES.get(scope, frozenset())
    return frozenset(granted)


def key_allows(scopes: Iterable[str] | None, needed: frozenset[str]) -> bool:
    """True when a key with ``scopes`` may perform an action needing any of ``needed``."""
    granted = effective_scopes(scopes)
    return granted is None or bool(granted & needed)


def required_scopes(method: str, route_path: str) -> frozenset[str] | None:
    """Scopes (any one of) a workload key needs for a control-plane API route.

    ``route_path`` is the route template (e.g. ``/runs/{run_id}``). None means no
    scope is required.
    """
    method = method.upper()
    if (method, route_path) in _ALWAYS:
        return None
    if route_path.startswith(_INGEST_PREFIXES):
        # Reading back ingested runs is also allowed for read keys.
        return INGEST | READ if method in {"GET", "HEAD", "OPTIONS"} else INGEST
    if (method, route_path) in _TELEMETRY_WRITES:
        return INGEST | WRITE
    if method in {"GET", "HEAD", "OPTIONS"} or (method, route_path) in _READ_LIKE_POSTS:
        return READ
    return WRITE
