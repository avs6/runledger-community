"""
Example: Economics, Outcomes, and Monitoring FinOps posture.

Demonstrates the economics/outcomes/monitoring-to-FinOps bridge:
1. Fetch the economics FinOps posture (budgets, overrides, notifications, ledger, spend)
2. Fetch the outcomes FinOps posture (budgets, billing periods, chargeback, outcomes)
3. Fetch the monitoring FinOps posture (budgets, overrides, notifications, billing, ledger)
4. Summarise budget health across all three surfaces

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
    print("=== Economics FinOps Posture ===\n")
    econ = get("/analytics/economics-finops-posture")
    bc = econ["budget_context"]
    print(f"  Active budgets: {bc['active_budgets']} / {bc['budgets']} total")
    print(f"  Total limit:    ${bc['total_limit_usd']:.2f}")
    print(f"  Breached:       {bc['breach_count']}")
    print(f"  Overrides:      {bc['overrides']} ({bc['active_overrides']} active)")

    nc = econ["notification_context"]
    print(f"\n  Notifications:   {nc['active_notifications']} active / {nc['notifications']} total")

    lc = econ["ledger_context"]
    print(f"  Ledger:          {lc['ledger_snapshots']} total, {lc['ledger_snapshots_30d']} in 30d")

    sc = econ["spend_context"]
    print(f"\n  Spend (30d):    ${sc['total_spend_30d']:.2f}")
    print(f"  Runs (30d):     {sc['total_runs_30d']}")

    blc = econ["billing_context"]
    print(f"\n  Billing periods: {blc['billing_periods']} ({blc['open_billing_periods']} open)")
    print(f"  Chargeback rules: {blc['chargeback_rules']}")

    print("\n=== Outcomes FinOps Posture ===\n")
    out = get("/analytics/outcomes-finops-posture")
    obc = out["budget_context"]
    print(f"  Active budgets: {obc['active_budgets']} / {obc['budgets']} total")
    print(f"  Total limit:    ${obc['total_limit_usd']:.2f}")
    print(f"  Breached:       {obc['breach_count']}")

    oblc = out["billing_context"]
    print(f"\n  Billing periods: {oblc['billing_periods']} ({oblc['open_billing_periods']} open)")
    print(f"  Chargeback rules: {oblc['chargeback_rules']}")

    osc = out["spend_context"]
    print(f"\n  Spend (30d):    ${osc['total_spend_30d']:.2f}")
    print(f"  Outcomes (30d): {osc['outcomes_30d']}")

    print("\n=== Monitoring FinOps Posture ===\n")
    mon = get("/analytics/monitoring-finops-posture")
    mbc = mon["budget_context"]
    print(f"  Active budgets: {mbc['active_budgets']} / {mbc['budgets']} total")
    print(f"  Breached:       {mbc['breach_count']}")
    print(f"  Overrides:      {mbc['overrides']} ({mbc['active_overrides']} active)")

    mnc = mon["notification_context"]
    print(f"\n  Notifications:   {mnc['active_notifications']} active / {mnc['notifications']} total")

    mlc = mon["ledger_context"]
    print(f"  Ledger:          {mlc['ledger_snapshots']} snapshots")

    mblc = mon["billing_context"]
    print(f"\n  Billing periods: {mblc['billing_periods']} ({mblc['open_billing_periods']} open)")
    print(f"  Chargeback rules: {mblc['chargeback_rules']}")

    print("\n=== Drill-Through Targets ===\n")
    print("  /budgets                     — Manage budget limits and breach actions")
    print("  /budgets?tab=overrides       — Budget overrides")
    print("  /budgets?tab=notifications   — Budget notification endpoints")
    print("  /billing                     — Billing periods and attribution")
    print("  /chargeback                  — Chargeback attribution rules")
    print("  /ledger                      — Full ledger snapshots")


if __name__ == "__main__":
    main()
