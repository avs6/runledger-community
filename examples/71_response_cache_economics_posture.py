"""
Example: Response cache economics and evidence posture.

Demonstrates querying the response-cache-economics-posture endpoint that
surfaces cache profiles and routes, FinOps context (budgets, overrides,
notifications, billing periods, ledger snapshots), governance context (audit
events), and org context (users).

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
    print("--- Response Cache Economics Posture ---")
    posture = api("GET", "/analytics/response-cache-economics-posture")
    print(json.dumps(posture, indent=2))

    cc = posture.get("cache_context", {})
    print(f"\nCache profiles: {cc.get('profiles', 0)}")
    print(f"Cache-enabled routes: {cc.get('cache_enabled_routes', 0)}")
    print(f"Active routes: {cc.get('active_routes', 0)}")

    fc = posture.get("finops_context", {})
    print(f"\nBudgets: {fc.get('budgets', 0)}")
    print(f"Budget overrides: {fc.get('budget_overrides', 0)}")
    print(f"Budget notifications: {fc.get('budget_notifications', 0)}")
    print(f"Billing periods: {fc.get('billing_periods', 0)}")
    print(f"Ledger snapshots: {fc.get('ledger_snapshots', 0)}")

    gc = posture.get("governance_context", {})
    print(f"\nAudit events (30d): {gc.get('audit_events_30d', 0)}")

    oc = posture.get("org_context", {})
    print(f"\nUsers: {oc.get('users', 0)}")


if __name__ == "__main__":
    main()
