"""
examples/106_approvals_runtime_scope.py

Demonstrates approvals runtime scope and evidence across
requester context, gateway escalation, observability, monitoring,
and budget integration:

1. Fetch the approvals runtime posture
2. List recent approval requests
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
        posture = client.get("/analytics/approvals-runtime-posture").json()
        print("=== Approvals Runtime Scope ===")
        print(f"  Requesters: {posture['requester_context']['workspace_users']} users, "
              f"{posture['requester_context']['active_api_keys']} API keys, "
              f"{posture['requester_context']['total_workspaces']} workspaces")
        print(f"  Gateway: {posture['gateway_escalation']['model_routes']} routes, "
              f"{posture['gateway_escalation']['guardrail_rules']} guardrail rules")
        print(f"  Observe: {posture['observe_evidence']['runs_30d']} runs, "
              f"{posture['observe_evidence']['approval_linked_runs_30d']} approval-linked 30d")
        print(f"  Monitoring: {posture['monitoring_context']['active_alert_rules']} rules, "
              f"{posture['monitoring_context']['alert_firings_30d']} firings 30d")
        print(f"  Budgets: {posture['budget_context']['total_budgets']} active, "
              f"{posture['budget_context']['budget_increase_approvals_30d']} increase approvals 30d")

        approvals = client.get("/approvals", params={"limit": 10}).json()
        items = approvals.get("items", [])
        print(f"\n  Recent approvals: {len(items)}")
        for a in items[:10]:
            print(f"    - {a['request_type']} [{a['status']}] by {a.get('requester_id', 'unknown')[:8]}...")


if __name__ == "__main__":
    main()
