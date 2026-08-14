"""
Example: billing period reconciliation workflow.

This walks through the Bundle B billing surface:
1. create a billing period
2. add a finance adjustment
3. inspect reconciliation + breakdown
4. export finance evidence
"""

from __future__ import annotations

import json
import os
from datetime import date

import requests

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8201")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")


def api(method: str, path: str, **kwargs):
    response = requests.request(
        method,
        f"{BASE_URL}{path}",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        timeout=30,
        **kwargs,
    )
    response.raise_for_status()
    if response.headers.get("content-type", "").startswith("application/json"):
        return response.json()
    return response.text


def main() -> None:
    if not API_KEY:
        raise SystemExit("Set RUNLEDGER_API_KEY before running this example.")

    today = date.today()
    period_start = today.replace(day=1).isoformat()
    period_end = today.isoformat()

    period = api(
        "POST",
        "/billing/periods",
        data=json.dumps({"period_start": period_start, "period_end": period_end}),
    )
    period_id = period["id"]
    print(f"Created period: {period_id}")

    adjustment = api(
        "POST",
        f"/billing/periods/{period_id}/adjustments",
        data=json.dumps(
            {
                "adjustment_type": "credit",
                "amount_usd": "3.50",
                "description": "Bundle B example credit",
                "reference_id": "bundle-b-example",
            }
        ),
    )
    print(f"Added adjustment: {adjustment['id']}")

    reconciliation = api("GET", f"/billing/periods/{period_id}/reconciliation")
    print("Reconciliation status:", reconciliation["status"])

    breakdown = api("GET", f"/billing/periods/{period_id}/breakdown")
    print("Applications in breakdown:", len(breakdown["by_application"]))

    signed_export = api("GET", f"/billing/periods/{period_id}/export?format=signed_json")
    print("Signed export rows:", len(signed_export["rows"]))


if __name__ == "__main__":
    main()
