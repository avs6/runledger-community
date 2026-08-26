"""
Example 91 — Monitoring Telemetry Ops and Governance Refresh

Demonstrates the posture endpoints used by the Monitoring and Telemetry pages
to surface gateway, governance, budget, and identity context for operational
triage and cross-suite investigation.
"""

import os
import httpx

BASE = os.getenv("RUNLEDGER_API_URL", "http://localhost:8000")
KEY = os.getenv("RUNLEDGER_API_KEY", "rl_test_key")
HEADERS = {"Authorization": f"Bearer {KEY}"}


def main() -> None:
    with httpx.Client(base_url=BASE, headers=HEADERS, timeout=30) as c:
        # Monitoring — ops posture
        mon = c.get("/analytics/monitoring-ops-posture").json()
        print("=== Monitoring Ops Posture ===")
        print(f"  Providers: {mon['gateway_context']['distinct_providers']}")
        print(f"  Guardrail rules: {mon['gateway_context']['guardrail_rules']}")
        print(f"  Cache configs: {mon['gateway_context']['cache_configs']}")
        print(f"  Rate limit routes: {mon['gateway_context']['rate_limit_routes']}")
        print(f"  Tool registry: {mon['governance_context']['tool_registry']}")
        print(f"  Approvals: {mon['governance_context']['approvals']}")
        print(f"  API key attribution: via org context users={mon['org_context']['workspace_users']}")

        # Monitoring — finops posture
        fin = c.get("/analytics/monitoring-finops-posture").json()
        print("\n=== Monitoring FinOps Posture ===")
        print(f"  Active budgets: {fin['budget_context']['active_budgets']}/{fin['budget_context']['budgets']}")
        print(f"  Breaches: {fin['budget_context']['breach_count']}")
        print(f"  Budget detail drill-through now available")

        # Telemetry — ops posture
        tel = c.get("/analytics/telemetry-ops-posture").json()
        print("\n=== Telemetry Ops Posture ===")
        print(f"  Routes: {tel['gateway_context']['active_routes']}")
        print(f"  Models: {tel['gateway_context']['distinct_models']}")
        print(f"  Gateway reqs (30d): {tel['gateway_context']['gateway_requests_30d']}")
        print(f"  Capture policies: {tel['governance_context']['capture_policies']}")
        print(f"  Alert rules: {tel['governance_context']['active_alert_rules']}/{tel['governance_context']['alert_rules']}")
        print(f"  Approvals: {tel['governance_context']['approvals']}")
        print("  Drill-through: Guardrails, Response Cache, Rate Limits, Tool Registry, Tool Policies now available")


if __name__ == "__main__":
    main()
