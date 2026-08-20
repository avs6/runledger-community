"""
Example: user financial exposure.

Fetches the financial summary for a platform user — 30-day and total spend,
run/call counts, and any budgets scoped to that user — then prints the
handoff links to runs, analytics, and chargeback for further investigation.
"""

from __future__ import annotations

import json
import os
import urllib.request


BASE_URL = os.environ.get("RUNLEDGER_BASE_URL", "http://localhost:8000").rstrip("/")
API_KEY = os.environ["RUNLEDGER_API_KEY"]
USER_ID = os.environ["RUNLEDGER_USER_ID"]


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
    finance = api_get(f"/users/{USER_ID}/finance")

    print("User Financial Exposure")
    print("=======================")
    print(f"User:           {finance['full_name'] or finance['email']}")
    print(f"Email:          {finance['email']}")
    print(f"User ID:        {finance['user_id']}")
    print(f"30d spend:      ${float(finance['spend_30d_usd']):,.2f}")
    print(f"Total spend:    ${float(finance['spend_total_usd']):,.2f}")
    print(f"30d runs:       {finance['run_count_30d']}")
    print(f"30d calls:      {finance['call_count_30d']}")
    print()

    budgets = finance.get("budgets", [])
    print(f"Budgets ({len(budgets)})")
    print("-" * 40)
    if budgets:
        for b in budgets:
            status = "active" if b["is_active"] else "inactive"
            print(f"  {b['budget_id']}  {b['period_type']}  ${float(b['limit_usd']):,.2f}  [{status}]")
    else:
        print("  No budgets scoped to this user.")

    print()
    print("Investigation links")
    print("===================")
    uid = finance["user_id"]
    print(f"Runs:       {BASE_URL}/runs?end_user_id={uid}")
    print(f"Analytics:  {BASE_URL}/analytics?scope=workspace&end_user_id={uid}")
    print(f"Chargeback: {BASE_URL}/chargeback?dimension=end_user&end_user_id={uid}")


if __name__ == "__main__":
    main()
