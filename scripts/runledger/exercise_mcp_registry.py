"""
Smoke-test the consolidated MCP Registry control-plane flow.

Requires:
  RUNLEDGER_BASE_URL
  RUNLEDGER_SESSION_KEY
  RUNLEDGER_WORKSPACE_ID

This script exercises the real registry CRUD, permission, and tool-call APIs
that back /mcp-registry.
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
    sys.exit(1)

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
    server_name = f"MCP Smoke {suffix}"

    with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=20) as client:
        seeded = expect_ok(client.post("/mcp-registry/seed-defaults"), "seed default servers")
        print(f"[ok] seeded defaults added={seeded['servers_added']}")

        created = expect_ok(
            client.post(
                "/mcp-registry",
                json={
                    "name": server_name,
                    "description": "MCP registry smoke server",
                    "transport": "http",
                    "url": "https://smoke.internal/mcp",
                    "env": {"RUNLEDGER_ENV": "smoke"},
                    "auth_type": "bearer",
                },
            ),
            "create mcp server",
        )
        server_id = created["id"]
        print(f"[ok] created server {created['name']}")

        fetched = expect_ok(client.get(f"/mcp-registry/{server_id}"), "get mcp server")
        assert fetched["name"] == server_name
        print("[ok] fetched created server")

        updated = expect_ok(
            client.put(
                f"/mcp-registry/{server_id}",
                json={
                    "description": "MCP registry smoke server updated",
                    "transport": "stdio",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-brave-search"],
                    "env": {"RUNLEDGER_ENV": "smoke-updated"},
                },
            ),
            "update mcp server",
        )
        assert updated["transport"] == "stdio"
        print("[ok] updated server definition")

        permission = expect_ok(
            client.post(
                "/mcp-registry/permissions",
                json={
                    "mcp_server_id": server_id,
                    "scope_type": "workspace",
                    "scope_id": WORKSPACE_ID,
                    "allowed_tools": ["brave_web_search"],
                },
            ),
            "grant permission policy",
        )
        permission_id = permission["id"]
        print("[ok] created permission policy")

        permissions = expect_ok(client.get("/mcp-registry/permissions"), "list permissions")
        assert any(item["id"] == permission_id for item in permissions["items"])
        print("[ok] listed permission policies")

        tools = expect_ok(client.get("/mcp-registry/tools"), "list mcp tools")
        print(f"[ok] listed {len(tools['items'])} tools")
        if tools["items"]:
            tool = tools["items"][0]
            tool_call = expect_ok(
                client.post(
                    "/mcp-registry/tools/call",
                    json={
                        "server_id": tool["server_id"],
                        "tool_name": tool["tool_name"],
                        "arguments": {},
                    },
                ),
                "execute tool call",
            )
            print(f"[ok] executed tool call status={tool_call['status']}")

        expect_ok(client.delete(f"/mcp-registry/{server_id}"), "deactivate mcp server")
        print("[ok] deactivated server")

        reactivated = expect_ok(
            client.put(f"/mcp-registry/{server_id}", json={"is_active": True}),
            "reactivate mcp server",
        )
        assert reactivated["is_active"] is True
        print("[ok] re-activated server")

        expect_ok(client.delete(f"/mcp-registry/permissions/{permission_id}"), "revoke permission policy")
        print("[ok] revoked permission policy")

    print("[done] MCP registry smoke test completed")


if __name__ == "__main__":
    main()
