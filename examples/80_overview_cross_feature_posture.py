"""
Example: Overview cross-feature posture cards.

Demonstrates the Analytics Overview cross-feature posture entry point:
1. Fetch gateway posture (providers, routes, guardrails)
2. Fetch governance posture (security, alerts, audit, tags)
3. Fetch org identity posture (users, API keys, telemetry, MCP, AI hub)
4. Summarise workspace health across all three domains

Required env vars:
  RUNLEDGER_BASE_URL
  RUNLEDGER_API_KEY
"""

from __future__ import annotations

import os

import requests

BASE = os.environ["RUNLEDGER_BASE_URL"].rstrip("/")
HEADERS = {
    "Authorization": f"Bearer {os.environ['RUNLEDGER_API_KEY']}",
    "Content-Type": "application/json",
}


def get(path: str) -> dict:
    resp = requests.get(f"{BASE}{path}", headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    print("=== Gateway Posture ===\n")
    gw = get("/analytics/overview-gateway-posture")
    pc = gw["provider_context"]
    print(f"  Distinct providers: {pc['distinct_providers']}")
    print(f"  Routes:             {pc['active_routes']}/{pc['total_routes']} active")
    print(f"  Routing policies:   {pc['routing_policies']}")

    gc = gw["guardrail_context"]
    print(f"\n  Guardrail rules:    {gc['active_rules']} active")
    print(f"  Events (30d):       {gc['events_30d']}")
    print(f"  Blocks (30d):       {gc['blocks_30d']}")

    rc = gw["route_context"]
    print(f"  Passthrough:        {rc['passthrough_endpoints']} endpoints")

    print("\n=== Governance Posture ===\n")
    gov = get("/analytics/overview-governance-posture")
    sc = gov["security_context"]
    print(f"  Security events:    {sc['security_events']} total, {sc['security_events_30d']} in 30d")

    ac = gov["alert_context"]
    print(f"  Alert rules:        {ac['active_alert_rules']}/{ac['alert_rules']} active")
    print(f"  Active firings:     {ac['active_firings']}")

    auc = gov["audit_context"]
    print(f"  Audit events (30d): {auc['audit_events_30d']}")

    govc = gov["governance_context"]
    print(f"\n  Tags:               {govc['active_tags']}/{govc['tags']} active")
    print(f"  Approvals:          {govc['approvals']}")
    print(f"  Capture policies:   {govc['capture_policies']}")

    print("\n=== Org Identity Posture ===\n")
    org = get("/analytics/overview-org-posture")
    print(f"  Workspace users:    {org['user_context']['workspace_users']}")
    print(f"  API keys:           {org['api_key_context']['active_api_keys']}/{org['api_key_context']['api_keys']} active")
    print(f"  Telemetry (30d):    {org['telemetry_context']['telemetry_batches_30d']} batches")
    print(f"  MCP servers:        {org['mcp_context']['active_mcp_servers']}/{org['mcp_context']['mcp_servers']} active")
    print(f"  AI Hub models:      {org['hub_context']['active_hub_models']}/{org['hub_context']['hub_models']} active")

    print("\n=== Drill-Through Targets ===\n")
    print("  /provider-profiles   — Provider configuration and traffic")
    print("  /gateway             — Model gateway and routing")
    print("  /guardrails          — Guardrail rules and events")
    print("  /security            — Security events and investigation")
    print("  /alert-rules         — Alert rule management")
    print("  /audit               — Audit log")
    print("  /tags                — Tag management")
    print("  /users               — User management")
    print("  /api-keys            — API key management")
    print("  /monitoring/telemetry — Telemetry ingest")
    print("  /mcp-registry        — MCP server registry")
    print("  /ai-hub              — AI hub model catalog")


if __name__ == "__main__":
    main()
