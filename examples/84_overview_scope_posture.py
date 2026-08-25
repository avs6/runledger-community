"""
Example 84 — Overview Scope Posture Refresh

Demonstrates the WU-012 endpoint that enriches the Analytics Overview
with access-group, cache, rate-limit, and governance-tool context.

Usage:
    export RUNLEDGER_API_KEY="rl_test_..."
    python examples/84_overview_scope_posture.py
"""

import os
import httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.getenv("RUNLEDGER_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {KEY}"}


def main() -> None:
    with httpx.Client(base_url=BASE, headers=HEADERS, timeout=30) as c:
        print("=== Overview Scope Posture ===")
        r = c.get("/analytics/overview-scope-posture")
        r.raise_for_status()
        p = r.json()

        ag = p["access_group_context"]
        print(f"\n  Access Groups: {ag['active_access_groups']}/{ag['access_groups']} ({ag['total_members']} members)")

        ca = p["cache_context"]
        print(f"  Cache Configs: {ca['enabled_configs']}/{ca['cache_configs']} enabled")
        print(f"  Cache Hits: {ca['total_hits']}  Savings: ${ca['total_savings_usd']:.2f}")

        rl = p["rate_limit_context"]
        print(f"  Rate-Limited Routes: {rl['routes_with_limits']}  Unlimited: {rl['routes_without_limits']}")

        tc = p["tool_context"]
        print(f"  Tool Registry: {tc['tool_registry_entries']} entries")
        print(f"  Tool Policies: {tc['active_tool_policies']}/{tc['tool_policies']} active")
        print(f"  Pending Approvals: {tc['pending_approvals']}")
        print(f"  Capture Policies: {tc['capture_policies']}")

        print("\n=== Gateway Posture (existing) ===")
        r = c.get("/analytics/overview-gateway-posture")
        r.raise_for_status()
        gw = r.json()
        print(f"  Providers: {gw['provider_context']['distinct_providers']}")
        print(f"  Routes: {gw['provider_context']['active_routes']}/{gw['provider_context']['total_routes']}")
        print(f"  Guardrails: {gw['guardrail_context']['active_rules']} active, {gw['guardrail_context']['blocks_30d']} blocks 30d")


if __name__ == "__main__":
    main()
