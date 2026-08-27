"""
examples/94_approvals_budget_alerts.py

Demonstrates the approvals-and-alert-rules-to-FinOps budget bridge:

1. Fetch the approvals/alert FinOps posture (budget increase requests, breaches, alert rules)
2. List pending budget-increase approvals
3. List alert rules filtered to budget metrics
4. Print a summary of budget governance posture

Requires RUNLEDGER_API_KEY.
"""

from __future__ import annotations

import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")

if not API_KEY:
    print("Error: RUNLEDGER_API_KEY not set", file=sys.stderr)
    sys.exit(1)

HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def check(resp: httpx.Response, label: str) -> dict:
    if resp.status_code not in (200, 201, 204):
        print(f"{label} failed: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    if resp.status_code == 204:
        return {}
    return resp.json()


def main() -> None:
    client = httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=30)

    posture = check(
        client.get("/analytics/approvals-alert-finops-posture"),
        "Approvals-alert FinOps posture",
    )
    print("=== Approvals & Alert Rules FinOps Budget Posture ===")
    ac = posture.get("approval_context", {})
    bc = posture.get("budget_context", {})
    alc = posture.get("alert_context", {})
    print(f"  Budget increase requests : {ac.get('budget_increase_total', 0)}")
    print(f"    Pending               : {ac.get('budget_increase_pending', 0)}")
    print(f"    Approved              : {ac.get('budget_increase_approved', 0)}")
    print(f"  Active budgets          : {bc.get('active_budgets', 0)}")
    print(f"  Total limit             : ${bc.get('total_limit', 0):,.2f}")
    print(f"  Active overrides        : {bc.get('active_overrides', 0)}")
    print(f"  Breaches (30d)          : {bc.get('breach_count_30d', 0)}")
    print(f"  Budget alert rules      : {alc.get('budget_alert_rules', 0)}")
    print(f"  Alert firings (30d)     : {alc.get('budget_alert_firings_30d', 0)}")

    approvals = check(
        client.get("/approvals", params={"status": "pending"}),
        "List pending approvals",
    )
    budget_approvals = [
        a for a in approvals.get("items", []) if a.get("request_type") == "budget_increase"
    ]
    print(f"\n=== Pending Budget-Increase Approvals ({len(budget_approvals)}) ===")
    for a in budget_approvals[:10]:
        print(f"  [{a['id'][:8]}] {a.get('request_type')} — {a.get('status')}")

    alerts = check(client.get("/alert-rules"), "List alert rules")
    budget_alerts = [
        r
        for r in alerts.get("items", [])
        if r.get("metric") in ("budget_utilization", "budget_breach_count")
    ]
    print(f"\n=== Budget Alert Rules ({len(budget_alerts)}) ===")
    for r in budget_alerts[:10]:
        op = ">" if r.get("operator") == "gt" else "<"
        print(f"  [{r['id'][:8]}] {r['name']}: {r['metric']} {op} {r.get('threshold')}")

    print("\nDone.")


if __name__ == "__main__":
    main()
