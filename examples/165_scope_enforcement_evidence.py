"""Inspect scope enforcement evidence posture for a workspace.

Shows enforcement decisions by outcome (blocked/allowed/modified),
scope friction rates, violation lineage structure, and evidence loop
closure across observe and governance surfaces.
"""

import os, httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.environ.get("RUNLEDGER_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {KEY}"} if KEY else {}

r = httpx.get(f"{BASE}/analytics/scope-enforcement-evidence-posture", headers=HEADERS, timeout=10)
r.raise_for_status()
d = r.json()

print(f"=== Scope Enforcement Evidence ({d['period_days']}d) ===\n")

es = d["enforcement_summary"]
print("Enforcement summary:")
print(f"  Guardrail events:    {es['guardrail_events_30d']}")
print(f"  Blocked:             {es['blocked_30d']}")
print(f"  Allowed:             {es['allowed_30d']}")
print(f"  Modified:            {es['modified_30d']}")
print(f"  False positives:     {es['false_positives_30d']}")
print(f"  Distinct rules:      {es['distinct_rules_triggered']}")
print(f"  Active rules:        {es['active_guardrail_rules']}")

sf = d["scope_friction"]
print(f"\nScope friction:")
print(f"  Tool policies:       {sf['total_tool_policies']}")
print(f"  Workspace-scoped:    {sf['workspace_scoped']}")
print(f"  Group-scoped:        {sf['access_group_scoped']}")
print(f"  Block rate:          {sf['block_rate_pct']}%")
print(f"  False positive rate: {sf['false_positive_rate_pct']}%")

vl = d["violation_lineage"]
print(f"\nViolation lineage:")
print(f"  Scope inputs:        {', '.join(vl['scope_inputs'])}")
print(f"  Enforcement points:  {', '.join(vl['enforcement_points'])}")
print(f"  Decision outcomes:   {', '.join(vl['decision_outcomes'])}")
print(f"  Evidence fields:     {', '.join(vl['evidence_fields'])}")

el = d["evidence_loop"]
print(f"\nEvidence loop:")
print(f"  Requests (30d):      {el['requests_30d']}")
print(f"  Audit events:        {el['audit_events_30d']}")
print(f"  API keys:            {el['api_keys']}")
print(f"  Observe surfaces:    {', '.join(el['observe_surfaces'])}")
print(f"  Governance surfaces: {', '.join(el['governance_surfaces'])}")
