"""Inspect the pipeline studio posture for a workspace.

Shows the end-to-end pipeline model (ingest → routing → enforcement →
execution → reporting), traffic overlay, enforcement overlay, FinOps
overlay, and build overlay.
"""

import os, httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.environ.get("RUNLEDGER_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {KEY}"} if KEY else {}

r = httpx.get(f"{BASE}/analytics/pipeline-studio-posture", headers=HEADERS, timeout=10)
r.raise_for_status()
d = r.json()

print("=== Pipeline Studio Posture ===\n")

pm = d["pipeline_model"]
print(f"Pipeline stages: {' → '.join(pm['stages'])}")
print(f"Ingest sources:  {', '.join(pm['ingest_sources'])}")

rn = pm["routing_nodes"]
print(f"\nRouting nodes:")
print(f"  Active routes:     {rn['active_routes']}")
print(f"  Providers:         {rn['distinct_providers']}")
print(f"  Routing groups:    {rn['routing_groups']}")
print(f"  Routing policies:  {rn['routing_policies']}")

er = pm["execution_runtime"]
print(f"\nExecution runtime:")
print(f"  Data plane:    {er['data_plane']}")
print(f"  Control plane: {er['control_plane']}")

to = d["traffic_overlay"]
print(f"\nTraffic overlay:")
print(f"  Requests (7d):   {to['requests_7d']}")
print(f"  Requests (30d):  {to['requests_30d']}")
print(f"  Cache hits (7d): {to['cache_hits_7d']}")
print(f"  Audit events:    {to['audit_events_30d']}")

eo = d["enforcement_overlay"]
print(f"\nEnforcement overlay:")
print(f"  Guardrail rules:  {eo['guardrail_rules']}")
print(f"  Events (30d):     {eo['guardrail_events_30d']}")
print(f"  Blocked (30d):    {eo['blocked_events_30d']}")
print(f"  Tool policies:    {eo['tool_policies']}")

fo = d["finops_overlay"]
print(f"\nFinOps overlay:")
print(f"  Budgets:          {fo['budgets']}")
print(f"  Cost tracking:    {fo['cost_tracking']}")

bo = d["build_overlay"]
print(f"\nBuild overlay:")
print(f"  Agents:           {bo['agents']}")
print(f"  Workflows:        {bo['workflows']}")
print(f"  Participants:     {', '.join(bo['pipeline_participants'])}")
