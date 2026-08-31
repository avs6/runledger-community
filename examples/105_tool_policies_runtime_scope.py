"""
examples/105_tool_policies_runtime_scope.py

Demonstrates tool policies runtime scope and evidence across
gateway enforcement, observability, budget context, and ledger
integration:

1. Fetch the tool policies runtime posture
2. List active tool policies
3. Print a cross-suite scope summary

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
        posture = client.get("/analytics/tool-policies-runtime-posture").json()
        print("=== Tool Policies Runtime Scope ===")
        print(f"  Scope: {posture['scope_context']['total_workspaces']} workspaces, "
              f"{posture['scope_context']['workspace_scoped_policies']} workspace policies, "
              f"{posture['scope_context']['access_group_scoped_policies']} access-group policies")
        print(f"  Gateway: {posture['gateway_enforcement']['model_routes']} routes, "
              f"{posture['gateway_enforcement']['guardrail_rules']} guardrail rules, "
              f"{posture['gateway_enforcement']['guardrail_events_30d']} events 30d")
        print(f"  Observe: {posture['observe_evidence']['policy_violations_30d']} violations, "
              f"{posture['observe_evidence']['request_flows_30d']} request flows, "
              f"{posture['observe_evidence']['monitoring_alerts_30d']} alerts 30d")
        print(f"  Budgets: {posture['budget_context']['total_budgets']} active, "
              f"{posture['budget_context']['budget_notifications_30d']} notifications 30d")
        print(f"  Ledger: {posture['ledger_context']['ledger_snapshots']} snapshots, "
              f"{posture['ledger_context']['ledger_entries_30d']} entries 30d")

        policies = client.get("/tool-policies", params={"include_inactive": False, "limit": 50}).json()
        items = policies.get("items", [])
        print(f"\n  Active policies: {len(items)}")
        for p in items[:10]:
            print(f"    - {p['name']} ({p['action']}) scope={p['scope_type']} tool={p['tool_name']}")


if __name__ == "__main__":
    main()
