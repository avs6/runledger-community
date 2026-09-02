"""
Example: Billing org scope posture.

Queries the billing-org-scope-posture analytics endpoint and prints
billing period counts, org scope (users, access groups, API keys),
attribution context, and 30-day spend.

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
    posture = api("GET", "/analytics/billing-org-scope-posture")
    print("Billing Org Scope Posture")
    print("=" * 50)

    bc = posture["billing_context"]
    print(f"\nBilling Context:")
    print(f"  Total periods:  {bc['total_periods']}")
    print(f"  Open periods:   {bc['open_periods']}")
    print(f"  Closed periods: {bc['closed_periods']}")
    print(f"  Total billed:   ${bc['total_billed_usd']:.2f}")

    oc = posture["org_context"]
    print(f"\nOrg Scope:")
    print(f"  Workspace users:  {oc['workspace_users']}")
    print(f"  Access groups:    {oc['access_groups']}")
    print(f"  API keys:         {oc['api_keys']}")

    ac = posture["attribution_context"]
    print(f"\nAttribution Context (30d):")
    print(f"  Calls:          {ac['calls_30d']}")
    print(f"  Distinct models: {ac['distinct_models']}")
    print(f"  Avg cost/call:  ${ac['avg_cost_per_call']:.6f}")

    sc = posture["spend_context"]
    print(f"\nSpend Context:")
    print(f"  Total spend (30d):   ${sc['total_spend_30d']:.2f}")
    print(f"  Distinct models (30d): {sc['distinct_models_30d']}")


if __name__ == "__main__":
    main()
