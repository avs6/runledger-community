"""
Example: Chargeback attribution posture.

Queries the chargeback-attribution-posture analytics endpoint and prints
identity context, runtime context, monitoring context, optimization, and spend.

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
    posture = api("GET", "/analytics/chargeback-attribution-posture")
    print("Chargeback — Attribution Posture")
    print("=" * 50)

    ic = posture["identity_context"]
    print(f"\nIdentity Context:")
    print(f"  Users:         {ic['workspace_users']}")
    print(f"  API Keys:      {ic['api_keys']}")
    print(f"  Access Groups: {ic['access_groups']}")

    rt = posture["runtime_context"]
    print(f"\nRuntime Context:")
    print(f"  Cache configs:    {rt['cache_configs']}")
    print(f"  Cache savings:    ${rt['cache_hit_savings_usd']:.2f}")
    print(f"  Chargeback rules: {rt['chargeback_rules']}")

    mn = posture["monitoring_context"]
    print(f"\nMonitoring Context:")
    print(f"  Alert rules:   {mn['alert_rules']}")
    print(f"  Audit events:  {mn['audit_events_30d']}")
    print(f"  Tags:          {mn['tags']}")

    oc = posture["optimization_context"]
    print(f"\nOptimization Context:")
    print(f"  Chargeback rules: {oc['chargeback_rules']}")
    print(f"  Cache savings:    ${oc['cache_savings_usd']:.2f}")

    sp = posture["spend_context"]
    print(f"\nSpend Context:")
    print(f"  30d spend:  ${sp['total_spend_30d']:.2f}")


if __name__ == "__main__":
    main()
