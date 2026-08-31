"""
examples/109_alert_rules_runtime_scope.py

Demonstrates alert rules runtime scope and evidence across
gateway runtime, monitoring ops, and FinOps accountability:

1. Fetch the alert rules runtime posture
2. List active alert rules
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
        posture = client.get("/analytics/alert-rules-runtime-posture").json()
        print("=== Alert Rules Runtime Scope ===")
        print(f"  Ops: {posture['ops_context']['active_alert_rules']} active rules, "
              f"{posture['ops_context']['alert_firings_30d']} firings 30d, "
              f"{posture['ops_context']['total_workspaces']} workspaces")
        print(f"  Gateway: {posture['gateway_runtime']['model_routes']} routes, "
              f"{posture['gateway_runtime']['guardrail_rules']} guardrail rules, "
              f"{posture['gateway_runtime']['rate_limited_routes']} rate-limited")
        print(f"  Observe: {posture['observe_evidence']['runs_30d']} runs, "
              f"{posture['observe_evidence']['provider_calls_30d']} provider calls 30d")
        print(f"  FinOps: {posture['finops_context']['chargeback_rules']} chargeback rules, "
              f"{posture['finops_context']['active_budgets']} budgets, "
              f"{posture['finops_context']['budget_notifications_30d']} notifications 30d")

        rules = client.get("/alert-rules", params={"include_inactive": "false"}).json()
        items = rules.get("items", [])
        print(f"\n  Active rules: {len(items)}")
        for r in items[:5]:
            print(f"    - {r['name']} ({r['metric']} {r['operator']} {r['threshold']})")


if __name__ == "__main__":
    main()
