"""
examples/103_governance_internal_cohesion.py

Demonstrates internal governance cohesion across Safety & Governance features:

1. Fetch the governance internal posture (tool registry, policies, approvals,
   data capture, security, alert rules, audit, tags)
2. List registered tools and active policies
3. Print a summary of cross-surface governance coverage

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
        posture = client.get("/analytics/governance-internal-posture").json()
        print("=== Governance Internal Posture ===")
        print(f"  Tool Registry: {posture['tool_registry_context']['total_tools']} tools "
              f"({posture['tool_registry_context']['enforced_tools']} enforced)")
        print(f"  Tool Policies: {posture['tool_policies_context']['active_policies']} active "
              f"/ {posture['tool_policies_context']['total_policies']} total")
        print(f"  Approvals: {posture['approvals_context']['pending_approvals']} pending, "
              f"{posture['approvals_context']['total_approvals_30d']} total (30d)")
        print(f"  Data Capture: {posture['data_capture_context']['capture_policies']} policies, "
              f"{posture['data_capture_context']['security_events_30d']} security events (30d)")
        print(f"  Security Events (30d): {posture['security_context']['security_events_30d']}")
        print(f"  Alert Rules: {posture['alert_rules_context']['active_alert_rules']} active, "
              f"{posture['alert_rules_context']['alert_firings_30d']} firings (30d)")
        print(f"  Audit Events (30d): {posture['audit_context']['audit_events_30d']}")
        print(f"  Tags: {posture['tags_context']['active_tags']} active "
              f"/ {posture['tags_context']['total_tags']} total")

        tools = client.get("/tool-registry").json()
        print(f"\n=== Registered Tools ({len(tools.get('items', []))}) ===")
        for t in tools.get("items", [])[:5]:
            print(f"  {t['tool_name']} — policy={t['policy']}, enforced={t.get('runtime_enforcement', False)}")

        policies = client.get("/tool-policies").json()
        print(f"\n=== Tool Policies ({len(policies.get('items', []))}) ===")
        for p in policies.get("items", [])[:5]:
            print(f"  {p['name']} — action={p['action']}, active={p.get('is_active', True)}")

        print("\n=== Governance Surface Links ===")
        surfaces = [
            "Tool Registry (/tool-registry)",
            "Tool Policies (/tool-policies)",
            "Approvals (/approvals)",
            "Data Capture (/data-capture)",
            "Security (/security)",
            "Alert Rules (/alert-rules)",
            "Audit Log (/audit)",
            "Governance Pack (/governance-pack)",
            "Tags (/tags)",
        ]
        for s in surfaces:
            print(f"  -> {s}")
        print(f"\nAll {len(surfaces)} governance surfaces cross-linked via internal posture card.")


if __name__ == "__main__":
    main()
