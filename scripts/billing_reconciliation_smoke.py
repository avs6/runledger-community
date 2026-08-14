"""
Bundle B smoke script for billing and reconciliation.

Usage:
  RUNLEDGER_BASE_URL=http://localhost:8201
  RUNLEDGER_API_KEY=...
  python scripts/billing_reconciliation_smoke.py
"""

from __future__ import annotations

import json
import os
from datetime import date

import requests

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8201")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")


def call(method: str, path: str, payload: dict | None = None):
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
    if not API_KEY:
        raise SystemExit("RUNLEDGER_API_KEY is required")

    today = date.today()
    period = call(
        "POST",
        "/billing/periods",
        {"period_start": today.replace(day=1).isoformat(), "period_end": today.isoformat()},
    )
    period_id = period["id"]
    print(f"[billing] created period {period_id}")

    adjustment = call(
        "POST",
        f"/billing/periods/{period_id}/adjustments",
        {
            "adjustment_type": "surcharge",
            "amount_usd": "1.25",
            "description": "Smoke-test surcharge",
            "reference_id": "smoke-bundle-b",
        },
    )
    print(f"[billing] created adjustment {adjustment['id']}")

    reconciliation = call("GET", f"/billing/periods/{period_id}/reconciliation")
    print(f"[billing] reconciliation status={reconciliation['status']}")

    breakdown = call("GET", f"/billing/periods/{period_id}/breakdown")
    print(f"[billing] application groups={len(breakdown['by_application'])}")

    policies = call("GET", "/billing/shared-cost-policies")
    print(f"[billing] shared-cost policies={len(policies['items'])}")

    exported = call("GET", f"/billing/periods/{period_id}/export?format=signed_json")
    print(f"[billing] export rows={len(exported['rows'])}")

    print("[billing] smoke complete")


if __name__ == "__main__":
    main()
