"""
examples/110_audit_log_runtime_scope.py

Demonstrates audit log evidence lineage across gateway,
observe, and FinOps runtime layers:

1. Fetch the audit log runtime posture
2. List recent audit events
3. Print evidence lineage summary

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
        posture = client.get("/analytics/audit-log-runtime-posture").json()
        print("=== Audit Log Evidence Lineage ===")
        print(f"  Evidence: {posture['evidence_scope']['audit_events_30d']} events 30d, "
              f"{posture['evidence_scope']['workspace_users']} users, "
              f"{posture['evidence_scope']['active_api_keys']} API keys")
        print(f"  Gateway: {posture['gateway_lineage']['guardrail_rules']} guardrail rules, "
              f"{posture['gateway_lineage']['cache_configs']} cache configs, "
              f"{posture['gateway_lineage']['rate_limited_routes']} rate-limited routes")
        print(f"  Observe: {posture['observe_lineage']['runs_30d']} runs, "
              f"{posture['observe_lineage']['provider_calls_30d']} provider calls 30d")
        print(f"  FinOps: {posture['finops_lineage']['active_budgets']} budgets, "
              f"{posture['finops_lineage']['ledger_snapshots_30d']} ledger snapshots 30d")

        events = client.get("/audit-events", params={"limit": "5"}).json()
        items = events.get("items", [])
        print(f"\n  Recent events: {len(items)}")
        for ev in items:
            print(f"    - {ev['action']} on {ev.get('target_type', '?')} at {ev['created_at']}")


if __name__ == "__main__":
    main()
