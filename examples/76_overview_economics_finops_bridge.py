"""
Example: Overview & Economics FinOps budget bridge.

Demonstrates the overview-to-budget and model-usage-to-budget investigation flow:
1. Fetch the workspace budget rollup (budgets, limits, spend, breaches)
2. Fetch per-model budget utilization (spend vs. model budgets, scope_type=model)
3. Identify models exceeding or approaching budget limits
4. Drill into budget detail and billing period context

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
    print("=== Workspace Budget Rollup ===\n")
    ctx = get("/context?entity=workspace")
    print("  Workspace context: " + ", ".join(f"{i['label']}={i['value']}" for i in ctx["items"]))
    rollup = get("/budgets/rollup?scope=workspace")
    print(f"  Active budgets: {rollup['active_budget_count']} / {rollup['budget_count']} total")
    print(f"  Total limit:    ${float(rollup['limit_usd']):.2f}")
    print(f"  Current spend:  ${float(rollup['current_spend_usd']):.2f}")
    print(f"  Exceeded:       {rollup['exceeded_count']}  at risk: {rollup['at_risk_count']}")

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
    print("  /budgets?scope_type=model — Model budgets (scope_type=model)")
    print("  /ledger                — Full ledger snapshots")


if __name__ == "__main__":
    main()
