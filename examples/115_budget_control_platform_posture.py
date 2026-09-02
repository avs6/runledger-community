"""
Example: Budget control platform posture.

Queries the budget-control-platform-posture analytics endpoint (platform
admin only) and prints cross-org budget governance totals, per-org budget
breakdowns, override context, and platform-wide spend.

Required env vars:
  RUNLEDGER_BASE_URL
  RUNLEDGER_API_KEY  (must belong to a platform admin)
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
    posture = api("GET", "/analytics/budget-control-platform-posture")
    print("Budget Control Platform Posture")
    print("=" * 50)

    pt = posture["platform_totals"]
    print(f"\nPlatform Totals:")
    print(f"  Organizations:   {pt['organizations']}")
    print(f"  Total budgets:   {pt['total_budgets']}")
    print(f"  Total limit:     ${pt['total_limit_usd']:.2f}")
    print(f"  Total breaches:  {pt['total_breaches']}")

    print(f"\nPer-Org Budget Breakdown:")
    for org in posture["org_budgets"]:
        breach_flag = " [BREACHED]" if org["breach_count"] > 0 else ""
        print(f"  {org['org_name']:30s}  budgets={org['budget_count']}  limit=${org['total_limit_usd']:.2f}{breach_flag}")

    oc = posture["override_context"]
    print(f"\nOverride Context:")
    print(f"  Total overrides:  {oc['total_overrides']}")
    print(f"  Active overrides: {oc['active_overrides']}")

    sc = posture["spend_context"]
    print(f"\nSpend Context:")
    print(f"  Total spend (30d):   ${sc['total_spend_30d']:.2f}")
    print(f"  Distinct models (30d): {sc['distinct_models_30d']}")


if __name__ == "__main__":
    main()
