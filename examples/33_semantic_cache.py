"""
Example 33 — Semantic Cache

Demonstrates RunLedger's semantic (near-duplicate) cache, which sits alongside the
exact prompt cache in the model gateway.

  Exact cache  → hits only on a byte-for-byte identical request.
  Semantic cache → hits on a *paraphrase* whose embedding is within the similarity
                   threshold, scoped to {tenant, model, system-prompt, version}.

Flow
────
  1. POST /gateway/routes            — add a route with semantic_cache_enabled=true
  2. POST /gateway/chat/completions  — first question (miss → real provider call)
  3. POST /gateway/chat/completions  — a re-worded question (semantic HIT, no provider call)
  4. GET  /gateway/requests          — show the decision_reason = "semantic_cache_hit"
  5. DELETE /gateway/routes/{id}     — cleanup

Two ways to turn it on
──────────────────────
  • Per route (persistent): semantic_cache_enabled=true — also toggleable in the
    dashboard Gateway page ("Cache ON/OFF" badge on each route).
  • Per request (ad-hoc):   pass  "semantic_cache": true  in the completion body.

Prerequisites
─────────────
  • The optimization services are up (qdrant + embedding-svc + semantic-cache-svc):
        docker compose up -d
  • A provider key is set on the API server (e.g. OPENAI_API_KEY in .env).

Install
───────
    pip install httpx python-dotenv

Run it
──────
    python 33_semantic_cache.py

Key .env variables:
    RUNLEDGER_API_KEY   — your workspace API key
    RUNLEDGER_BASE_URL  — http://localhost:8201  (default)
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
ALIAS = "gpt-4o-mini"


def sep(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print("─" * 60)


# ── Step 1 — Create a route with the semantic cache turned ON ─────────────────

sep("Step 1 — POST /gateway/routes (semantic_cache_enabled=true)")

route_payload = {
    "alias": ALIAS,
    "provider": "openai",
    "target_model": "gpt-4o-mini",
    "api_key_env_var": "OPENAI_API_KEY",
    "priority": 10,
    "semantic_cache_enabled": True,  # ← the GUI toggle sets this same flag
}

with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
    resp = client.post("/gateway/routes", json=route_payload)

route_id = None
if resp.status_code == 201:
    route = resp.json()
    route_id = route["id"]
    print(f"  ✓ Route created: id={route_id[:8]}…  semantic_cache={route['semantic_cache_enabled']}")
else:
    print(f"  ERROR {resp.status_code}: {resp.text}")


# ── Step 2 — First question (semantic miss → real provider call) ──────────────

sep("Step 2 — POST /gateway/chat/completions (first ask — miss)")

SYSTEM = {"role": "system", "content": "You are a concise HR assistant."}
first = {
    "model": ALIAS,
    "messages": [SYSTEM, {"role": "user", "content": "How much parental leave do employees get?"}],
    "max_tokens": 60,
    # Route toggle already enables it; you could also force it per-request:
    # "semantic_cache": True,
}

t0 = time.monotonic()
with httpx.Client(base_url=GATEWAY_BASE_URL, headers=HEADERS, timeout=30) as client:
    resp = client.post("/gateway/chat/completions", json=first)
miss_ms = int((time.monotonic() - t0) * 1000)

if resp.status_code == 200:
    content = resp.json()["choices"][0]["message"]["content"]
    print(f"  Response:  {content[:80]!r}")
    print(f"  Latency:   {miss_ms}ms  (miss — real provider call)")
elif resp.status_code == 502:
    print("  502 - set OPENAI_API_KEY on the Rust gateway runtime and restart it, then re-run.")
    sys.exit(0)
else:
    print(f"  ERROR {resp.status_code}: {resp.text}")


# ── Step 3 — Re-worded question (semantic HIT — no provider call) ─────────────

sep("Step 3 — POST /gateway/chat/completions (paraphrase — semantic HIT)")

paraphrase = {
    "model": ALIAS,
    "messages": [SYSTEM, {"role": "user", "content": "how much parental leave do employees get"}],
    "max_tokens": 60,
}

t0 = time.monotonic()
with httpx.Client(base_url=GATEWAY_BASE_URL, headers=HEADERS, timeout=30) as client:
    resp2 = client.post("/gateway/chat/completions", json=paraphrase)
hit_ms = int((time.monotonic() - t0) * 1000)

if resp2.status_code == 200:
    content2 = resp2.json()["choices"][0]["message"]["content"]
    print(f"  Response:  {content2[:80]!r}")
    print(f"  Latency:   {hit_ms}ms  (served from the semantic cache)")
    if hit_ms > 0:
        print(f"  Speedup:   {round(miss_ms / hit_ms, 1)}×  vs the first call")
    print("  Note: the exact cache would MISS this (different bytes); the semantic cache HITS.")
else:
    print(f"  Response: {resp2.status_code} — {resp2.text[:120]}")


# ── Step 4 — Confirm the decision reason in the routing log ───────────────────

sep("Step 4 — GET /gateway/requests (decision_reason)")

with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
    resp = client.get("/gateway/requests", params={"alias": ALIAS, "limit": 5})

if resp.status_code == 200:
    for r in resp.json().get("items", []):
        print(f"    {r['status']:<12}  decision={r.get('decision_reason')}")


# ── Step 5 — Cleanup ──────────────────────────────────────────────────────────

sep("Step 5 — DELETE /gateway/routes/{id} (cleanup)")

if route_id:
    with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
        resp = client.delete(f"/gateway/routes/{route_id}")
    print(f"  ✓ Route {route_id[:8]}… deleted." if resp.status_code == 204 else f"  {resp.status_code}")

print("\n✓ Example 33 complete.\n")
