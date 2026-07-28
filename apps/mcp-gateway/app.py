"""
MCP Gateway — Claude Desktop / Code entry point (Lane B).

A FastMCP server that MCP clients attach to. Phase 1 shipped a `health` tool; Phase 2 adds
`compile_context`, which shrinks an OpenAI-style messages array via the Context Compiler service
(dedup / tool-output compression / rerank / compaction) so a client can compact context on demand.
The cognitive tools (memory, knowledge graph, episodes) attach here in Phase 5.

Runs as a streamable-HTTP MCP server.
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

HOST = os.getenv("MCP_HOST", "0.0.0.0")
PORT = int(os.getenv("MCP_PORT", "8200"))
CONTEXT_COMPILER_SVC_URL = os.getenv(
    "CONTEXT_COMPILER_SVC_URL", "http://runledger-context-compiler:8103"
).rstrip("/")

mcp = FastMCP("runledger-optimization", host=HOST, port=PORT)


@mcp.tool()
def health() -> dict[str, str]:
    """Liveness check for the RunLedger optimization MCP gateway."""
    return {"status": "ok", "phase": "2", "registered_tools": "health, compile_context"}


@mcp.tool()
async def compile_context(
    messages: list[dict[str, Any]], config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Compile (shrink) an OpenAI-style `messages` array before sending it to a model.

    Runs dedup, tool-output compression, relevance rerank+prune, and conversation compaction.
    `config` may set: model, reranker_model, token_threshold (0 = always), token_budget, stages.
    Returns { messages, token_report, dropped }. Fail-open: on error returns the input unchanged.
    """
    payload: dict[str, Any] = {"messages": messages}
    if config:
        payload["config"] = config
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{CONTEXT_COMPILER_SVC_URL}/compile", json=payload)
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:  # noqa: BLE001 — fail-open
        return {"messages": messages, "token_report": None, "dropped": [], "error": str(exc)}


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
