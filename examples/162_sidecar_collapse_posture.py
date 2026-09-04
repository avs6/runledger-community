"""Fetch sidecar collapse posture: deprecated router sidecar, gateway-rs absorption, topology simplification, and routing classification."""

import os, httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.environ["RUNLEDGER_API_KEY"]

r = httpx.get(
    f"{BASE}/analytics/sidecar-collapse-posture",
    headers={"Authorization": f"Bearer {KEY}"},
)
r.raise_for_status()
data = r.json()
cs = data["collapsed_service"]
ga = data["gateway_rs_absorption"]
ts = data["topology_simplification"]
rc = data["routing_classification"]
obs = data["observe_context"]
print(f"Collapsed: {cs['name']} (port {cs['former_port']}) → {cs['status']}")
print(f"  Absorbed by: {cs['absorbed_by']}")
print(f"Gateway-rs: {ga['service']} (port {ga['port']})")
print(f"  Classifier: {ga['classifier_endpoint']} modes={', '.join(ga['classifier_modes'])}")
print(f"  IR-enabled routes: {ga['ir_enabled_routes']} / {ga['active_routes']} active ({ga['distinct_providers']} providers)")
print(f"Topology: removed {', '.join(ts['services_removed'])}")
print(f"  Env redirected: {', '.join(ts['env_vars_redirected'])} → {ts['new_default_target']}")
print(f"  Profiles affected: {', '.join(ts['compose_profiles_affected'])}")
print(f"Classification: owner={rc['owner']} path={rc['classify_path']} fallback={rc['fallback']}")
print(f"  Groups: {rc['routing_groups']} · Policies: {rc['routing_policies']} · Guardrails: {rc['active_guardrails']} · Cache: {rc['cache_configs']}")
print(f"Observe: {obs['requests_7d']} requests (7d), {obs['routed_requests_7d']} routed")
