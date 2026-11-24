"""
examples/43_mcp_registry.py

Exercise the MCP Registry lifecycle with a dashboard session key:
  1. seed default servers
  2. create a custom server
  3. list and inspect it
  4. update the server definition
  5. allow-list two tools on the server with tool policies scoped to it
  6. list tools and make a governed test tool call (status is the real outcome)
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

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8201")
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

        # Per-server permissions are tool policies scoped to the server (one evaluator for
        # MCP calls, /tools/check and the gateway): allow two tools, block the rest.
        policy_ids: list[str] = []
        for name, tool, action, priority in [
            ("allow read_file", "read_file", "allow", 10),
            ("allow list_directory", "list_directory", "allow", 11),
            ("block everything else", "*", "block", 1000),
        ]:
            created_policy = expect_ok(
                client.post(
                    "/tool-policies",
                    json={
                        "name": f"{server_name}: {name}",
                        "tool_name": tool,
                        "action": action,
                        "scope_type": "mcp_server",
                        "scope_id": server_id,
                        "priority": priority,
                    },
                ),
                f"create policy {name}",
            )
            policy_ids.append(created_policy["id"])
        print(f"[ok] allow-listed 2 tools on the server ({len(policy_ids)} policies)")

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
                "governed test tool call",
                allowed=(200, 202, 403),
            )
            # success | error (HTTP server ran it), not_executed (stdio runs on the agent),
            # pending_approval (202), or a 403 when a policy blocks it.
            print(f"[ok] tool call status={tool_call.get('status', 'blocked')}")

        for pid in policy_ids:
            expect_ok(client.delete(f"/tool-policies/{pid}"), "archive policy")
        print("[ok] archived the server's tool policies")

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
