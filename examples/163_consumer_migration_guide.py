"""Consumer migration guide: transitioning from Python inline gateway to Rust data plane.

This script validates that your deployment is correctly pointing to the Rust
gateway (runledger-gateway-rs) rather than the deprecated Python inline runtime.

What changed:
  - Live chat completions: http://localhost:8210/gateway/chat/completions (Rust)
  - Python /gateway/chat/completions returns 410 GONE (compatibility stub)
  - ROUTER_SVC_URL now defaults to runledger-gateway-rs:8210 (sidecar collapsed)
  - runledger-router sidecar moved to 'deprecated' Docker Compose profile

Migration checklist:
  1. Point all /gateway/chat/completions calls to port 8210 (Rust gateway)
  2. Point ROUTER_SVC_URL to http://runledger-gateway-rs:8210
  3. Use RUNLEDGER_GATEWAY_BASE_URL=http://localhost:8210/gateway for SDKs
  4. Control plane APIs remain on port 8201 (Python): routes, stats, analytics
  5. Remove any docker compose --profile aux dependency on runledger-router
"""

import os, httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
GATEWAY = os.getenv("RUNLEDGER_GATEWAY_BASE_URL", "http://localhost:8210/gateway")
KEY = os.environ.get("RUNLEDGER_API_KEY", "")

def check(label: str, url: str, method: str = "GET", expect_status: int | None = None):
    try:
        r = getattr(httpx, method.lower())(url, headers={"Authorization": f"Bearer {KEY}"} if KEY else {}, timeout=5)
        status = "OK" if (expect_status is None or r.status_code == expect_status) else "UNEXPECTED"
        print(f"  [{status}] {label}: {r.status_code}")
    except httpx.ConnectError:
        print(f"  [DOWN] {label}: connection refused")

print("=== Consumer Migration Validation ===\n")

print("1. Rust gateway (should be 200 or provider error):")
check("GET /health/live", f"{GATEWAY.rsplit('/gateway', 1)[0]}/health/live", expect_status=200)

print("\n2. Python legacy stub (should be 410 GONE):")
check("POST /gateway/chat/completions (Python)", f"{BASE}/gateway/chat/completions", method="POST", expect_status=410)

print("\n3. Control plane health (should be 200):")
check("GET /health/live (API)", f"{BASE}/health/live", expect_status=200)

print("\n4. Sidecar collapse posture (should be 200 if API key set):")
if KEY:
    r = httpx.get(f"{BASE}/analytics/sidecar-collapse-posture", headers={"Authorization": f"Bearer {KEY}"}, timeout=5)
    if r.status_code == 200:
        data = r.json()
        print(f"  [OK] Collapsed: {data['collapsed_service']['name']} -> {data['collapsed_service']['absorbed_by']}")
        print(f"  [OK] Status: {data['collapsed_service']['status']}")
    else:
        print(f"  [WARN] {r.status_code}: {r.text[:100]}")
else:
    print("  [SKIP] No API key set")

print("\n=== Migration summary ===")
print("  Data plane:     http://localhost:8210/gateway/chat/completions  (Rust)")
print("  Control plane:  http://localhost:8201  (Python)")
print("  Legacy stub:    http://localhost:8201/gateway/chat/completions  (410 GONE)")
print("  Router sidecar: DEPRECATED (absorbed into gateway-rs)")
