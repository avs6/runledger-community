"""
Example: Gateway control plane posture.

Demonstrates querying the gateway-control-plane-posture endpoint that surfaces
org context (users, access groups, API keys), gateway context (routes, policies,
providers, guardrails), observe context (monitoring alerts), and governance
context (pending approvals, audit events).

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
    print("--- Gateway Control Plane Posture ---")
    posture = api("GET", "/analytics/gateway-control-plane-posture")
    print(json.dumps(posture, indent=2))

    org = posture.get("org_context", {})
    print(f"\nUsers: {org.get('users', 0)}")
    print(f"Access groups: {org.get('access_groups', 0)}")
    print(f"API keys: {org.get('api_keys', 0)}")

    gw = posture.get("gateway_context", {})
    print(f"\nActive routes: {gw.get('active_routes', 0)}")
    print(f"Routing policies: {gw.get('routing_policies', 0)}")
    print(f"Provider profiles: {gw.get('provider_profiles', 0)}")
    print(f"Active guardrails: {gw.get('active_guardrails', 0)}")

    observe = posture.get("observe_context", {})
    print(f"\nMonitoring alerts: {observe.get('monitoring_alerts', 0)}")

    gov = posture.get("governance_context", {})
    print(f"\nApprovals pending: {gov.get('approvals_pending', 0)}")
    print(f"Audit events (30d): {gov.get('audit_events_30d', 0)}")


if __name__ == "__main__":
    main()
