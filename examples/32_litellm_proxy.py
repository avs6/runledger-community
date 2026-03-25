"""
Example 32 — LiteLLM Proxy Gateway Coexistence
================================================

RunLedger and LiteLLM Proxy can run side-by-side.  This example shows
three complementary integration patterns — choose the one that fits your
architecture.

┌─────────────────────────────────────────────────────────────────────────┐
│  Pattern A  │  Direct SDK instrumentation (no proxy)                    │
│  Pattern B  │  OpenAI client → LiteLLM Proxy → provider                │
│  Pattern C  │  RunLedger Gateway → LiteLLM Proxy → provider            │
└─────────────────────────────────────────────────────────────────────────┘

──────────────────────────────────────────────────────────────────────────
Pattern A — LiteLLM SDK (no proxy)
──────────────────────────────────────────────────────────────────────────
Use ``rl.instrument_litellm()`` to intercept calls made directly through
the LiteLLM Python SDK.  No proxy process needed.

  your app ──litellm.completion()──▶ RunLedger SDK ──▶ OpenAI / Anthropic /…

──────────────────────────────────────────────────────────────────────────
Pattern B — OpenAI client pointing at LiteLLM Proxy
──────────────────────────────────────────────────────────────────────────
Use ``rl.instrument()`` (OpenAI instrumentation) and set the client's
base_url to the LiteLLM Proxy endpoint.  Every call goes through the proxy
and is still tracked by RunLedger.

  your app ──openai.chat.completions.create()──▶ RunLedger SDK
                                                  └──▶ LiteLLM Proxy :4000
                                                        └──▶ OpenAI / Anthropic /…

  Start LiteLLM Proxy:
      litellm --model gpt-4o --model claude-3-5-sonnet-20241022 --port 4000

──────────────────────────────────────────────────────────────────────────
Pattern C — RunLedger Gateway routing through LiteLLM Proxy
──────────────────────────────────────────────────────────────────────────
Register LiteLLM Proxy as a gateway route inside RunLedger.  RunLedger
handles prompt caching, cost-cap enforcement, routing policies, and audit
logging.  LiteLLM Proxy handles provider fan-out, retries, and load
balancing.

  your app ──▶ RunLedger Gateway :8000/gateway
                 ├── prompt cache (SHA-256, 24 h TTL)
                 ├── cost-cap enforcement
                 └──▶ LiteLLM Proxy :4000
                        ├── load balancing
                        ├── provider retries
                        └──▶ OpenAI / Anthropic / Bedrock /…

Install
───────
    pip install litellm openai runledger-sdk python-dotenv httpx

Run
───
    # Terminal 1 — start LiteLLM Proxy (requires OPENAI_API_KEY in env):
    litellm --model gpt-4o --model claude-3-5-sonnet-20241022 --port 4000

    # Terminal 2 — run this example:
    python 32_litellm_proxy.py

.env variables:
    RUNLEDGER_API_KEY    — your workspace API key
    RUNLEDGER_BASE_URL   — http://localhost:8000  (RunLedger API)
    LITELLM_PROXY_URL    — http://localhost:4000  (LiteLLM Proxy)
    LITELLM_PROXY_KEY    — master key set in litellm config (or leave blank)
    OPENAI_API_KEY       — required by LiteLLM Proxy
"""

from __future__ import annotations

import os
import sys
import time

import httpx
import openai
from dotenv import load_dotenv

from runledger_sdk import RunLedger

load_dotenv()

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")
LITELLM_PROXY_URL = os.getenv("LITELLM_PROXY_URL", "http://localhost:4000")
LITELLM_PROXY_KEY = os.getenv("LITELLM_PROXY_KEY", "sk-litellm-proxy")

if not API_KEY:
    print("ERROR: RUNLEDGER_API_KEY env var is required", file=sys.stderr)
    sys.exit(1)

HEADERS = {"Authorization": f"Bearer {API_KEY}"}

# ═════════════════════════════════════════════════════════════════════════════
# Pattern A — LiteLLM SDK instrumentation (no proxy needed)
# ═════════════════════════════════════════════════════════════════════════════

print("=" * 70)
print("Pattern A — LiteLLM SDK instrumentation")
print("=" * 70)

import litellm  # noqa: E402

rl_a = RunLedger(api_key=API_KEY, base_url=BASE_URL)
rl_a.instrument_litellm()

openai_key = os.getenv("OPENAI_API_KEY")
if openai_key:
    with rl_a.context(end_user_id="user-pattern-a", feature_tag="direct-sdk"):
        try:
            resp = litellm.completion(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Say 'hello' in one word."}],
                api_key=openai_key,
            )
            print(f"  ✓ gpt-4o-mini: {resp.choices[0].message.content!r}")
        except Exception as exc:
            print(f"  ✗ {exc}")
else:
    print("  ⚠  Skipped — OPENAI_API_KEY not set")

rl_a.flush()


# ═════════════════════════════════════════════════════════════════════════════
# Pattern B — OpenAI client → LiteLLM Proxy
# ═════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("Pattern B — OpenAI client → LiteLLM Proxy")
print("=" * 70)

# Check if LiteLLM Proxy is running
proxy_alive = False
try:
    health = httpx.get(f"{LITELLM_PROXY_URL}/health", timeout=2)
    proxy_alive = health.status_code < 500
except Exception:
    pass

if not proxy_alive:
    print(f"  ⚠  LiteLLM Proxy not reachable at {LITELLM_PROXY_URL}")
    print("     Start it with: litellm --model gpt-4o --port 4000")
