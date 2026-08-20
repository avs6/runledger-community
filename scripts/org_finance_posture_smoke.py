"""
Smoke check for the org financial posture rollup.

Usage:
  RUNLEDGER_API_KEY=... python scripts/org_finance_posture_smoke.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request


BASE_URL = os.environ.get("RUNLEDGER_BASE_URL", "http://localhost:8000").rstrip("/")
API_KEY = os.environ.get("RUNLEDGER_API_KEY")


def get_json(path: str) -> dict:
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        method="GET",
    )
    with urllib.request.urlopen(req) as response:  # noqa: S310 - smoke for configured target
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    if not API_KEY:
        print("RUNLEDGER_API_KEY is required", file=sys.stderr)
        return 2

    finance = get_json("/org/finance")
    required_keys = [
        "workspaces",
        "org_spend_30d_usd",
        "active_budget_count",
        "active_override_count",
        "active_notification_count",
        "overdue_billing_period_count",
        "chargeback_rule_count",
        "ledger_readiness_status",
    ]
    missing = [key for key in required_keys if key not in finance]
    if missing:
        print(f"[org-finance] missing keys: {missing}", file=sys.stderr)
        return 1

    print(
        "[org-finance] "
        f"workspaces={len(finance['workspaces'])} "
        f"budgets={finance['active_budget_count']} "
        f"overdue_periods={finance['overdue_billing_period_count']} "
        f"ledger={finance['ledger_readiness_status']}"
    )
    print("[org-finance] smoke complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
