"""Inspect the consumer migration refresh posture for a workspace.

Shows post-migration validation: stale reference audit across docs, examples,
scripts, and Postman, provider execution mode inventory with signing and
streaming details, asset alignment status, and runtime validation.
"""

import os, httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.environ.get("RUNLEDGER_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {KEY}"} if KEY else {}

r = httpx.get(f"{BASE}/analytics/consumer-migration-refresh-posture", headers=HEADERS, timeout=10)
r.raise_for_status()
d = r.json()

print("=== Consumer Migration Refresh Posture ===\n")

mc = d["migration_completeness"]
print(f"Status:             {mc['status']}")
print(f"Data plane:         {mc['data_plane']} (port {mc['data_plane_port']})")
print(f"Control plane:      {mc['control_plane']} (port {mc['control_plane_port']})")
print(f"Active routes:      {mc['active_routes']} / {mc['total_routes']} total")
print(f"Providers:          {mc['distinct_providers']}")
print(f"All direct HTTP:    {mc['all_providers_direct_http']}")

sra = d["stale_reference_audit"]
print(f"\nStale reference audit:")
print(f"  Python stub:      {sra['python_completion_stub']}")
print(f"  Inline runtime:   {sra['stale_inline_runtime_refs']}")
print(f"  Router sidecar:   {sra['stale_router_sidecar_refs']}")
print(f"  Python adapter:   {sra['stale_python_adapter_refs']}")
print(f"  Docs aligned:     {sra['docs_aligned']}")
print(f"  Examples aligned: {sra['examples_aligned']}")
print(f"  Scripts aligned:  {sra['scripts_aligned']}")
print(f"  Postman aligned:  {sra['postman_aligned']}")

pem = d["provider_execution_modes"]
print(f"\nProvider execution modes:")
for name, info in pem.items():
    print(f"  {name:16s} → {info['mode']} | signing: {info['signing']} | streaming: {info['streaming']}")

aa = d["asset_alignment"]
print(f"\nAsset alignment:")
print(f"  API keys:         {aa['api_keys']}")
print(f"  Benchmark target: {aa['benchmark_scripts_target']}")
print(f"  Swagger UI:       {aa['swagger_ui_enabled']}")
print(f"  Migration guide:  {aa['migration_guide']}")
print(f"  Runtime model:    {aa['docs_runtime_model']}")

rv = d["runtime_validation"]
print(f"\nRuntime validation:")
print(f"  Env vars migrated: {', '.join(rv['env_vars_migrated'])}")
print(f"  Legacy stub:      {rv['legacy_python_stub']}")
print(f"  Router profile:   {rv['router_sidecar_profile']}")
print(f"  Direct HTTP:      {rv['direct_http_provider_count']}")
print(f"  Adapter fallback: {rv['python_adapter_fallback_count']}")

oc = d["observe_context"]
print(f"\nObserve context:")
print(f"  Requests (7d):     {oc['requests_7d']}")
print(f"  Requests (30d):    {oc['requests_30d']}")
print(f"  Cache hits (7d):   {oc['cache_hits_7d']}")
print(f"  Audit events (30d): {oc['audit_events_30d']}")
