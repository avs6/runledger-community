"""Inspect the runtime scope model posture for a workspace.

Shows identity model (access groups, API keys, scope types), policy
enforcement (tool policies by scope, guardrails, events), scope
propagation (enforcement points, preflight inputs), and observe context.
"""

import os, httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.environ.get("RUNLEDGER_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {KEY}"} if KEY else {}

r = httpx.get(f"{BASE}/analytics/runtime-scope-model-posture", headers=HEADERS, timeout=10)
r.raise_for_status()
d = r.json()

print("=== Runtime Scope Model Posture ===\n")

im = d["identity_model"]
print(f"Identity model:")
print(f"  Access groups:       {im['access_groups']} ({im['access_group_members']} members)")
print(f"  Groups with budget:  {im['groups_with_budget']}")
print(f"  Groups with guards:  {im['groups_with_guardrails']}")
print(f"  API keys:            {im['api_keys']}")
print(f"  Scope types:         {', '.join(im['scope_types'])}")

pe = d["policy_enforcement"]
print(f"\nPolicy enforcement:")
print(f"  Tool policies:       {pe['active_tool_policies']} active / {pe['total_tool_policies']} total")
print(f"  Workspace-scoped:    {pe['workspace_scoped_policies']}")
print(f"  Group-scoped:        {pe['access_group_scoped_policies']}")
print(f"  Guardrail rules:     {pe['guardrail_rules']}")
print(f"  Guardrail events:    {pe['guardrail_events_30d']} (30d)")
print(f"  Policy actions:      {', '.join(pe['policy_actions'])}")

sp = d["scope_propagation"]
print(f"\nScope propagation:")
print(f"  Rust data plane:     {sp['rust_data_plane']}")
print(f"  Python control:      {sp['python_control_plane']}")
print(f"  Preflight inputs:    {', '.join(sp['preflight_scope_inputs'])}")
print(f"  Enforcement points:  {', '.join(sp['enforcement_points'])}")
print(f"  Active routes:       {sp['active_routes']}")

oc = d["observe_context"]
print(f"\nObserve context:")
print(f"  Requests (30d):      {oc['requests_30d']}")
print(f"  Guardrail events:    {oc['guardrail_events_30d']}")
print(f"  Audit events:        {oc['audit_events_30d']}")
