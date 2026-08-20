"""
Example: workspace chargeback workflow.

This walks through the Bundle C chargeback surface:
1. create a workflow-tag chargeback rule
2. review the current period allocation report
3. export finance-ready evidence

Optional env var:
  RUNLEDGER_ACCESS_GROUP_ID
    When set, the example requests an access-group-scoped report using
    the `access_group` dimension.
"""

from __future__ import annotations

import json
import os
from datetime import date

import requests

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8201")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")
ACCESS_GROUP_ID = os.getenv("RUNLEDGER_ACCESS_GROUP_ID", "")


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
    dimension = "access_group" if ACCESS_GROUP_ID else "feature_tag"
    access_group_qs = f"&access_group_id={ACCESS_GROUP_ID}" if ACCESS_GROUP_ID else ""

    rule = api(
        "POST",
        "/billing/chargeback-rules",
        data=json.dumps(
            {
                "allocation_type": "direct",
                "dimension": dimension,
                "weight": "1.0",
            }
        ),
    )
    print(f"Created chargeback rule: {rule['id']}")

    report = api(
        "GET",
        f"/billing/chargeback-report?period={period}&dimension={dimension}{access_group_qs}",
    )
    first = report["items"][0]
    print("Chargeback period:", first["period"])
    print("Total cost:", first["total_cost_usd"])
    print("Breakdown rows:", len(first["breakdown"]))

    exported = api(
        "GET",
        f"/billing/chargeback-report/export?period={period}&dimension={dimension}&format=json{access_group_qs}",
    )
    print("Exported report dimension:", exported["dimension"])


if __name__ == "__main__":
    main()
