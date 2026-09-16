"""Inspect the router collapse refresh posture for a workspace.

Shows post-collapse validation: sidecar absorption status, service topology,
routing classification health, deployment artifact alignment (Helm, Compose,
Makefile), and routing intelligence capabilities.
"""

import os, httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.environ.get("RUNLEDGER_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {KEY}"} if KEY else {}

r = httpx.get(f"{BASE}/analytics/router-collapse-refresh-posture", headers=HEADERS, timeout=10)
r.raise_for_status()
d = r.json()

print("=== Router Collapse Refresh Posture ===\n")

cs = d["collapse_status"]
print(f"Collapse state:     {cs['collapse_state']}")
print(f"Collapsed service:  {cs['collapsed_service']} (port {cs['collapsed_port']})")
print(f"Absorbed into:      {cs['absorbed_into']} (port {cs['absorbing_port']})")
print(f"Remaining refs:     {cs['remaining_references']}")

st = d["service_topology"]
print(f"\nService topology:")
print(f"  Active services:    {', '.join(st['active_services'])}")
print(f"  Deprecated:         {', '.join(st['deprecated_services'])}")
print(f"  Compose profile:    {st['compose_profile']}")
print(f"  Helm enabled:       {st['helm_enabled']}")
print(f"  Helm replicas:      {st['helm_replicas']}")
print(f"  Env vars redirected: {', '.join(st['env_vars_redirected'])}")
print(f"  Default target:     {st['new_default_target']}")

ch = d["classification_health"]
print(f"\nClassification health:")
print(f"  Classifier owner:   {ch['classifier_owner']}")
print(f"  Endpoint:           {ch['classifier_endpoint']}")
print(f"  Modes:              {', '.join(ch['classifier_modes'])}")
print(f"  IR-enabled routes:  {ch['ir_enabled_routes']}")
print(f"  Active routes:      {ch['active_routes']}")
print(f"  Providers:          {ch['distinct_providers']}")
print(f"  Routing groups:     {ch['routing_groups']}")
print(f"  Routing policies:   {ch['routing_policies']}")

dv = d["deployment_validation"]
print(f"\nDeployment validation:")
print(f"  Makefile build:     {dv['makefile_router_build']}")
print(f"  Compose router:     {dv['docker_compose_router']}")
print(f"  Helm enabled:       {dv['helm_router_enabled']}")
print(f"  ROUTER_SVC_URL:     {dv['router_svc_url_target']}")
print(f"  IR default:         {dv['intelligent_router_default']}")
print(f"  Stale imports:      {dv['stale_router_imports']}")

ri = d["routing_intelligence"]
print(f"\nRouting intelligence:")
print(f"  Cache configs:      {ri['cache_configs']}")
print(f"  Active guardrails:  {ri['active_guardrails']}")
print(f"  Fallback:           {ri['fallback_strategy']}")
print(f"  Canary support:     {ri['canary_support']}")
print(f"  A/B test support:   {ri['ab_test_support']}")
print(f"  Weighted routing:   {ri['weighted_routing']}")

oc = d["observe_context"]
print(f"\nObserve context:")
print(f"  Requests (7d):     {oc['requests_7d']}")
print(f"  Routed (7d):       {oc['routed_requests_7d']}")
print(f"  Audit events (30d): {oc['audit_events_30d']}")
