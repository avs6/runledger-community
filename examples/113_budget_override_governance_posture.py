"""
Example: Budget override governance posture.

Queries the budget-override-governance-posture analytics endpoint and prints
approval workflow context, alert rule coverage, audit events, governance
coverage, and tag attribution for budget overrides.

Required env vars:
  RUNLEDGER_BASE_URL
  RUNLEDGER_API_KEY
"""

from __future__ import annotations

import json
import os

import requests

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8201")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")


def api(method: str, path: str, payload: dict | None = None):
    response = requests.request(
        method,
        f"{BASE_URL}{path}",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        data=json.dumps(payload) if payload is not None else None,
        timeout=30,
    )
    response.raise_for_status()
    if response.headers.get("content-type", "").startswith("application/json"):
        return response.json()
    return response.text


def main() -> None:
    posture = api("GET", "/analytics/budget-override-governance-posture")
    print("Budget Override Governance Posture")
    print("=" * 50)

    ac = posture["approval_context"]
    print(f"\nApproval Context:")
    print(f"  Pending approvals:       {ac['pending_approvals']}")
    print(f"  Approved (30d):          {ac['approved_30d']}")
    print(f"  Denied (30d):            {ac['denied_30d']}")
    print(f"  Overrides with approval: {ac['overrides_with_approval']}")

    al = posture["alert_context"]
    print(f"\nAlert Context:")
    print(f"  Budget alert rules:  {al['budget_alert_rules']}")
    print(f"  Active alerts:       {al['active_budget_alerts']}")

    au = posture["audit_context"]
    print(f"\nAudit Context:")
    print(f"  Override audit events (30d): {au['override_audit_events_30d']}")
    print(f"  Total overrides:             {au['total_overrides']}")
    print(f"  Active overrides:            {au['active_overrides']}")

    gc = posture["governance_context"]
    print(f"\nGovernance Context:")
    print(f"  Approval coverage: {gc['approval_coverage_pct']}%")
    print(f"  Active overrides:  {gc['active_overrides']}")

    tc = posture["tag_context"]
    print(f"\nTag Context:")
    print(f"  Budget tags:   {tc['budget_tags']}")
    print(f"  Override tags: {tc['override_tags']}")


if __name__ == "__main__":
    main()
