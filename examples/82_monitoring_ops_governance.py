"""
Example 82 — Monitoring & Ops Governance Integration

Demonstrates the two WU-010 posture endpoints that connect Monitoring and
Telemetry to gateway, governance, org, and investigation context.

Usage:
    export RUNLEDGER_API_KEY="rl_test_..."
    python examples/82_monitoring_ops_governance.py
"""

import os
import httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.getenv("RUNLEDGER_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {KEY}"}


def main() -> None:
    with httpx.Client(base_url=BASE, headers=HEADERS, timeout=30) as c:
        print("=== Monitoring Ops Posture ===")
        r = c.get("/analytics/monitoring-ops-posture")
        r.raise_for_status()
        m = r.json()
        gw = m["gateway_context"]
        gov = m["governance_context"]
        org = m["org_context"]
        inv = m["investigation_context"]
        print(f"  Providers: {gw['distinct_providers']}  Routes: {gw['active_routes']}")
        print(f"  Guardrails: {gw['guardrail_rules']}  Events 30d: {gw['guardrail_events_30d']}")
        print(f"  Cache configs: {gw['cache_configs']}  Rate-limit routes: {gw['rate_limit_routes']}")
        print(f"  Tool registry: {gov['tool_registry']}  Policies: {gov['tool_policies']}")
        print(f"  Capture: {gov['capture_policies']}  Audit 30d: {gov['audit_events_30d']}")
        print(f"  Approvals: {gov['approvals']}  Tags: {gov['tags']}")
        print(f"  Users: {org['workspace_users']}  MCP: {org['active_mcp_servers']}/{org['mcp_servers']}")
        print(f"  Runs 30d: {inv['runs_30d']}  Gateway reqs 30d: {inv['gateway_requests_30d']}")

        print("\n=== Telemetry Ops Posture ===")
        r = c.get("/analytics/telemetry-ops-posture")
        r.raise_for_status()
        t = r.json()
        gw2 = t["gateway_context"]
        gov2 = t["governance_context"]
        org2 = t["org_context"]
        inv2 = t["investigation_context"]
        print(f"  Routes: {gw2['active_routes']}  Models: {gw2['distinct_models']}")
        print(f"  Gateway reqs 30d: {gw2['gateway_requests_30d']}")
        print(f"  Capture: {gov2['capture_policies']}  Security 30d: {gov2['security_events_30d']}")
        print(f"  Alerts: {gov2['active_alert_rules']}/{gov2['alert_rules']}  Audit 30d: {gov2['audit_events_30d']}")
        print(f"  Approvals: {gov2['approvals']}  Tags: {gov2['tags']}")
        print(f"  Users: {org2['workspace_users']}  Batches 30d: {org2['telemetry_batches_30d']}")
        print(f"  Runs 30d: {inv2['runs_30d']}  Provider calls 30d: {inv2['provider_calls_30d']}")


if __name__ == "__main__":
    main()
