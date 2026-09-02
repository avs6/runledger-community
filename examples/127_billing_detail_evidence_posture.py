"""
Example: Billing detail evidence posture.

Queries the billing-detail-evidence-posture analytics endpoint and prints
identity context, gateway context, observe context, build context, and spend.

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
    posture = api("GET", "/analytics/billing-detail-evidence-posture")
    print("Billing Detail — Evidence Posture")
    print("=" * 50)

    ic = posture["identity_context"]
    print(f"\nIdentity Context:")
    print(f"  Users:         {ic['workspace_users']}")
    print(f"  API Keys:      {ic['api_keys']}")
    print(f"  Access Groups: {ic['access_groups']}")

    gc = posture["gateway_context"]
    print(f"\nGateway Context:")
    print(f"  Active routes:   {gc['active_routes']}")
    print(f"  Distinct models: {gc['distinct_models_30d']}")

    oc = posture["observe_context"]
    print(f"\nObserve Context:")
    print(f"  Sessions 30d: {oc['sessions_30d']}")
    print(f"  Requests 30d: {oc['requests_30d']}")

    bc = posture["build_context"]
    print(f"\nBuild Context:")
    print(f"  Replay experiments: {bc['replay_experiments']}")

    sp = posture["spend_context"]
    print(f"\nSpend Context:")
    print(f"  30d spend:  ${sp['total_spend_30d']:.2f}")


if __name__ == "__main__":
    main()
