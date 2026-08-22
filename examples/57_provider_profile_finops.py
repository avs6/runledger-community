"""
Example: Provider-profile FinOps posture and budget override scoping.

Demonstrates creating a budget scoped to a provider profile, adding an
override, and querying the provider-profile financial posture endpoint.

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
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    return response.json() if response.content else None


def main():
    profiles = api("GET", "/providers/pricing")
    items = profiles.get("items", [])
    if not items:
        print("No provider profiles found — import pricing first.")
        return

    profile = items[0]
    profile_id = profile["id"]
    print(f"Using provider profile: {profile['provider']}/{profile['model']} ({profile_id})")

    print("\n--- Creating budget scoped to provider profile ---")
    budget = api("POST", "/budgets", {
        "scope_type": "provider_profile",
        "scope_id": profile_id,
        "period_type": "monthly",
        "limit_usd": 250.00,
        "action": "notify",
    })
    budget_id = budget["id"]
    print(f"Created budget {budget_id} (limit: $250.00)")

    print("\n--- Creating budget override ---")
    override = api("POST", f"/budgets/{budget_id}/override", {
        "override_limit_usd": 500.00,
        "starts_at": "2026-08-01T00:00:00Z",
        "expires_at": "2026-08-31T23:59:59Z",
        "reason": "End-of-quarter spike expected",
    })
    print(f"Created override {override['id']} (new limit: $500.00)")

    print("\n--- Provider Profile FinOps Posture ---")
    posture = api("GET", f"/analytics/provider-profile-finops-posture?profile_id={profile_id}")
    print(json.dumps(posture, indent=2))

    print("\n--- Listing budget overrides ---")
    overrides = api("GET", f"/budgets/{budget_id}/overrides")
    print(f"Override count: {overrides['total']}")
    for ov in overrides.get("items", []):
        print(f"  {ov['id']}: ${ov['override_limit_usd']} ({ov['status']})")


if __name__ == "__main__":
    main()
