"""
examples/95_tags_budget_attribution.py

Demonstrates the tags-to-FinOps budget attribution bridge:

1. Fetch the tags FinOps budget posture (tagged spend, tag-scoped budgets, chargeback rules)
2. List tags with active spend
3. List budgets scoped to feature_tag
4. Print a summary of tag-driven budget attribution

Requires RUNLEDGER_API_KEY.
"""

from __future__ import annotations

import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")

if not API_KEY:
    print("Error: RUNLEDGER_API_KEY not set", file=sys.stderr)
    sys.exit(1)

HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def check(resp: httpx.Response, label: str) -> dict:
    if resp.status_code not in (200, 201, 204):
        print(f"{label} failed: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    if resp.status_code == 204:
        return {}
    return resp.json()


def main() -> None:
    client = httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=30)

    posture = check(
        client.get("/analytics/tags-finops-budget-posture"),
        "Tags FinOps budget posture",
    )
    print("=== Tags FinOps Budget Attribution Posture ===")
    tc = posture.get("tag_context", {})
    bc = posture.get("budget_context", {})
    cc = posture.get("chargeback_context", {})
    sc = posture.get("spend_context", {})
    print(f"  Total tags:              {tc.get('total_tags', 0)}")
    print(f"  Active tags:             {tc.get('active_tags', 0)}")
    print(f"  Active auto-rules:       {tc.get('active_auto_rules', 0)}")
    print(f"  Distinct tags w/ spend:  {tc.get('distinct_tags_with_spend', 0)}")
    print(f"  Tag-scoped budgets:      {bc.get('tag_scoped_budgets', 0)}")
    print(f"  Total budget limit:      ${bc.get('total_budget_limit_usd', 0):.2f}")
    print(f"  Tag dimension rules:     {cc.get('tag_dimension_rules', 0)}")
    print(f"  Tagged spend (30d):      ${sc.get('tagged_spend_30d', 0):.2f}")
    print(f"  Tagged call count:       {sc.get('tagged_call_count', 0)}")
    print(f"  Total spend (30d):       ${sc.get('total_spend_30d', 0):.2f}")

    tags = check(client.get("/tags", params={"include_inactive": False}), "Tags list")
    items = tags.get("items", [])
    print(f"\n=== Active Tags ({len(items)}) ===")
    for t in items[:10]:
        print(f"  {t['category']}/{t['key']}={t['value']}")

    budgets = check(client.get("/budgets"), "Budgets list")
    tag_budgets = [
        b for b in budgets.get("items", []) if b.get("scope_type") == "feature_tag"
    ]
    print(f"\n=== Tag-Scoped Budgets ({len(tag_budgets)}) ===")
    for b in tag_budgets[:10]:
        print(
            f"  {b['name']} — scope={b.get('scope_ref','*')} "
            f"limit=${b.get('limit_usd', 0):.2f} "
            f"({b.get('period_type', 'monthly')})"
        )

    print("\nDone.")


if __name__ == "__main__":
    main()
