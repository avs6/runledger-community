"""
Example: workspace chargeback workflow.

This walks through the Bundle C chargeback surface:
1. create a workflow-tag chargeback rule
2. review the current period allocation report
3. export finance-ready evidence
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
    period = f"{today.year}-{today.month:02d}"

    rule = api(
        "POST",
        "/billing/chargeback-rules",
        data=json.dumps(
            {
                "allocation_type": "direct",
                "dimension": "feature_tag",
                "weight": "1.0",
            }
        ),
    )
    print(f"Created chargeback rule: {rule['id']}")

    report = api(
        "GET",
        f"/billing/chargeback-report?period={period}&dimension=feature_tag",
    )
    first = report["items"][0]
    print("Chargeback period:", first["period"])
    print("Total cost:", first["total_cost_usd"])
    print("Breakdown rows:", len(first["breakdown"]))

    exported = api(
        "GET",
        f"/billing/chargeback-report/export?period={period}&dimension=feature_tag&format=json",
    )
    print("Exported report dimension:", exported["dimension"])


if __name__ == "__main__":
    main()
