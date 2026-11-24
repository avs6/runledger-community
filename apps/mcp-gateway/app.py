"""
MCP Gateway — Claude Desktop / Code entry point (Lane B).

A FastMCP server that MCP clients attach to. Exposes the optimization + cognitive layer as tools:
  - compile_context  — shrink a messages array (Context Compiler)
  - memory_store / memory_recall — the shared, workspace-scoped memory (Phase 5)
  - kg_add_entity / kg_add_relation / kg_neighbors — the knowledge graph (Phase 5)
  - skill_list / skill_get — the skill registry (Phase 5)

Access control: every tool call must carry a RunLedger API key (``Authorization: Bearer rl_...``).
The key is resolved through the control plane (same rules as the API: a scoped key needs the
``mcp`` scope; revoked/expired keys,
suspended orgs and workspaces, and stale dashboard sessions are refused), and all memory,
knowledge-graph and skill data is namespaced under the key's workspace. The ``workspace``
argument a client passes only names a sub-namespace inside that workspace, so one tenant can
never read or write another tenant's data. Set ``MCP_REQUIRE_AUTH=false`` only for isolated
local development.

Downstream calls are fail-open: when a backing service errors, a tool returns an { error }
payload rather than raising, so a client session is never broken. Authentication is never
fail-open.

Runs as a streamable-HTTP MCP server.
"""

from __future__ import annotations

import os
import time
from typing import Any

import httpx
from mcp.server.fastmcp import Context, FastMCP

HOST = os.getenv("MCP_HOST", "0.0.0.0")
PORT = int(os.getenv("MCP_PORT", "8200"))
CONTEXT_COMPILER_SVC_URL = os.getenv(
    "CONTEXT_COMPILER_SVC_URL", "http://runledger-context-compiler:8103"
).rstrip("/")
MEMORY_SVC_URL = os.getenv("MEMORY_SVC_URL", "http://runledger-memory-svc:8107").rstrip("/")
KG_SVC_URL = os.getenv("KG_SVC_URL", "http://runledger-kg-svc:8106").rstrip("/")
SKILL_REGISTRY_URL = os.getenv("SKILL_REGISTRY_URL", "http://runledger-skill-registry:8108").rstrip(
    "/"
)
FLYWHEEL_SVC_URL = os.getenv("FLYWHEEL_SVC_URL", "http://runledger-flywheel:8109").rstrip("/")

CONTROL_PLANE_URL = os.getenv("RUNLEDGER_CONTROL_PLANE_URL", "http://runledger-api:8000").rstrip(
    "/"
)
ADMIN_SECRET = os.getenv("RUNLEDGER_CONTROL_PLANE_ADMIN_SECRET", "")
# Dedicated channel secret (review tr-security); the admin secret is a legacy fallback.
MCP_INTERNAL_TOKEN = os.getenv("RUNLEDGER_MCP_INTERNAL_TOKEN", "")
CONTROL_PLANE_AUTH = (
    {"x-gateway-internal-token": MCP_INTERNAL_TOKEN}
    if MCP_INTERNAL_TOKEN
    else {"x-admin-secret": ADMIN_SECRET}
)
REQUIRE_AUTH = os.getenv("MCP_REQUIRE_AUTH", "true").lower() not in {"0", "false", "no"}
# Backing services only accept calls that carry this token.
INTERNAL_SERVICE_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN", "")
_AUTH_CACHE_TTL = 60.0
_auth_cache: dict[str, tuple[float, str]] = {}

mcp = FastMCP("runledger-optimization", host=HOST, port=PORT)


class AuthError(Exception):
    pass


def _bearer(ctx: Context | None) -> str | None:
    request = getattr(getattr(ctx, "request_context", None), "request", None) if ctx else None
    header = request.headers.get("authorization", "") if request is not None else ""
    if header.lower().startswith("bearer "):
        return header.split(" ", 1)[1].strip() or None
    return None


async def _workspace_for(ctx: Context | None) -> str:
    """Resolve the caller's workspace id from its RunLedger API key (cached briefly)."""
    raw = _bearer(ctx)
    if raw is None:
        if not REQUIRE_AUTH:
            return "local"
        raise AuthError("Missing RunLedger API key (send Authorization: Bearer rl_...)")
    cached = _auth_cache.get(raw)
    if cached and cached[0] > time.monotonic():
        return cached[1]
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{CONTROL_PLANE_URL}/gateway/runtime/internal/resolve-api-key",
                headers=CONTROL_PLANE_AUTH,
                json={"raw_key": raw, "required_scope": "mcp"},
            )
    except httpx.HTTPError as exc:
        raise AuthError(f"Could not verify API key: {exc}") from exc
    if resp.status_code != 200:
        raise AuthError(
            "Invalid, revoked or unauthorized API key (scoped keys need the 'mcp' scope)"
        )
    workspace_id = str(resp.json()["workspace_id"])
    _auth_cache[raw] = (time.monotonic() + _AUTH_CACHE_TTL, workspace_id)
    return workspace_id


def _namespace(workspace_id: str, requested: str | None) -> str:
    """Tenant-isolated namespace: the caller's workspace, optionally with a sub-namespace."""
    if not requested or requested == workspace_id:
        return workspace_id
    return f"{workspace_id}:{requested}"


async def _scoped(ctx: Context | None, requested: str | None) -> str | dict[str, Any]:
    try:
        return _namespace(await _workspace_for(ctx), requested)
    except AuthError as exc:
        return {"error": str(exc), "status": 401}


