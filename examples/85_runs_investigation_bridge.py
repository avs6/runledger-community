"""
Example 85 — Runs Investigation Bridge

Demonstrates the WU-013 enriched investigation context on the Runs list:
governance posture (approvals, data capture), org identity (access groups),
and FinOps budget posture with budget detail drill-through.

Usage:
    export RUNLEDGER_API_KEY="rl_test_..."
    python examples/85_runs_investigation_bridge.py
"""

import os
import httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.getenv("RUNLEDGER_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {KEY}"}


def main() -> None:
    with httpx.Client(base_url=BASE, headers=HEADERS, timeout=30) as c:
        print("=== Governance Posture (Runs) ===")
        r = c.get("/analytics/investigation-governance-posture")
        r.raise_for_status()
        g = r.json()
        print(f"  Filtered runs: {g['filtered_runs']}")
        print(f"  Tool policies: {g['tool_governance']['active_tool_policies']}")
        print(f"  Security events: {g['security']['events']}")
        print(f"  Approvals: {g['governance_pack']['approvals']}")
        print(f"  Capture policies: {g['governance_pack']['capture_policies']}")

        print("\n=== Scope Posture (access groups) ===")
        r = c.get("/analytics/overview-scope-posture")
        r.raise_for_status()
        s = r.json()
        ag = s["access_group_context"]
        print(f"  Access groups: {ag['active_access_groups']}/{ag['access_groups']} ({ag['total_members']} members)")

        print("\n=== FinOps Budget Posture (Runs) ===")
        r = c.get("/analytics/investigation-finops-budget-posture")
        r.raise_for_status()
        f = r.json()
        print(f"  Budgets: {f['budget_context']['active_budgets']}/{f['budget_context']['budgets']}")
        print(f"  Breaches: {f['budget_context']['breach_count']}")
        print(f"  Spend 30d: ${f['spend_context']['total_spend_30d']:.2f}")


if __name__ == "__main__":
    main()
