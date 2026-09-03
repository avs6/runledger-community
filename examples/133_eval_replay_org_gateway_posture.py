"""Fetch evaluation & replay org/gateway posture."""

import os, httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.environ["RUNLEDGER_API_KEY"]

r = httpx.get(
    f"{BASE}/analytics/eval-replay-org-gateway-posture",
    headers={"Authorization": f"Bearer {KEY}"},
)
r.raise_for_status()
data = r.json()
print(f"Workspace: {data['workspace_context']['workspace_name']}")
print(f"  Access groups: {data['access_group_context']['access_groups']}")
print(f"  API keys: {data['api_key_context']['api_keys']}")
print(f"  Hub models: {data['ai_hub_context']['hub_models']} (active: {data['ai_hub_context']['hub_active_models']})")
print(f"  Providers: {data['provider_context']['distinct_providers']}")
print(f"  Active routes: {data['provider_context']['active_routes']}")
print(f"  Guardrail rules: {data['guardrail_context']['guardrail_rules']}")
print(f"  Cache configs: {data['gateway_context']['cache_configs']}")
print(f"  Routing policies: {data['gateway_context']['routing_policies']}")
