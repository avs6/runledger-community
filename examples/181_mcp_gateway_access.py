"""
examples/181_mcp_gateway_access.py

Tenant-isolated memory through the optimization MCP gateway.

  1. Connect without an API key: every tool call is refused (status 401).
  2. Connect with a RunLedger API key: the gateway resolves the key to its
     workspace, and memory is stored and recalled inside that workspace only.
  3. Pass another tenant's workspace name: it only becomes a sub-namespace of
     the caller's own workspace, so nothing leaks across tenants.

Required env vars:
  RUNLEDGER_API_KEY   a workspace API key (rl_live_... / rl_test_...)
Optional:
  RUNLEDGER_MCP_URL   default http://localhost:8206/mcp

Needs:  pip install "mcp>=1.10"
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

MCP_URL = os.getenv("RUNLEDGER_MCP_URL", "http://localhost:8206/mcp")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")


async def call(headers: dict[str, str], tool: str, args: dict[str, Any]) -> dict[str, Any]:
    async with (
        streamablehttp_client(MCP_URL, headers=headers) as (read, write, _),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        result = await session.call_tool(tool, args)
        text = result.content[0].text if result.content else "{}"  # type: ignore[union-attr]
        return json.loads(text)


async def main() -> None:
    if not API_KEY:
        print("Error: RUNLEDGER_API_KEY not set", file=sys.stderr)
        raise SystemExit(1)

    anonymous = await call({}, "memory_recall", {"query": "anything"})
    print(f"[ok] no key       -> {anonymous.get('status')} {anonymous.get('error')}")

    auth = {"Authorization": f"Bearer {API_KEY}"}
    stored = await call(
        auth, "memory_store", {"text": "Deploys happen on Tuesdays.", "kind": "fact"}
    )
    print(f"[ok] store        -> {stored}")
    recalled = await call(auth, "memory_recall", {"query": "When do deploys happen?", "k": 3})
    print(f"[ok] recall       -> {recalled}")

    # Naming someone else's workspace cannot reach their data.
    other = await call(auth, "memory_recall", {"query": "secrets", "workspace": "another-tenant"})
    print(f"[ok] other tenant -> searched only inside your own workspace: {other}")


if __name__ == "__main__":
    asyncio.run(main())
