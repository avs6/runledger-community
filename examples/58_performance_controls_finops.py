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
    ctx = api("GET", f"/context?entity=budget&id={budget_id}")
    print("  Related: " + ", ".join(f"{i['label']}={i['value']}" for i in ctx["items"]))

    print(f"\nCache hit rate: {cache.get('cache_hit_rate_pct', 0)}%")
    print(f"Estimated savings: ~{cache.get('estimated_savings_pct', 0)}%")

    print(f"Rate-limited routes: {rl.get('rate_limited_routes', 0)}/{rl.get('total_active_routes', 0)}")
    print(f"Containment coverage: {rl.get('containment_coverage_pct', 0)}%")

    print("\n--- Billing Period Performance Posture ---")

    print(f"\nOpen periods: {billing.get('open_periods', 0)}/{billing.get('total_periods', 0)}")
    print(f"Active budgets: {billing.get('active_budget_count', 0)}")


if __name__ == "__main__":
    main()
