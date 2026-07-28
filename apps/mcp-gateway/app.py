"""
MCP Gateway — Claude Desktop / Code entry point (Lane B).

A FastMCP server that MCP clients attach to. Exposes the optimization + cognitive layer as tools:
  - compile_context  — shrink a messages array (Context Compiler)
  - memory_store / memory_recall — the shared, workspace-scoped memory (Phase 5)
  - kg_add_entity / kg_add_relation / kg_neighbors — the knowledge graph (Phase 5)
  - skill_list / skill_get — the skill registry (Phase 5)

Every tool is fail-open: on error it returns an { error } payload rather than raising, so a client
session is never broken by a downstream service being unavailable.

Runs as a streamable-HTTP MCP server.
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

HOST = os.getenv("MCP_HOST", "0.0.0.0")
PORT = int(os.getenv("MCP_PORT", "8200"))
CONTEXT_COMPILER_SVC_URL = os.getenv("CONTEXT_COMPILER_SVC_URL", "http://runledger-context-compiler:8103").rstrip("/")
MEMORY_SVC_URL = os.getenv("MEMORY_SVC_URL", "http://runledger-memory-svc:8107").rstrip("/")
KG_SVC_URL = os.getenv("KG_SVC_URL", "http://runledger-kg-svc:8106").rstrip("/")
SKILL_REGISTRY_URL = os.getenv("SKILL_REGISTRY_URL", "http://runledger-skill-registry:8108").rstrip("/")
FLYWHEEL_SVC_URL = os.getenv("FLYWHEEL_SVC_URL", "http://runledger-flywheel:8109").rstrip("/")

mcp = FastMCP("runledger-optimization", host=HOST, port=PORT)


async def _call(method: str, url: str, **kw: Any) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
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
async def compile_context(messages: list[dict[str, Any]], config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Shrink an OpenAI-style messages array (dedup / tool-output / rerank / compaction). Returns { messages, token_report, dropped }."""
    payload: dict[str, Any] = {"messages": messages}
    if config:
        payload["config"] = config
    return await _call("POST", f"{CONTEXT_COMPILER_SVC_URL}/compile", json=payload)


@mcp.tool()
async def select_tools(query: str, tools: list[dict[str, Any]]) -> dict[str, Any]:
    """Return the subset of the given tool definitions most relevant to the query (reduces tool-schema tokens)."""
    return await _call("POST", f"{CONTEXT_COMPILER_SVC_URL}/select-tools", json={"query": query, "tools": tools})


@mcp.tool()
async def memory_store(workspace: str, text: str, kind: str = "fact") -> dict[str, Any]:
    """Store a memory (kind: fact | preference | decision | episode) for a workspace."""
    return await _call("POST", f"{MEMORY_SVC_URL}/memory", json={"workspace": workspace, "kind": kind, "text": text})


@mcp.tool()
async def memory_recall(workspace: str, query: str, k: int = 5) -> dict[str, Any]:
    """Recall the top-k memories relevant to a query for a workspace."""
    return await _call("POST", f"{MEMORY_SVC_URL}/recall", json={"workspace": workspace, "query": query, "k": k})


@mcp.tool()
async def kg_add_entity(workspace: str, id: str, type: str = "", name: str = "") -> dict[str, Any]:
    """Add or update an entity in the knowledge graph."""
    return await _call("POST", f"{KG_SVC_URL}/entities", json={"workspace": workspace, "id": id, "type": type, "name": name})


@mcp.tool()
async def kg_add_relation(workspace: str, from_id: str, to_id: str, type: str) -> dict[str, Any]:
    """Add a relationship between two entities in the knowledge graph."""
    return await _call("POST", f"{KG_SVC_URL}/relations", json={"workspace": workspace, "from_id": from_id, "to_id": to_id, "type": type})


@mcp.tool()
async def kg_neighbors(workspace: str, entity: str, limit: int = 25) -> dict[str, Any]:
    """Return the entities connected to a given entity."""
    return await _call("GET", f"{KG_SVC_URL}/neighbors", params={"workspace": workspace, "entity": entity, "limit": limit})


@mcp.tool()
async def flywheel_analyze(
    segments: list[dict[str, Any]],
    min_quality: float = 0.8,
    min_sample_size: int = 20,
    segment_by: str = "outcome_type",
    action_space: list[str] | None = None,
) -> dict[str, Any]:
    """Given per-segment observations of how configs performed (config, n, avg_cost_per_req, quality), return the cheapest config per segment that holds the quality SLA. Returns { recommendations }."""
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
async def skill_list(workspace: str) -> dict[str, Any]:
    """List the skills registered for a workspace."""
    return await _call("GET", f"{SKILL_REGISTRY_URL}/skills", params={"workspace": workspace})


@mcp.tool()
async def skill_get(workspace: str, name: str) -> dict[str, Any]:
    """Fetch a skill's full content by name."""
    return await _call("GET", f"{SKILL_REGISTRY_URL}/skills/{name}", params={"workspace": workspace})


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
