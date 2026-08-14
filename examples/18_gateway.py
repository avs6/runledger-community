"""
Example 18 — Model Gateway

Demonstrates the OpenAI-compatible proxy built into RunLedger:
  1. POST /gateway/routes      — add a provider route
  2. GET  /gateway/routes      — list configured routes
  3. POST /chat/completions on the Rust gateway runtime — send a completion through the gateway
     (cache miss → provider call → response cached)
  4. POST /chat/completions on the Rust gateway runtime — repeat same prompt
  5. GET  /gateway/stats        — request counts, cache hit rate, avg latency
  6. DELETE /gateway/routes/{id} — cleanup

How the gateway works
─────────────────────
Your app points its OpenAI base_url at /gateway instead of api.openai.com.
RunLedger:
  • Checks the prompt cache (SHA-256 of model + messages)
  • If a cache hit exists → returns immediately, no provider call
  • Otherwise → forwards to the configured provider route (with fallback)
  • Stores the response in the cache (TTL 24 h)
  • Logs every request as a GatewayRequest record (visible in /gateway/stats)

Provider API key
────────────────
The gateway reads the key from an environment variable on the Rust gateway runtime.
Set api_key_env_var to the name of that variable (e.g. "OPENAI_API_KEY").
The variable must be set in the runtime service environment.

Install
───────
    pip install httpx python-dotenv

Run it
──────
    # Set OPENAI_API_KEY in the Rust gateway runtime environment
    python 18_gateway.py

Key .env variables:
    RUNLEDGER_API_KEY          — your workspace API key
    RUNLEDGER_BASE_URL         — control-plane API (default)
    RUNLEDGER_GATEWAY_BASE_URL — Rust gateway runtime (default: http://localhost:8210/gateway)
"""

from __future__ import annotations

import os
import sys
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
GATEWAY_BASE_URL = os.getenv("RUNLEDGER_GATEWAY_BASE_URL", "http://localhost:8210/gateway")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")

if not API_KEY:
    print("ERROR: RUNLEDGER_API_KEY env var is required", file=sys.stderr)
    sys.exit(1)

HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def sep(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print("─" * 60)


# ── Step 1 — Create a gateway route ───────────────────────────────────────────

sep("Step 1 — POST /gateway/routes (add OpenAI route)")

route_payload = {
    "alias": "gpt-4o-mini",          # what the client sends as model name
    "provider": "openai",
    "target_model": "gpt-4o-mini",   # what the gateway sends to OpenAI
    "api_key_env_var": "OPENAI_API_KEY",  # env var on the Rust gateway runtime
    "priority": 10,
}

with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
    resp = client.post("/gateway/routes", json=route_payload)

if resp.status_code == 201:
    route = resp.json()
    route_id = route["id"]
    print(f"  ✓ Route created: id={route_id[:8]}…")
    print(f"    alias={route['alias']}  provider={route['provider']}")
    print(f"    target={route['target_model']}  priority={route['priority']}")
else:
    print(f"  ERROR {resp.status_code}: {resp.text}")
    # Still try listing — there may be an existing route
    route_id = None


# ── Step 2 — List routes ───────────────────────────────────────────────────────

sep("Step 2 — GET /gateway/routes")

with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
    resp = client.get("/gateway/routes")

if resp.status_code == 200:
    data = resp.json()
    routes = data["items"]
    print(f"  {len(routes)} active route(s):")
    for r in routes:
        print(
            f"    [{r['alias']:<20}]  provider={r['provider']:<10}"
            f"  target={r['target_model']}  priority={r['priority']}"
        )
else:
    print(f"  ERROR {resp.status_code}: {resp.text}")


# ── Step 3 — Send a completion (cache miss) ────────────────────────────────────

sep("Step 3 — POST Rust gateway /chat/completions")

PROMPT_MESSAGES = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is 2 + 2? Reply with just the number."},
]

