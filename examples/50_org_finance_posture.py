"""
Example: org financial posture summary.

Reads the org-level finance rollup from /org/finance and prints the key
handoff paths into the FinOps surfaces that own editing and investigation.
"""

from __future__ import annotations

import json
import os
import urllib.request


BASE_URL = os.environ.get("RUNLEDGER_BASE_URL", "http://localhost:8000").rstrip("/")
API_KEY = os.environ["RUNLEDGER_API_KEY"]


def api_get(path: str) -> dict:
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        method="GET",
    )
    with urllib.request.urlopen(req) as response:  # noqa: S310 - local/dev example
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    finance = api_get("/org/finance")

    print("Organization Finance Posture")
    print("============================")
    print(f"30d spend:          ${float(finance['org_spend_30d_usd']):,.2f}")
    print(f"Budget envelope:    ${float(finance['org_total_budget_limit_usd']):,.2f}")
    print(f"Active budgets:     {finance['active_budget_count']}")
    print(f"Active overrides:   {finance['active_override_count']}")
    print(f"Notifications:      {finance['active_notification_count']}")
    print(f"Overdue periods:    {finance['overdue_billing_period_count']}")
    print(
        "Chargeback ready:   "
        f"{finance['chargeback_ready_workspace_count']}/{len(finance['workspaces'])} workspaces"
    )
    print(f"Ledger readiness:   {finance['ledger_readiness_status']}")
    print()
    print("Next owner surfaces")
    print("===================")
    print(f"Budgets:    {BASE_URL}/budgets?tab=policies")
    print(f"Billing:    {BASE_URL}/billing")
    print(f"Chargeback: {BASE_URL}/chargeback?dimension=workspace")
    print(f"Compliance: {BASE_URL}/settings?tab=compliance")


if __name__ == "__main__":
    main()
