"""Inspect the API explorer refresh posture for a workspace.

Shows refreshed OpenAPI surface with pipeline endpoint discovery,
endpoint ownership across control/data planes, SDK support, and
discovery surface configuration including sidebar linking.
"""

import os, httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8201")
KEY = os.environ.get("RUNLEDGER_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {KEY}"} if KEY else {}

r = httpx.get(f"{BASE}/analytics/api-explorer-refresh-posture", headers=HEADERS, timeout=10)
r.raise_for_status()
d = r.json()

print("=== API Explorer Refresh Posture ===\n")

oa = d["openapi_surface"]
print(f"Spec format:        {oa['spec_format']}")
print(f"Spec URL:           {oa['spec_url']}")
print(f"Reference UI:       {oa['reference_ui']}")
print(f"Swagger UI:         {oa['swagger_ui']}")
print(f"Source of truth:    {oa['source_of_truth']}")

eo = d["endpoint_ownership"]
print(f"\nEndpoint ownership:")
for plane, info in eo.items():
    print(f"  {plane:16s} → {info['host']} ({len(info['families'])} families)")
    for fam in info["families"]:
        print(f"    - {fam}")

pe = d["pipeline_endpoints"]
print(f"\nPipeline endpoints:")
print(f"  Live Pipeline:    {pe['live_pipeline']}")
print(f"  Pipeline Designer: {pe['pipeline_designer']}")
print(f"  Pipeline Studio:  {pe['pipeline_studio']}")
print(f"  Streaming inject: {pe['streaming_inject']}")
print(f"  Trace enrichment: {pe['trace_enrichment']}")
print(f"  MCP servers:      {pe['mcp_servers']}")

sdk = d["sdk_support"]
print(f"\nSDK support:")
print(f"  Languages:        {', '.join(sdk['languages'])}")
print(f"  Auth model:       {sdk['auth_model']}")
print(f"  API keys:         {sdk['api_keys']}")
print(f"  Active routes:    {sdk['active_routes']}")

ds = d["discovery_surface"]
print(f"\nDiscovery surface:")
print(f"  In-app explorer:  {ds['in_app_explorer']}")
print(f"  Swagger UI:       {ds['swagger_ui']}")
print(f"  Scalar reference: {ds['scalar_reference']}")
print(f"  Postman:          {ds['postman_collection']}")
print(f"  Sidebar linked:   {ds['sidebar_linked']}")

oc = d["observe_context"]
print(f"\nObserve context:")
print(f"  Requests (30d):    {oc['requests_30d']}")
print(f"  Audit events (30d): {oc['audit_events_30d']}")
