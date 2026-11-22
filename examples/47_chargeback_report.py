"""
Example: chargeback by cost center.

1. create two cost centers
2. map a workflow tag to them 60/40 with chargeback rules
3. read the cost-center report (rules applied to this month's billable cost)
4. export the by-workflow report for finance

Required env vars:
  RUNLEDGER_API_KEY   a workspace admin's key or session (cost centers and rules
                      need workspace admin; reports need billing access)
Optional:
  RUNLEDGER_BASE_URL  (default http://localhost:8201)
  RUNLEDGER_FEATURE_TAG  workflow tag to map (default: the costliest tag this month)
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

    by_tag = api("GET", f"/billing/chargeback-report?period={period}&dimension=feature_tag")
    rows = [r for r in by_tag["items"][0]["breakdown"] if r.get("dimension_key")]
    tag = os.getenv("RUNLEDGER_FEATURE_TAG") or (rows[0]["dimension_key"] if rows else None)
    if not tag:
        raise SystemExit("No workflow-tagged usage this month; send some traffic first.")

    support = api(
        "POST", "/billing/cost-centers", data=json.dumps({"name": "Support", "code": "SUP"})
    )
    platform = api(
        "POST", "/billing/cost-centers", data=json.dumps({"name": "Platform", "code": "PLT"})
    )
    for center, weight in ((support, "0.6"), (platform, "0.4")):
        rule = api(
            "POST",
            "/billing/chargeback-rules",
            data=json.dumps(
                {
                    "dimension": "feature_tag",
                    "dimension_value": tag,
                    "cost_center_id": center["id"],
                    "allocation_type": "shared_weight",
                    "weight": weight,
                }
            ),
        )
        print(f"Rule {rule['id']}: {tag} -> {center['name']} at {weight} ({rule['status']})")

    report = api("GET", f"/billing/chargeback-report/cost-centers?period={period}")
    print(f"Billable {report['total_billable_usd']}, unassigned {report['unassigned_usd']}")
    for row in report["rows"]:
        print(
            f"  {row['name']}: {row['total_usd']} (rules {row['direct_usd']}, shared {row['shared_usd']})"
        )

    exported = api(
        "GET",
        f"/billing/chargeback-report/export?period={period}&dimension=feature_tag&format=json",
    )
    print("Exported rows:", len(exported["breakdown"]))


if __name__ == "__main__":
    main()
