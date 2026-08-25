"""
Example: Overview & Economics FinOps budget bridge.

Demonstrates the overview-to-budget and model-usage-to-budget investigation flow:
1. Fetch the overview FinOps budget posture (budgets, billing, spend, notifications)
2. Fetch per-model budget utilization (spend vs. budget limit per model)
3. Identify models exceeding or approaching budget limits
4. Drill into budget detail and billing period context

Required env vars:
  RUNLEDGER_BASE_URL
  RUNLEDGER_API_KEY
"""

from __future__ import annotations

import json
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
    print("=== Overview FinOps Budget Posture ===\n")
    posture = get("/analytics/overview-finops-budget-posture")
    bc = posture["budget_context"]
    print(f"  Active budgets: {bc['active_budgets']} / {bc['budgets']} total")
    print(f"  Total limit:    ${bc['total_limit_usd']:.2f}")
    print(f"  Breached:       {bc['breach_count']}")
    print(f"  Overrides:      {bc['overrides']} ({bc['active_overrides']} active)")

    sc = posture["spend_context"]
    print(f"\n  Spend (30d):    ${sc['total_spend_30d']:.2f}")
    print(f"  Runs (30d):     {sc['total_runs_30d']}")

    blc = posture["billing_context"]
    print(f"\n  Billing periods: {blc['billing_periods']} ({blc['open_billing_periods']} open)")
    print(f"  Chargeback rules: {blc['chargeback_rules']}")

    nc = posture["notification_context"]
    print(f"\n  Notifications:   {nc['active_notifications']} active / {nc['notifications']} total")

    print("\n=== Model Budget Utilization ===\n")
    util = get("/analytics/model-budget-utilization")
    print(f"  Model budgets: {util['active_model_budgets']} active / {util['total_model_budgets']} total")
    print(f"  Billing periods: {util['billing_periods']} ({util['open_billing_periods']} open)")
    print(f"  Chargeback rules: {util['chargeback_rules']}")

    budgeted = [m for m in util["models"] if m["budget_limit_usd"] is not None]
    if budgeted:
        print(f"\n  Models with budgets ({len(budgeted)}):\n")
        for m in budgeted:
            limit = m["budget_limit_usd"]
            utilization = (m["spend_30d"] / limit * 100) if limit > 0 else 0
            status = "OVER" if utilization > 100 else "WARN" if utilization > 80 else "OK"
            print(
                f"    {m['model']:30s}  "
                f"${m['spend_30d']:>10.4f} / ${limit:>10.2f}  "
                f"{utilization:5.1f}%  [{status}]  "
                f"action={m['budget_action']}  period={m['period_type']}"
            )
    else:
        print("\n  No models with budget limits configured.")

    unbudgeted = [m for m in util["models"] if m["budget_limit_usd"] is None and m["spend_30d"] > 0]
    if unbudgeted:
        print(f"\n  Models without budgets ({len(unbudgeted)}):\n")
        for m in sorted(unbudgeted, key=lambda x: -x["spend_30d"])[:5]:
            print(f"    {m['model']:30s}  ${m['spend_30d']:>10.4f}  {m['request_count']} requests")

    print("\n=== Drill-Through Targets ===\n")
    print("  /budgets               — Manage budget limits and overrides")
    print("  /budgets?view=detail   — Budget detail with utilization history")
    print("  /budgets?view=notifications — Budget notification endpoints")
    print("  /billing               — Billing periods and attribution")
    print("  /chargeback            — Chargeback attribution rules")
    print("  /model-budgets         — Per-model budget controls")
    print("  /ledger                — Full ledger snapshots")


if __name__ == "__main__":
    main()
