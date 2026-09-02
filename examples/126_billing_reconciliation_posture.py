"""
Example: Billing reconciliation posture.

Queries the billing-reconciliation-posture analytics endpoint and prints
identity context, provider context, optimization context, evidence, and spend.

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
    posture = api("GET", "/analytics/billing-reconciliation-posture")
    print("Billing Periods — Reconciliation Posture")
    print("=" * 50)

    ic = posture["identity_context"]
    print(f"\nIdentity Context:")
    print(f"  Users:         {ic['workspace_users']}")
    print(f"  API Keys:      {ic['api_keys']}")
    print(f"  Access Groups: {ic['access_groups']}")

    pc = posture["provider_context"]
    print(f"\nProvider Context:")
    print(f"  Active providers: {pc['active_providers_30d']}")
    print(f"  Cache configs:    {pc['cache_configs']}")
    print(f"  Cache savings:    ${pc['cache_hit_savings_usd']:.2f}")
    print(f"  Distinct models:  {pc['distinct_models_30d']}")

    oc = posture["optimization_context"]
    print(f"\nOptimization Context:")
    print(f"  Billing periods: {oc['billing_periods']}")
    print(f"  Alert rules:     {oc['alert_rules']}")
    print(f"  Cache savings:   ${oc['cache_savings_usd']:.2f}")

    ev = posture["evidence_context"]
    print(f"\nEvidence Context:")
    print(f"  Audit events:  {ev['audit_events_30d']}")
    print(f"  Alert rules:   {ev['alert_rules']}")

    sp = posture["spend_context"]
    print(f"\nSpend Context:")
    print(f"  30d spend:  ${sp['total_spend_30d']:.2f}")


if __name__ == "__main__":
    main()