async def _call(method: str, url: str, **kw: Any) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(
            timeout=30.0, headers={"x-internal-token": INTERNAL_SERVICE_TOKEN}
        ) as client:
            resp = await client.request(method, url, **kw)
            resp.raise_for_status()
            return resp.json() if resp.content else {}
    except Exception as exc:  # noqa: BLE001 — fail-open
        return {"error": str(exc)}


@mcp.tool()
def health() -> dict[str, str]:
    """Liveness check for the RunLedger optimization MCP gateway."""
    return {"status": "ok", "phase": "5"}


@mcp.tool()
async def compile_context(
    messages: list[dict[str, Any]], config: dict[str, Any] | None = None, ctx: Context | None = None
) -> dict[str, Any]:
    """Shrink an OpenAI-style messages array (dedup / tool-output / rerank / compaction). Returns { messages, token_report, dropped }."""
    if isinstance(ns := await _scoped(ctx, None), dict):
        return ns
    payload: dict[str, Any] = {"messages": messages}
    if config:
        payload["config"] = config
    return await _call("POST", f"{CONTEXT_COMPILER_SVC_URL}/compile", json=payload)


@mcp.tool()
async def select_tools(
    query: str, tools: list[dict[str, Any]], ctx: Context | None = None
) -> dict[str, Any]:
    """Return the subset of the given tool definitions most relevant to the query (reduces tool-schema tokens)."""
    if isinstance(ns := await _scoped(ctx, None), dict):
        return ns
    return await _call(
        "POST", f"{CONTEXT_COMPILER_SVC_URL}/select-tools", json={"query": query, "tools": tools}
    )


@mcp.tool()
async def memory_store(
    text: str, kind: str = "fact", workspace: str = "", ctx: Context | None = None
) -> dict[str, Any]:
    """Store a memory (kind: fact | preference | decision | episode) for a workspace."""
    if isinstance(ns := await _scoped(ctx, workspace), dict):
        return ns
    return await _call(
        "POST", f"{MEMORY_SVC_URL}/memory", json={"workspace": ns, "kind": kind, "text": text}
    )


@mcp.tool()
async def memory_recall(
    query: str, k: int = 5, workspace: str = "", ctx: Context | None = None
) -> dict[str, Any]:
    """Recall the top-k memories relevant to a query for a workspace."""
    if isinstance(ns := await _scoped(ctx, workspace), dict):
        return ns
    return await _call(
        "POST", f"{MEMORY_SVC_URL}/recall", json={"workspace": ns, "query": query, "k": k}
    )


@mcp.tool()
async def kg_add_entity(
    id: str, type: str = "", name: str = "", workspace: str = "", ctx: Context | None = None
) -> dict[str, Any]:
    """Add or update an entity in the knowledge graph."""
    if isinstance(ns := await _scoped(ctx, workspace), dict):
        return ns
    return await _call(
        "POST",
        f"{KG_SVC_URL}/entities",
        json={"workspace": ns, "id": id, "type": type, "name": name},
    )


@mcp.tool()
async def kg_add_relation(
    from_id: str, to_id: str, type: str, workspace: str = "", ctx: Context | None = None
) -> dict[str, Any]:
    """Add a relationship between two entities in the knowledge graph."""
    if isinstance(ns := await _scoped(ctx, workspace), dict):
        return ns
    return await _call(
        "POST",
        f"{KG_SVC_URL}/relations",
        json={"workspace": ns, "from_id": from_id, "to_id": to_id, "type": type},
    )


@mcp.tool()
async def kg_neighbors(
    entity: str, limit: int = 25, workspace: str = "", ctx: Context | None = None
) -> dict[str, Any]:
    """Return the entities connected to a given entity."""
    if isinstance(ns := await _scoped(ctx, workspace), dict):
        return ns
    return await _call(
        "GET", f"{KG_SVC_URL}/neighbors", params={"workspace": ns, "entity": entity, "limit": limit}
    )


@mcp.tool()
async def flywheel_analyze(
    segments: list[dict[str, Any]],
    min_quality: float = 0.8,
    min_sample_size: int = 20,
    segment_by: str = "outcome_type",
    action_space: list[str] | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Given per-segment observations of how configs performed (config, n, avg_cost_per_req, quality), return the cheapest config per segment that holds the quality SLA. Returns { recommendations }."""
    if isinstance(ns := await _scoped(ctx, None), dict):
        return ns
    payload: dict[str, Any] = {
        "segments": segments,
        "min_quality": min_quality,
        "min_sample_size": min_sample_size,
        "segment_by": segment_by,
    }
    if action_space:
        payload["action_space"] = action_space
    return await _call("POST", f"{FLYWHEEL_SVC_URL}/analyze", json=payload)


@mcp.tool()
async def skill_list(workspace: str = "", ctx: Context | None = None) -> dict[str, Any]:
    """List the skills registered for a workspace."""
    if isinstance(ns := await _scoped(ctx, workspace), dict):
        return ns
    return await _call("GET", f"{SKILL_REGISTRY_URL}/skills", params={"workspace": ns})


@mcp.tool()
async def skill_get(name: str, workspace: str = "", ctx: Context | None = None) -> dict[str, Any]:
    """Fetch a skill's full content by name."""
    if isinstance(ns := await _scoped(ctx, workspace), dict):
        return ns
    return await _call("GET", f"{SKILL_REGISTRY_URL}/skills/{name}", params={"workspace": ns})


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
