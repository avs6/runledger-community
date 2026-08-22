"""
Example: Gateway FinOps posture — route spend context and budget awareness.

Demonstrates querying the gateway-wide FinOps posture endpoint that surfaces
route-level spend, budget coverage, notification channels, billing periods,
and chargeback rules for the workspace.

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


def api(method: str, path: str, payload: dict | None = None):
    response = requests.request(
        method,
        f"{BASE_URL}{path}",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    return response.json() if response.content else None


def main():
    print("--- Gateway FinOps Posture ---")
    posture = api("GET", "/analytics/gateway-finops-posture")
    print(json.dumps(posture, indent=2))

    routes = posture.get("routes", {})
    print(f"\nActive routes: {routes.get('total_active', 0)}")
    print(f"  With cost caps: {routes.get('with_cost_caps', 0)}")
    print(f"  With rate limits: {routes.get('with_rate_limits', 0)}")
    print(f"  Distinct models: {routes.get('distinct_models', 0)}")
    print(f"  Routing policies: {routes.get('routing_policies', 0)}")

    spend = posture.get("spend", {})
    print(f"\n30-day spend: ${spend.get('total_30d_usd', 0):.2f}")
    print(f"30-day requests: {spend.get('total_requests_30d', 0)}")

    budgets = posture.get("budgets", {})
    print(f"\nActive budgets: {budgets.get('active_count', 0)}")
    print(f"Budget overrides: {budgets.get('override_count', 0)} total, {budgets.get('active_overrides', 0)} active")

    notif = posture.get("notifications", {})
    print(f"Notification channels: {notif.get('active_channels', 0)}")

    billing = posture.get("billing", {})
    print(f"\nBilling periods: {billing.get('open_periods', 0)} open / {billing.get('total_periods', 0)} total")

    chargeback = posture.get("chargeback", {})
    print(f"Chargeback rules: {chargeback.get('rule_count', 0)}")


if __name__ == "__main__":
    main()
