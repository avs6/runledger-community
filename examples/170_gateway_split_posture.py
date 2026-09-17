"""Inspect the gateway architecture split posture for a workspace.

Shows the Rust data-plane / Python control-plane boundary, provider execution
map, response normalizers, stream parsers, and deprecated migration paths.
"""

import os, httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8201")
KEY = os.environ.get("RUNLEDGER_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {KEY}"} if KEY else {}

r = httpx.get(f"{BASE}/analytics/gateway-split-posture", headers=HEADERS, timeout=10)
r.raise_for_status()
d = r.json()

print("=== Gateway Architecture Split Posture ===\n")

ab = d["architecture_boundary"]
print(f"Status:           {ab['status']}")
print(f"Protocol:         {ab['contract_protocol']}")
print(f"Control plane:    {ab['control_plane']}")
print(f"Data plane:       {ab['data_plane']}")
print(f"Preflight owner:  {ab['preflight_owner']}")
print(f"Finalize owner:   {ab['finalize_owner']}")

rdp = d["rust_data_plane"]
print(f"\nRust data plane:  {rdp['service']} (port {rdp['port']})")
print(f"Active routes:    {rdp['active_routes']}")
print(f"Direct HTTP:      {rdp['direct_http_routes']}")
print(f"Providers:        {rdp['distinct_providers']}")
print(f"Capabilities:")
for cap in rdp["capabilities"]:
    print(f"  - {cap}")
print(f"Response normalizers:")
for n in rdp["response_normalizers"]:
    print(f"  - {n}")
print(f"Stream parsers:")
for p in rdp["stream_parsers"]:
    print(f"  - {p}")

pcp = d["python_control_plane"]
print(f"\nPython control plane modules:")
for m in pcp["modules"]:
    print(f"  - {m}")
print(f"Ownership domains:")
for o in pcp["ownership"]:
    print(f"  - {o}")

pem = d["provider_execution_map"]
print(f"\nProvider execution map:")
print(f"  Direct HTTP routes:   {pem['direct_http_route_count']}")
print(f"  Adapter fallback:     {pem['python_adapter_route_count']}")
for name, info in pem["providers"].items():
    print(f"  {name:16s} → {info['execution']} ({info['active_routes']} routes)")

dp = d["deprecated_paths"]
print(f"\nDeprecated paths: {dp['count']}")
for p in dp.get("items", []):
    print(f"  - {p}")

oc = d["observe_context"]
print(f"\nObserve context:")
print(f"  Requests (7d):     {oc['requests_7d']}")
print(f"  Cache hits (7d):   {oc['cache_hits_7d']}")
print(f"  Audit events (30d): {oc['audit_events_30d']}")
