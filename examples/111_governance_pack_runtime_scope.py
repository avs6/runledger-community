"""
examples/111_governance_pack_runtime_scope.py

Demonstrates governance pack compliance closure across
governance, monitoring, and FinOps evidence sources:

1. Fetch the governance pack runtime posture
2. Generate a governance audit pack
3. Print compliance packaging summary

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
        posture = client.get("/analytics/governance-pack-runtime-posture").json()
        print("=== Governance Pack Compliance Closure ===")
        print(f"  Scope: {posture['scope_context']['total_workspaces']} workspaces, "
              f"{posture['scope_context']['workspace_users']} users, "
              f"{posture['scope_context']['active_budgets']} budgets")
        print(f"  Sources: {posture['governance_sources']['guardrail_rules']} guardrail rules, "
              f"{posture['governance_sources']['audit_events_30d']} audit events 30d, "
              f"{posture['governance_sources']['active_tags']} tags")
        print(f"  Monitoring: {posture['monitoring_evidence']['alert_firings_30d']} alert firings 30d, "
              f"{posture['monitoring_evidence']['guardrail_events_30d']} guardrail events 30d")
        print(f"  FinOps: {posture['finops_evidence']['budget_notifications_30d']} budget notifications 30d, "
              f"{posture['finops_evidence']['ledger_snapshots_30d']} ledger snapshots 30d")

        pack = client.get("/governance/audit-pack", params={"from": "2024-01-01", "to": "2024-12-31"}).json()
        print(f"\n  Pack summary: {pack['summary']['total_requests']} requests, "
              f"${float(pack['summary']['total_cost_usd']):.2f} cost, "
              f"{pack['summary']['models_used']} models")


if __name__ == "__main__":
    main()
