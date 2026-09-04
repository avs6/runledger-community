"""Inspect the API explorer posture for a workspace.

Shows OpenAPI surface metadata, endpoint ownership by plane, SDK support
details, and 30-day observe context.
"""

import os, httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.environ.get("RUNLEDGER_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {KEY}"} if KEY else {}

r = httpx.get(f"{BASE}/analytics/api-explorer-posture", headers=HEADERS, timeout=10)
r.raise_for_status()
d = r.json()

print("=== API Explorer Posture ===\n")

oa = d["openapi_surface"]
print(f"Spec URL:       {oa['spec_url']}")
print(f"Reference UI:   {oa['reference_ui']}")
print(f"Spec format:    {oa['spec_format']}")
print(f"Auto-generated: {oa['generated']}")
print(f"Source of truth: {oa['source_of_truth']}")

eo = d["endpoint_ownership"]
print("\nEndpoint ownership:")
for plane, info in eo.items():
    label = plane.replace("_", " ").title()
    families = ", ".join(info["families"][:5])
    extra = f" +{len(info['families']) - 5} more" if len(info["families"]) > 5 else ""
    print(f"  {label:16s} {info['host']:30s} {len(info['families'])} families: {families}{extra}")

sdk = d["sdk_support"]
print(f"\nSDK support:")
print(f"  Languages:    {', '.join(sdk['languages'])}")
print(f"  Auth model:   {sdk['auth_model']}")
print(f"  API keys:     {sdk['api_keys']}")
print(f"  Active routes: {sdk['active_routes']}")

obs = d["observe_context"]
print(f"\nObserve context (30d):")
print(f"  Requests:     {obs['requests_30d']}")
print(f"  Audit events: {obs['audit_events_30d']}")
