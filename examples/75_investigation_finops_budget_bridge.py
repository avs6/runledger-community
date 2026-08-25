"""
Example: Investigation FinOps budget bridge.

Demonstrates the end-to-end cost investigation flow:
1. Fetch the investigation FinOps budget posture (budgets, billing, spend)
2. List runs filtered by cost to find high-spend requests
3. Inspect a run's cost against budget utilization
4. Drill into budget detail and billing period context

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
    # ── Step 1: Investigation FinOps budget posture ──────────────────────
    print("=== Step 1: Investigation FinOps Budget Posture ===")
    posture = api("GET", "/analytics/investigation-finops-budget-posture")
    print(json.dumps(posture, indent=2))

    bc = posture.get("budget_context", {})
    print(f"\nBudgets: {bc.get('budgets', 0)} total, {bc.get('active_budgets', 0)} active")
    print(f"Total limit: ${bc.get('total_limit_usd', 0):.2f}")
    print(f"In breach: {bc.get('breach_count', 0)}")
    print(f"Overrides: {bc.get('overrides', 0)} ({bc.get('active_overrides', 0)} active)")

    blc = posture.get("billing_context", {})
    print(f"\nBilling periods: {blc.get('billing_periods', 0)} ({blc.get('open_billing_periods', 0)} open)")
    print(f"Chargeback rules: {blc.get('chargeback_rules', 0)}")

    sc = posture.get("spend_context", {})
    print(f"\n30d spend: ${sc.get('total_spend_30d', 0):.4f}")
    print(f"30d runs: {sc.get('total_runs_30d', 0)}")

    # ── Step 2: List high-cost runs ──────────────────────────────────────
    print("\n=== Step 2: List high-cost runs ===")
    runs = api("GET", "/runs", params={"limit": 5, "min_cost": "0.01"})
    items = runs.get("items", [])
    print(f"Runs with cost >= $0.01: {len(items)}")
    for run in items:
        cost = run.get("total_cost_usd", 0)
        print(f"  {run['id']} — ${cost:.4f} — {run.get('feature_tag', 'untagged')} — {run.get('status', '?')}")

    if not items:
        print("  (none found, listing recent runs instead)")
        runs = api("GET", "/runs", params={"limit": 5})
        items = runs.get("items", [])
        for run in items:
            cost = run.get("total_cost_usd", 0)
            print(f"  {run['id']} — ${cost:.6f} — {run.get('feature_tag', 'untagged')}")

    # ── Step 3: Inspect a run's cost vs budget context ───────────────────
    if items:
        run_id = items[0]["id"]
        run_cost = items[0].get("total_cost_usd", 0)
        print(f"\n=== Step 3: Run {run_id} cost context ===")
        print(f"Run cost: ${run_cost:.6f}")

        limit = bc.get("total_limit_usd", 0)
        spend = sc.get("total_spend_30d", 0)
        if limit > 0:
            utilization = (spend / limit) * 100
            print(f"Budget utilization: ${spend:.4f} / ${limit:.2f} ({utilization:.1f}%)")
        else:
            print("No active budget limits configured")

        if bc.get("breach_count", 0) > 0:
            print(f"WARNING: {bc['breach_count']} budget(s) currently in breach")

    # ── Step 4: Drill into budget and billing detail ─────────────────────
    print("\n=== Step 4: Budget and billing detail ===")
    try:
        budgets = api("GET", "/budgets")
        budget_items = budgets.get("items", [])
        print(f"Budgets: {len(budget_items)}")
        for b in budget_items[:5]:
            print(f"  {b.get('scope_type', '?')}: limit=${b.get('limit_usd', 0):.2f}, "
                  f"spent=${b.get('current_spend_usd', 0):.4f}, "
                  f"action={b.get('action', '?')}, active={b.get('is_active', False)}")
    except Exception as e:
        print(f"  Could not fetch budgets: {e}")

    try:
        billing = api("GET", "/billing/periods")
        periods = billing.get("items", [])
        print(f"\nBilling periods: {len(periods)}")
        for p in periods[:3]:
            print(f"  {p.get('period_start', '?')} to {p.get('period_end', '?')} — "
                  f"status={p.get('status', '?')}, cost=${p.get('total_cost_usd', 0):.4f}")
    except Exception as e:
        print(f"  Could not fetch billing periods: {e}")


if __name__ == "__main__":
    main()
