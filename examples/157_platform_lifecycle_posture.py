"""Fetch platform lifecycle posture (platform admin only): FinOps, gateway, governance, and org access summaries."""

import os, httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.environ["RUNLEDGER_API_KEY"]

r = httpx.get(
    f"{BASE}/analytics/platform-lifecycle-posture",
    headers={"Authorization": f"Bearer {KEY}"},
)
r.raise_for_status()
data = r.json()
print(f"Billing periods: {data['finops_context']['billing_periods']} (active: {data['finops_context']['active_billing_periods']})")
print(f"Chargeback rules: {data['finops_context']['chargeback_rules']}")
print(f"Ledger snapshots: {data['finops_context']['ledger_snapshots']}")
print(f"Gateway routes: {data['gateway_context']['gateway_routes']}")
print(f"Providers: {data['gateway_context']['distinct_providers']}")
print(f"Guardrail rules: {data['gateway_context']['guardrail_rules']}")
print(f"Audit events (7d): {data['governance_context']['audit_events_30d']}")
print(f"Tool policies: {data['governance_context']['tool_policies']}")
print(f"Alert rules: {data['governance_context']['alert_rules']}")
print(f"Workspaces: {data['org_access_context']['total_workspaces']}")
print(f"API keys: {data['org_access_context']['total_api_keys']}")
print(f"Users: {data['org_access_context']['total_users']}")
