"""
Example: FinOps internal posture.

Queries the finops-internal-posture analytics endpoint and prints
budget totals, billing periods, chargeback rules, ledger snapshots,
overrides, notifications, and 30-day spend across all FinOps sub-features.

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
        data=json.dumps(payload) if payload is not None else None,
        timeout=30,
    )
    response.raise_for_status()
    if response.headers.get("content-type", "").startswith("application/json"):
        return response.json()
    return response.text


def main() -> None:
    posture = api("GET", "/analytics/finops-internal-posture")
    print("FinOps Internal Posture")
    print("=" * 50)

    bc = posture["budget_context"]
    print(f"\nBudget Context:")
    print(f"  Total budgets:   {bc['total_budgets']}")
    print(f"  Active budgets:  {bc['active_budgets']}")
    print(f"  Total limit:     ${bc['total_limit_usd']:.2f}")
    print(f"  Breached:        {bc['breached_budgets']}")

    bl = posture["billing_context"]
    print(f"\nBilling Context:")
    print(f"  Total periods:  {bl['total_periods']}")
    print(f"  Open periods:   {bl['open_periods']}")
    print(f"  Total billed:   ${bl['total_billed_usd']:.2f}")

    cc = posture["chargeback_context"]
    print(f"\nChargeback Context:")
    print(f"  Total rules:  {cc['total_rules']}")
    print(f"  Active rules: {cc['active_rules']}")

    lc = posture["ledger_context"]
    print(f"\nLedger Context:")
    print(f"  Total snapshots:     {lc['total_snapshots']}")
    print(f"  Latest snapshot date: {lc['latest_snapshot_date']}")

    oc = posture["override_context"]
    print(f"\nOverride Context:")
    print(f"  Total overrides:  {oc['total_overrides']}")
    print(f"  Active overrides: {oc['active_overrides']}")

    nc = posture["notification_context"]
    print(f"\nNotification Context:")
    print(f"  Total notifications: {nc['total_notifications']}")
    print(f"  30d spend:           ${nc['spend_30d']:.2f}")


if __name__ == "__main__":
    main()
