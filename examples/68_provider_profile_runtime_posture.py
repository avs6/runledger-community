"""
Example: Provider profile runtime & scope posture.

Demonstrates querying the provider-profile-runtime-posture endpoint that surfaces
FinOps context (budget notifications, ledger snapshots), org context (users),
observe context (monitoring alerts), and governance context (MCP servers, search
tools, capture policies).

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
    print("--- Provider Profile Runtime & Scope Posture ---")
    posture = api("GET", "/analytics/provider-profile-runtime-posture")
    print(json.dumps(posture, indent=2))

    print(f"\nProvider profiles: {posture.get('provider_profiles', 0)}")

    finops = posture.get("finops_context", {})
    print(f"\nBudget notifications: {finops.get('budget_notifications', 0)}")
    print(f"Ledger snapshots: {finops.get('ledger_snapshots', 0)}")

    org = posture.get("org_context", {})
    print(f"\nUsers: {org.get('users', 0)}")
    print(f"Workspace scoped: {org.get('workspace_scoped', False)}")

    observe = posture.get("observe_context", {})
    print(f"\nMonitoring alerts: {observe.get('monitoring_alerts', 0)}")

    gov = posture.get("governance_context", {})
    print(f"\nMCP servers: {gov.get('mcp_servers', 0)}")
    print(f"Search tools: {gov.get('search_tools', 0)}")
    print(f"Capture policies: {gov.get('capture_policies', 0)}")


if __name__ == "__main__":
    main()