completion_payload = {
    "model": "gpt-4o-mini",   # matches the alias set in Step 1
    "messages": PROMPT_MESSAGES,
    "max_tokens": 10,
    "cache": True,            # enable prompt cache
}

t0 = time.monotonic()
with httpx.Client(base_url=GATEWAY_BASE_URL, headers=HEADERS, timeout=30) as client:
    resp = client.post("/chat/completions", json=completion_payload)
elapsed_ms = int((time.monotonic() - t0) * 1000)

if resp.status_code == 200:
    result = resp.json()
    choices = result.get("choices", [])
    content = choices[0]["message"]["content"] if choices else "—"
    usage = result.get("usage", {})
    print(f"  Response:  {content!r}")
    print(f"  Latency:   {elapsed_ms}ms  (first call — cache miss, real provider call)")
    print(f"  Tokens:    in={usage.get('prompt_tokens')}  out={usage.get('completion_tokens')}")
elif resp.status_code == 502:
    print("  502 — No routes reachable or no provider key set on the Rust gateway runtime.")
    print("  Set OPENAI_API_KEY for runledger-gateway-rs, then restart that service.")
    print(f"  Detail: {resp.json().get('detail', '')}")
else:
    print(f"  ERROR {resp.status_code}: {resp.text}")


# ── Step 4 — Same prompt again (cache hit) ────────────────────────────────────

sep("Step 4 — POST Rust gateway /chat/completions again")

t0 = time.monotonic()
with httpx.Client(base_url=GATEWAY_BASE_URL, headers=HEADERS, timeout=30) as client:
    resp2 = client.post("/chat/completions", json=completion_payload)
elapsed_ms_2 = int((time.monotonic() - t0) * 1000)

if resp2.status_code == 200:
    result2 = resp2.json()
    choices2 = result2.get("choices", [])
    content2 = choices2[0]["message"]["content"] if choices2 else "—"
    print(f"  Response:  {content2!r}")
    print(f"  Latency:   {elapsed_ms_2}ms  (second call — served from cache)")
    speedup = round(elapsed_ms / elapsed_ms_2, 1) if elapsed_ms_2 > 0 else "∞"
    print(f"  Speedup:   {speedup}×  vs first call")
else:
    print(f"  Response: {resp2.status_code} — {resp2.text[:120]}")


# ── Step 5 — Gateway stats ────────────────────────────────────────────────────

sep("Step 5 — GET /gateway/stats")

with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
    resp = client.get("/gateway/stats")

if resp.status_code == 200:
    stats = resp.json()
    hit_rate = round(float(stats["cache_hit_rate"]) * 100, 1)
    avg_lat = stats["avg_latency_ms"]
    print(f"  Total requests:  {stats['total_requests']}")
    print(f"  Cache hits:      {stats['cache_hits']}")
    print(f"  Cache hit rate:  {hit_rate}%")
    print(f"  Avg latency:     {float(avg_lat):.0f}ms" if avg_lat else "  Avg latency:     —")
    if stats["routes"]:
        print("\n  Per-route breakdown:")
        for r in stats["routes"]:
            r_hit_rate = round(float(r["cache_hit_rate"]) * 100, 1)
            print(
                f"    [{r['alias']:<20}]  total={r['total_requests']}"
                f"  hits={r['cache_hits']}  hit_rate={r_hit_rate}%"
                f"  errors={r['error_count']}"
            )
else:
    print(f"  ERROR {resp.status_code}: {resp.text}")


# ── Step 6 — Cleanup ──────────────────────────────────────────────────────────

sep("Step 6 — DELETE /gateway/routes/{id} (cleanup)")

if route_id:
    with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
        resp = client.delete(f"/gateway/routes/{route_id}")
    if resp.status_code == 204:
        print(f"  ✓ Route {route_id[:8]}… deleted.")
    else:
        print(f"  ERROR {resp.status_code}: {resp.text}")
else:
    print("  (No route_id to clean up)")

print("\n✓ Example 18 complete.\n")
