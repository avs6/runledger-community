"""
Example: Budget override exception posture.

Queries the budget-override-exception-posture analytics endpoint and prints
override lifecycle, approval workflow, runtime context, monitoring, and spend.

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
    posture = api("GET", "/analytics/budget-override-exception-posture")
    print("Budget Overrides — Exception Posture")
    print("=" * 50)

    ov = posture["override_context"]
    print(f"\nOverride Context:")
    print(f"  Total:     {ov['total_overrides']}")
    print(f"  Active:    {ov['active_overrides']}")
    print(f"  Expired:   {ov['expired_overrides']}")
    print(f"  Limit USD: ${ov['active_override_limit_usd']:.2f}")

    ap = posture["approval_context"]
    print(f"\nApproval Context:")
    print(f"  Pending:   {ap['pending_approvals']}")
    print(f"  Approved:  {ap['approved_30d']}")
    print(f"  Denied:    {ap['denied_30d']}")

    rt = posture["runtime_context"]
    print(f"\nRuntime Context:")
    print(f"  Active routes:       {rt['active_routes']}")
    print(f"  Rate-limited routes: {rt['rate_limited_routes']}")

    mn = posture["monitoring_context"]
    print(f"\nMonitoring Context:")
    print(f"  Alert rules:    {mn['alert_rules']}")
    print(f"  Audit events:   {mn['audit_events_30d']}")

    sp = posture["spend_context"]
    print(f"\nSpend Context:")
    print(f"  30d spend:  ${sp['total_spend_30d']:.2f}")


if __name__ == "__main__":
    main()
