"""
Example: Budget scope governance posture.

Queries the budget-scope-governance-posture analytics endpoint and prints
identity context, runtime context, governance context, and spend.

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
    posture = api("GET", "/analytics/budget-scope-governance-posture")
    print("Budgets — Scope & Governance Posture")
    print("=" * 50)

    ident = posture["identity_context"]
    print(f"\nIdentity Context:")
    print(f"  Users:          {ident['workspace_users']}")
    print(f"  API keys:       {ident['api_keys']}")
    print(f"  Access groups:  {ident['access_groups']}")
    print(f"  Hub models:     {ident['hub_models']}")

    rt = posture["runtime_context"]
    print(f"\nRuntime Context:")
    print(f"  Routes:           {rt['routes']}")
    print(f"  Active providers: {rt['active_providers_30d']}")
    print(f"  Cache configs:    {rt['cache_configs']}")

    gov = posture["governance_context"]
    print(f"\nGovernance Context:")
    print(f"  Alert rules:    {gov['alert_rules']}")
    print(f"  Audit events:   {gov['audit_events_30d']}")
    print(f"  Tags:           {gov['tags']}")

    sp = posture["spend_context"]
    print(f"\nSpend Context:")
    print(f"  30d spend:  ${sp['total_spend_30d']:.2f}")


if __name__ == "__main__":
    main()
