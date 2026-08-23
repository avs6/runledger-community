"""
Example: Gateway safety & governance posture — tool policies, approvals, audit, and alerts.

Demonstrates querying the gateway-safety-posture endpoint that surfaces gateway context
(active routes, cache-enabled, rate-limited, guardrail rules, active guardrails, blocks),
tool governance (policies, MCP servers), approvals, audit events, alert rules, and tags.

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
    print("--- Gateway Safety & Governance Posture ---")
    posture = api("GET", "/analytics/gateway-safety-posture")
    print(json.dumps(posture, indent=2))

    gw = posture.get("gateway_context", {})
    print(f"\nActive routes: {gw.get('active_routes', 0)}")
    print(f"Cache-enabled: {gw.get('cache_enabled_routes', 0)}")
    print(f"Rate-limited: {gw.get('rate_limited_routes', 0)}")
    print(f"Guardrail rules: {gw.get('guardrail_rules', 0)}")
    print(f"Active guardrails: {gw.get('active_guardrails', 0)}")
    print(f"Guardrail blocks (30d): {gw.get('guardrail_blocks_30d', 0)}")

    tools = posture.get("tool_governance", {})
    print(f"\nTool policies: {tools.get('tool_policy_count', 0)}")
    print(f"Active tool policies: {tools.get('active_tool_policies', 0)}")
    print(f"MCP servers: {tools.get('mcp_server_count', 0)}")

    approvals = posture.get("approvals", {})
    print(f"\nApprovals (30d): {approvals.get('total_30d', 0)}")
    print(f"Pending: {approvals.get('pending', 0)}")

    audit = posture.get("audit", {})
    print(f"\nAudit events (30d): {audit.get('total_events_30d', 0)}")
    print(f"Gateway audit events (30d): {audit.get('gateway_events_30d', 0)}")

    alerts = posture.get("alert_rules", {})
    print(f"\nAlert rules: {alerts.get('total', 0)}")
    print(f"Active: {alerts.get('active', 0)}")

    tags = posture.get("tags", {})
    print(f"\nTags: {tags.get('total', 0)}")


if __name__ == "__main__":
    main()
