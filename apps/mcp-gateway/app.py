"""
MCP Gateway — Lane B scaffold.

A FastMCP server that Claude Desktop / Claude Code (and other MCP clients) attach to. In Phase 1
it exposes only a `health` tool with an empty-but-wired tool registry; the cognitive tools
(memory, knowledge graph, episodes, context compiler) attach here in Phase 5.

Run as a streamable-HTTP MCP server so it is reachable over the container network / from the host.
"""

from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

HOST = os.getenv("MCP_HOST", "0.0.0.0")
PORT = int(os.getenv("MCP_PORT", "8200"))

mcp = FastMCP("runledger-optimization", host=HOST, port=PORT)


@mcp.tool()
def health() -> dict[str, str]:
    """Liveness check for the RunLedger optimization MCP gateway."""
    return {"status": "ok", "phase": "1", "registered_tools": "health"}


if __name__ == "__main__":
    # Phase 5 will register memory/kg/episode/compiler tools before this line.
    mcp.run(transport="streamable-http")
