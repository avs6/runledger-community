"""Fetch gateway runtime boundary posture: Rust data plane, Python control plane, hot-path migration, and runtime contracts."""

import os, httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.environ["RUNLEDGER_API_KEY"]

r = httpx.get(
    f"{BASE}/analytics/gateway-runtime-boundary-posture",
    headers={"Authorization": f"Bearer {KEY}"},
)
r.raise_for_status()
data = r.json()
dp = data["rust_data_plane"]
cp = data["python_control_plane"]
hp = data["hot_path_migration"]
rc = data["runtime_contracts"]
obs = data["observe_context"]
print(f"Rust data plane: {dp['service']} (port {dp['port']})")
print(f"  Capabilities: {', '.join(dp['capabilities'])}")
print(f"  Direct HTTP routes: {dp['direct_http_routes']} / {dp['active_routes']} active ({dp['distinct_providers']} providers)")
print(f"Python control plane: {len(cp['modules'])} modules, {len(cp['ownership'])} ownership domains")
print(f"  Routes: {cp['total_routes']} total, {cp['routing_groups']} groups, {cp['routing_policies']} policies")
print(f"  Passthrough: {cp['passthrough_endpoints']} endpoints, {cp['cache_configs']} cache configs")
print(f"Hot-path migration: legacy stub={hp['legacy_stub']} at {hp['legacy_route']}")
print(f"  Execution: {hp['execution_owner']} | Preflight: {hp['preflight_owner']} | Finalize: {hp['finalize_owner']}")
print(f"  Guardrails: {hp['active_guardrails']} | Budgets: {hp['budgets']}")
print(f"Runtime contracts: preflight={rc['preflight']}, finalize={rc['finalize']}")
print(f"  Events: {rc['signed_events']}, Snapshot: {rc['snapshot']}")
print(f"Observe: {obs['requests_7d']} requests (7d), {obs['cache_hits_7d']} cache hits, {obs['monitoring_alerts']} alerts, {obs['audit_events_30d']} audit events (30d)")
