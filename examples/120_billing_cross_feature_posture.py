"""
Example: Billing cross-feature posture.

Queries the billing-cross-feature-posture analytics endpoint and prints
gateway context, safety context, platform context, and spend context.

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
    posture = api("GET", "/analytics/billing-cross-feature-posture")
    print("Billing — Cross-Feature Posture")
    print("=" * 50)

    gw = posture["gateway_context"]
    print(f"\nGateway Context:")
    print(f"  Routes:             {gw['routes']}")
    print(f"  Active providers:   {gw['active_providers_30d']}")
    print(f"  Cache configs:      {gw['cache_configs']}")
    print(f"  Rate limit endpoints: {gw['rate_limit_endpoints']}")
    print(f"  Distinct models:    {gw['distinct_models_30d']}")

    sf = posture["safety_context"]
    print(f"\nSafety Context:")
    print(f"  Tool registry:  {sf['tool_registry_count']}")
    print(f"  Alert rules:    {sf['alert_rules']}")
    print(f"  Audit events:   {sf['audit_events_30d']}")
    print(f"  Tags:           {sf['tags']}")

    pl = posture["platform_context"]
    print(f"\nPlatform Context:")
    print(f"  Organizations:  {pl['total_organizations']}")

    sp = posture["spend_context"]
    print(f"\nSpend Context:")
    print(f"  30d spend:  ${sp['total_spend_30d']:.2f}")


if __name__ == "__main__":
    main()
