"""
Example: Ledger cross-feature posture.

Queries the ledger-cross-feature-posture analytics endpoint and prints
org context, observe context, safety context, platform context, and ledger context.

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
    posture = api("GET", "/analytics/ledger-cross-feature-posture")
    print("Ledger — Cross-Feature Posture")
    print("=" * 50)

    org = posture["org_context"]
    print(f"\nOrg Context:")
    print(f"  Users:          {org['workspace_users']}")
    print(f"  Workspaces:     {org['workspaces']}")
    print(f"  Access groups:  {org['access_groups']}")

    obs = posture["observe_context"]
    print(f"\nObserve Context:")
    print(f"  Billing periods:  {obs['billing_periods']}")
    print(f"  30d spend:        ${obs['total_spend_30d']:.2f}")
    print(f"  Distinct models:  {obs['distinct_models_30d']}")

    sf = posture["safety_context"]
    print(f"\nSafety Context:")
    print(f"  Audit events:   {sf['audit_events_30d']}")
    print(f"  Tags:           {sf['tags']}")

    pl = posture["platform_context"]
    print(f"\nPlatform Context:")
    print(f"  Organizations:  {pl['total_organizations']}")

    lg = posture["ledger_context"]
    print(f"\nLedger Context:")
    print(f"  Snapshots:            {lg['total_snapshots']}")
    print(f"  Latest snapshot date: {lg['latest_snapshot_date']}")


if __name__ == "__main__":
    main()
