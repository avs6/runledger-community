"""
examples/112_tags_runtime_scope.py

Demonstrates tags taxonomy attribution across governance,
observe, and FinOps runtime layers:

1. Fetch the tags runtime posture
2. List active tags
3. Print cross-suite attribution summary

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


def main() -> None:
    with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=30) as client:
        posture = client.get("/analytics/tags-runtime-posture").json()
        print("=== Tags Taxonomy Attribution ===")
        print(f"  Taxonomy: {posture['taxonomy_scope']['active_tags']} active / "
              f"{posture['taxonomy_scope']['total_tags']} total tags, "
              f"{posture['taxonomy_scope']['workspace_users']} users")
        print(f"  Governance: {posture['governance_attribution']['tool_policies']} policies, "
              f"{posture['governance_attribution']['audit_events_30d']} audit events 30d, "
              f"{posture['governance_attribution']['guardrail_rules']} guardrail rules")
        print(f"  Observe: {posture['observe_attribution']['runs_30d']} runs, "
              f"{posture['observe_attribution']['provider_calls_30d']} provider calls 30d")
        print(f"  FinOps: {posture['finops_attribution']['active_budgets']} budgets, "
              f"{posture['finops_attribution']['chargeback_rules']} chargeback rules")

        tags = client.get("/tags", params={"limit": "10"}).json()
        items = tags.get("items", [])
        print(f"\n  Active tags: {len(items)}")
        for t in items[:5]:
            print(f"    - {t['key']}:{t['value']} ({t['category']})")


if __name__ == "__main__":
    main()
