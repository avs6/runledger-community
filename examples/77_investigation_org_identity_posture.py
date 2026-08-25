"""
Example: Investigation org identity posture.

Demonstrates querying the investigation-org-identity-posture endpoint that
surfaces organization identity context (workspace users, API keys, telemetry
batches, MCP servers) for investigation scope.

Required env vars:
  RUNLEDGER_BASE_URL
  RUNLEDGER_API_KEY
"""

from __future__ import annotations

import json
import os

import requests

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8201")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")


def api(method: str, path: str, params: dict | None = None):
    response = requests.request(
        method,
        f"{BASE_URL}{path}",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        params=params,
        timeout=30,
    )
    response.raise_for_status()
    return response.json() if response.content else None


def main():
    print("--- Investigation Org Identity Posture ---")
    posture = api("GET", "/analytics/investigation-org-identity-posture")
    print(json.dumps(posture, indent=2))

    org = posture.get("org_context", {})
    print(f"\nWorkspace: {org.get('workspace_name', 'N/A')}")
    print(f"Workspace users: {org.get('workspace_users', 0)}")

    users = posture.get("user_context", {})
    print(f"Distinct end users (30d): {users.get('distinct_end_users_30d', 0)}")
    print(f"Runs (30d): {users.get('runs_30d', 0)}")

    keys = posture.get("api_key_context", {})
    print(f"API keys: {keys.get('total_keys', 0)} total, {keys.get('active_keys', 0)} active, {keys.get('keys_with_traffic_30d', 0)} with traffic")

    telemetry = posture.get("telemetry_context", {})
    print(f"Telemetry batches (30d): {telemetry.get('batches_30d', 0)}")

    mcp = posture.get("mcp_context", {})
    print(f"MCP servers: {mcp.get('servers', 0)}, tool calls (30d): {mcp.get('tool_calls_30d', 0)}")

    print("\n--- Runs filtered by API key (example) ---")
    runs = api("GET", "/runs", params={"limit": "5"})
    for run in runs.get("items", [])[:3]:
        print(f"  Run {run['id'][:12]}  api_key={run.get('api_key_id', 'N/A')}  user={run.get('end_user_id', 'N/A')}")


if __name__ == "__main__":
    main()
