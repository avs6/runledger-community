"""Inspect the governance runtime refresh posture for a workspace.

Shows scope-aware policy filtering status: scope resolution dimensions,
policy breakdown by scope type, enforcement depth with block rates,
friction analysis per scope level, and observe surface metrics.
"""

import os, httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8201")
KEY = os.environ.get("RUNLEDGER_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {KEY}"} if KEY else {}

r = httpx.get(f"{BASE}/analytics/governance-runtime-refresh-posture", headers=HEADERS, timeout=10)
r.raise_for_status()
d = r.json()

print("=== Governance Runtime Refresh Posture ===\n")

sr = d["scope_resolution"]
print(f"Scope filtering:    {'Active' if sr['scope_filtering_active'] else 'Inactive'}")
print(f"Dimensions:         {', '.join(sr['dimensions_enforced'])}")
print(f"Types supported:    {', '.join(sr['scope_types_supported'])}")
for k, v in sr["identity_propagation"].items():
    print(f"  {k:20s} → {v}")

psb = d["policy_scope_breakdown"]
print(f"\nPolicy scope breakdown:")
print(f"  Total active:     {psb['total_active_policies']}")
print(f"  Workspace:        {psb['workspace_scoped']}")
print(f"  Access group:     {psb['access_group_scoped']}")
print(f"  Search tool:      {psb['search_tool_scoped']}")
print(f"  Scope-aware:      {psb['scope_aware_pct']}%")
print(f"  Access groups:    {psb['total_access_groups']} ({psb['groups_with_guardrails']} with guardrails)")

ed = d["enforcement_depth"]
print(f"\nEnforcement depth (30d):")
print(f"  Guardrail events: {ed['guardrail_events_30d']}")
print(f"  Blocked:          {ed['blocked_30d']}")
print(f"  Allowed:          {ed['allowed_30d']}")
print(f"  Block rate:       {ed['block_rate_pct']}%")
print(f"  Active rules:     {ed['active_guardrail_rules']}")
print(f"  Enforcement pts:  {', '.join(ed['enforcement_points'])}")
print(f"  Scope enrichment: {', '.join(ed['scope_enrichment'])}")

fs = d["friction_by_scope"]
print(f"\nFriction by scope:")
for level in ["workspace_level", "access_group_level", "search_tool_level"]:
    info = fs[level]
    extra = f" · {info['groups_with_guardrails']} groups" if "groups_with_guardrails" in info else ""
    print(f"  {level:24s} → {info['policies']} policies, {info['enforcement']}{extra}")

oc = d["observe_context"]
print(f"\nObserve context:")
print(f"  Requests (30d):    {oc['requests_30d']}")
print(f"  Audit events:      {oc['audit_events_30d']}")
print(f"  API keys:          {oc['api_keys']}")
print(f"  Guardrail events:  {oc['guardrail_events_30d']}")
