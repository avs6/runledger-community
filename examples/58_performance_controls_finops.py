"""
Example: Performance controls FinOps posture — cache and rate-limit economics.

Demonstrates querying the per-budget and workspace-wide performance posture
endpoints that surface cache hit rates, estimated savings, rate-limit
containment, and related billing/chargeback metrics.

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
    budgets = api("GET", "/budgets")
    items = budgets.get("items", [])
    if not items:
        print("No budgets found — create a budget first.")
        return

    budget = items[0]
    budget_id = budget["id"]
    print(f"Using budget: {budget_id} (scope: {budget['scope_type']}/{budget['scope_id']})")

    print("\n--- Budget Performance Posture ---")
    posture = api("GET", f"/analytics/budget-performance-posture/{budget_id}")
    print(json.dumps(posture, indent=2))

    cache = posture.get("cache", {})
    print(f"\nCache hit rate: {cache.get('cache_hit_rate_pct', 0)}%")
    print(f"Estimated savings: ~{cache.get('estimated_savings_pct', 0)}%")

    rl = posture.get("rate_limits", {})
    print(f"Rate-limited routes: {rl.get('rate_limited_routes', 0)}/{rl.get('total_active_routes', 0)}")
    print(f"Containment coverage: {rl.get('containment_coverage_pct', 0)}%")

    print("\n--- Billing Period Performance Posture ---")
    billing_posture = api("GET", "/analytics/billing-period-performance-posture")
    print(json.dumps(billing_posture, indent=2))

    billing = billing_posture.get("billing", {})
    print(f"\nOpen periods: {billing.get('open_periods', 0)}/{billing.get('total_periods', 0)}")
    print(f"Active budgets: {billing.get('active_budget_count', 0)}")
    print(f"Chargeback rules: {billing_posture.get('chargeback', {}).get('chargeback_rule_count', 0)}")


if __name__ == "__main__":
    main()
