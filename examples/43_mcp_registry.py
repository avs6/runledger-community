"""
examples/43_mcp_registry.py

Exercise the MCP Registry lifecycle with a dashboard session key:
  1. seed default servers
  2. create a custom server
  3. list and inspect it
  4. update the server definition
  5. grant and revoke a permission policy
  6. list tools and execute a test tool call
  7. deactivate and re-activate the server

Required env vars:
  RUNLEDGER_BASE_URL
  RUNLEDGER_SESSION_KEY
  RUNLEDGER_WORKSPACE_ID
"""

from __future__ import annotations

import os
import sys
import uuid

import httpx

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
SESSION_KEY = os.getenv("RUNLEDGER_SESSION_KEY", "")
WORKSPACE_ID = os.getenv("RUNLEDGER_WORKSPACE_ID", "")

if not SESSION_KEY or not WORKSPACE_ID:
    print("Error: RUNLEDGER_SESSION_KEY and RUNLEDGER_WORKSPACE_ID are required", file=sys.stderr)
    raise SystemExit(1)

HEADERS = {
    "Authorization": f"Bearer {SESSION_KEY}",
    "Content-Type": "application/json",
}


def expect_ok(resp: httpx.Response, label: str, allowed: tuple[int, ...] = (200, 201, 204)) -> dict:
    if resp.status_code not in allowed:
        raise RuntimeError(f"{label} failed: {resp.status_code} {resp.text}")
    if resp.status_code == 204:
        return {}
    return resp.json()


def main() -> None:
    suffix = uuid.uuid4().hex[:8]
    server_name = f"Example MCP Server {suffix}"

    with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=20) as client:
        seeded = expect_ok(client.post("/mcp-registry/seed-defaults"), "seed default servers")
        print(f"[ok] seeded defaults added={seeded['servers_added']}")

        created = expect_ok(
            client.post(
                "/mcp-registry",
                json={
                    "name": server_name,
                    "description": "Workspace example MCP server",
                    "transport": "http",
                    "url": "https://example.internal/mcp",
                    "env": {"RUNLEDGER_PROFILE": "example"},
                    "auth_type": "bearer",
                },
            ),
            "create mcp server",
        )
        server_id = created["id"]
        print(f"[ok] created MCP server {created['name']}")

        listing = expect_ok(client.get("/mcp-registry"), "list mcp servers")
        print(f"[ok] listed {len(listing['items'])} MCP servers")

        fetched = expect_ok(client.get(f"/mcp-registry/{server_id}"), "get mcp server")
        print(f"[ok] fetched transport={fetched['transport']}")

        updated = expect_ok(
            client.put(
                f"/mcp-registry/{server_id}",
                json={
                    "description": "Workspace example MCP server updated",
                    "transport": "stdio",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "./workspace"],
                    "env": {"RUNLEDGER_PROFILE": "example-updated"},
                },
            ),
            "update mcp server",
        )
        print(f"[ok] updated MCP server transport={updated['transport']}")

        policy = expect_ok(
            client.post(
                "/mcp-registry/permissions",
                json={
                    "mcp_server_id": server_id,
                    "scope_type": "workspace",
                    "scope_id": WORKSPACE_ID,
                    "allowed_tools": ["read_file", "list_directory"],
                },
            ),
            "grant permission policy",
        )
        policy_id = policy["id"]
        print(f"[ok] granted policy {policy_id}")

        tools = expect_ok(client.get("/mcp-registry/tools"), "list mcp tools")
        print(f"[ok] listed {len(tools['items'])} MCP tools")
        if tools["items"]:
            tool_name = tools["items"][0]["tool_name"]
            tool_call = expect_ok(
                client.post(
                    "/mcp-registry/tools/call",
                    json={
                        "server_id": tools["items"][0]["server_id"],
                        "tool_name": tool_name,
                        "arguments": {},
                    },
                ),
                "execute test tool call",
            )
            print(f"[ok] executed tool call status={tool_call['status']}")

        expect_ok(client.delete(f"/mcp-registry/permissions/{policy_id}"), "revoke permission policy")
        print("[ok] revoked permission policy")

        expect_ok(client.delete(f"/mcp-registry/{server_id}"), "deactivate mcp server")
        print("[ok] deactivated MCP server")

        reactivated = expect_ok(
            client.put(f"/mcp-registry/{server_id}", json={"is_active": True}),
            "reactivate mcp server",
        )
        print(f"[ok] re-activated MCP server active={reactivated['is_active']}")

    print("[done] MCP Registry example completed")


if __name__ == "__main__":
    main()
