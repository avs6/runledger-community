"""
Example: Rate limit scope and explainability posture.

Demonstrates querying the rate-limit-scope-posture endpoint that surfaces
throttle context (routes with RPM, pass-through, routing policies), scope
context (access groups, monitoring alerts), and FinOps context (budgets,
notifications, chargeback rules, ledger snapshots).

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
    print("--- Rate Limit Scope Posture ---")
    posture = api("GET", "/analytics/rate-limit-scope-posture")
    print(json.dumps(posture, indent=2))

    tc = posture.get("throttle_context", {})
    print(f"\nRoutes with RPM: {tc.get('routes_with_rpm', 0)}")
    print(f"Active routes: {tc.get('active_routes', 0)}")
    print(f"Pass-through with RPM: {tc.get('passthrough_with_rpm', 0)}")
    print(f"Routing policies: {tc.get('routing_policies', 0)}")

    sc = posture.get("scope_context", {})
    print(f"\nAccess groups: {sc.get('access_groups', 0)}")
    print(f"Monitoring alerts: {sc.get('monitoring_alerts', 0)}")

    fc = posture.get("finops_context", {})
    print(f"\nBudgets: {fc.get('budgets', 0)}")
    print(f"Budget notifications: {fc.get('budget_notifications', 0)}")
    print(f"Chargeback rules: {fc.get('chargeback_rules', 0)}")
    print(f"Ledger snapshots: {fc.get('ledger_snapshots', 0)}")


if __name__ == "__main__":
    main()
