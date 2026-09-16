"""Inspect the hot-path migration posture for a workspace.

Shows the Python-to-Rust migration status for each provider, including
Bedrock SigV4 pre-signing, Vertex SSE conversion, control-plane module
inventory, and runtime contract counts.
"""

import os, httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.environ.get("RUNLEDGER_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {KEY}"} if KEY else {}

r = httpx.get(f"{BASE}/analytics/hot-path-migration-posture", headers=HEADERS, timeout=10)
r.raise_for_status()
d = r.json()

print("=== Hot-Path Migration Posture ===\n")

ms = d["migration_summary"]
print(f"Migration:           {ms['migration_percentage']}%")
print(f"Status:              {ms['status']}")
print(f"Total active routes: {ms['total_active_routes']}")
print(f"Direct HTTP routes:  {ms['direct_http_routes']}")
print(f"Adapter fallback:    {ms['python_adapter_routes']}")
print(f"Passthrough:         {ms['passthrough_endpoints']}")

pms = d["provider_migration_status"]
print(f"\nProvider migration status:")
for name, info in pms.items():
    status = info.get("status", "unknown")
    routes = info.get("active_routes", 0)
    streaming = info.get("streaming", "n/a")
    notes = info.get("notes", "")
    print(f"  {name:16s} → {status:10s} | {routes} routes | streaming: {streaming}")
    if notes:
        print(f"  {'':16s}   {notes}")

cpm = d["control_plane_modules"]
print(f"\nControl-plane modules:")
for mod, role in cpm.items():
    print(f"  {mod:30s} → {role}")

rci = d["runtime_contract_inventory"]
print(f"\nRuntime contract inventory:")
print(f"  Total contracts:  {rci['total_contracts']}")
for name, desc in rci["contracts"].items():
    print(f"  {name:20s} → {desc}")

oc = d["observe_context"]
print(f"\nObserve context:")
print(f"  Requests (7d):     {oc['requests_7d']}")
print(f"  Cache hits (7d):   {oc['cache_hits_7d']}")
print(f"  Audit events (30d): {oc['audit_events_30d']}")