else:
    rl_b = RunLedger(api_key=API_KEY, base_url=BASE_URL)
    rl_b.instrument()  # patches openai.chat.completions.create

    # Point OpenAI client at LiteLLM Proxy — RunLedger intercepts before forwarding
    client = openai.OpenAI(
        base_url=f"{LITELLM_PROXY_URL}/v1",
        api_key=LITELLM_PROXY_KEY,
    )

    with rl_b.context(end_user_id="user-pattern-b", feature_tag="via-litellm-proxy"):
        try:
            resp = client.chat.completions.create(
                model="gpt-4o",  # LiteLLM Proxy selects backend by model name
                messages=[{"role": "user", "content": "What year is it?"}],
            )
            print(f"  ✓ via LiteLLM Proxy: {resp.choices[0].message.content!r}")
            print(f"    model={resp.model}  tokens={resp.usage.total_tokens}")
        except Exception as exc:
            print(f"  ✗ {exc}")

    rl_b.flush()


# ═════════════════════════════════════════════════════════════════════════════
# Pattern C — RunLedger Gateway → LiteLLM Proxy
# ═════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("Pattern C — RunLedger Gateway → LiteLLM Proxy")
print("=" * 70)

if not proxy_alive:
    print(f"  ⚠  LiteLLM Proxy not reachable at {LITELLM_PROXY_URL}")
    print("     Start it with: litellm --model gpt-4o --port 4000")
    sys.exit(0)

# Step C-1: Register LiteLLM Proxy as a RunLedger gateway route
print("\n  C-1  Creating gateway route → LiteLLM Proxy …")
route_payload = {
    "name": "litellm-proxy",
    "provider": "openai",  # proxy speaks OpenAI API
    "target_model": "gpt-4o",
    "base_url": f"{LITELLM_PROXY_URL}/v1",
    "api_key_env_var": "LITELLM_PROXY_KEY",  # set this on the RunLedger server
    "priority": 1,
    "is_active": True,
    # Optional spend controls:
    "daily_cost_limit_usd": 10.0,  # hard-stop at $10/day
    "pii_redaction_enabled": True,  # strip PII before forwarding to LiteLLM
}

route_id = None
try:
    r = httpx.post(
        f"{BASE_URL}/gateway/routes",
        json=route_payload,
        headers=HEADERS,
        timeout=10,
    )
    if r.status_code == 201:
        route_id = r.json()["id"]
        print(f"     Created route {route_id}")
    elif r.status_code == 422:
        # Route with same name may already exist — list and reuse
        routes = httpx.get(f"{BASE_URL}/gateway/routes", headers=HEADERS, timeout=10).json()
        for rt in routes.get("items", []):
            if rt["name"] == "litellm-proxy":
                route_id = rt["id"]
                print(f"     Reusing existing route {route_id}")
                break
    else:
        print(f"     Could not create route: {r.status_code} {r.text}")
except Exception as exc:
    print(f"     {exc}")

# Step C-2: Send completions through RunLedger Gateway (which calls LiteLLM Proxy)
if route_id:
    print("\n  C-2  Sending completions through RunLedger Gateway …")
    gateway_client = openai.OpenAI(
        base_url=f"{BASE_URL}/gateway/v1",
        api_key=API_KEY,
    )

    messages = [{"role": "user", "content": "Name the planets of the solar system."}]

    # First call — cache miss
    t0 = time.perf_counter()
    try:
        resp1 = gateway_client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
        )
        ms1 = int((time.perf_counter() - t0) * 1000)
        print(f"     Call 1 (cache miss):  {ms1} ms — {resp1.choices[0].message.content[:60]}…")
    except Exception as exc:
        print(f"     Call 1 error: {exc}")

    # Second call — same prompt → cache hit
    t0 = time.perf_counter()
    try:
        resp2 = gateway_client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
        )
        ms2 = int((time.perf_counter() - t0) * 1000)
        print(f"     Call 2 (cache hit):   {ms2} ms — {resp2.choices[0].message.content[:60]}…")
    except Exception as exc:
        print(f"     Call 2 error: {exc}")

    # Step C-3: Gateway stats
    print("\n  C-3  Gateway stats …")
    try:
        stats = httpx.get(
            f"{BASE_URL}/gateway/stats",
            headers=HEADERS,
            timeout=10,
        ).json()
        total = stats.get("total_requests", 0)
        hits = stats.get("cache_hits", 0)
        hit_rate = stats.get("cache_hit_rate_pct", 0)
        print(f"     total_requests={total}  cache_hits={hits}  hit_rate={hit_rate:.1f}%")
    except Exception as exc:
        print(f"     {exc}")

    # Cleanup — remove the test route
    print("\n  C-4  Cleaning up test route …")
    try:
        httpx.delete(
            f"{BASE_URL}/gateway/routes/{route_id}",
            headers=HEADERS,
            timeout=10,
        )
        print("     Route deleted")
    except Exception as exc:
        print(f"     {exc}")

# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("Summary")
print("=" * 70)
print("""
  Pattern A  Direct LiteLLM SDK — rl.instrument_litellm()
             Best when you own the LiteLLM call sites.

  Pattern B  OpenAI client → LiteLLM Proxy — rl.instrument()
             Best when LiteLLM Proxy is already in your stack and you want
             RunLedger to observe calls without touching LiteLLM config.

  Pattern C  RunLedger Gateway → LiteLLM Proxy
             Best for production: RunLedger adds prompt caching, cost-cap
             enforcement, PII redaction, and audit logging in front of
             LiteLLM Proxy's provider fan-out and retries.

Open the RunLedger dashboard → Model Gateway → Routing Log to see all
proxied calls, cache decisions, and cost attribution.
""")
