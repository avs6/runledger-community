"""
Example 15 — Prompt Management

Demonstrates:
  1. POST /prompts              — create a named prompt template
  2. POST /prompts/{name}/versions — commit v1 (staging) and v2 (staging)
  3. POST /prompts/{name}/promote  — promote staging → production
  4. GET  /prompts/{name}/latest   — pull the latest production version
  5. rl.get_prompt()           — SDK fetch with {{variable}} substitution + 60s cache
  6. GET  /prompts/{name}/metrics  — per-version run count, avg cost, avg score
  7. GET  /prompts              — list all prompts

Install
───────
    pip install httpx python-dotenv

    # SDK (for step 5 only):
    pip install -e "path/to/runledger/packages/sdk[openai]"

Run it
──────
    # Copy .env.example → .env, then:
    python 15_prompts.py

Key .env variables:
    RUNLEDGER_API_KEY   — your workspace API key
    RUNLEDGER_BASE_URL  — http://localhost:8000  (default)
"""

from __future__ import annotations

import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")

if not API_KEY:
    print("ERROR: RUNLEDGER_API_KEY env var is required", file=sys.stderr)
    sys.exit(1)

HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
PROMPT_NAME = "support-agent-demo"


def sep(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print("─" * 60)


# ── Step 1 — Create a prompt ───────────────────────────────────────────────────

sep("Step 1 — POST /prompts (create prompt)")

with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
    resp = client.post("/prompts", json={
        "name": PROMPT_NAME,
        "description": "Customer support agent system prompt",
        "default_environment": "production",
    })

if resp.status_code == 201:
    prompt = resp.json()
    print(f"  Created: name={prompt['name']}  id={prompt['id'][:8]}…")
elif resp.status_code == 409:
    print(f"  Already exists — continuing with existing prompt")
else:
    print(f"  ERROR {resp.status_code}: {resp.text}")


# ── Step 2 — Commit two staging versions ──────────────────────────────────────

sep("Step 2 — POST /prompts/{name}/versions (commit v1 + v2 to staging)")

with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
    r1 = client.post(f"/prompts/{PROMPT_NAME}/versions", json={
        "content": "You are a helpful support agent. Greet {{user_name}} warmly.",
        "variables": [{"name": "user_name", "type": "string", "description": "Customer name"}],
        "commit_message": "Initial draft",
        "environment": "staging",
        "model_hint": "gpt-4o-mini",
    })

if r1.status_code == 201:
    v1 = r1.json()
    print(f"  v{v1['version']} committed to staging — id={v1['id'][:8]}…")
else:
    print(f"  ERROR {r1.status_code}: {r1.text}")

with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
    r2 = client.post(f"/prompts/{PROMPT_NAME}/versions", json={
        "content": (
            "You are a helpful, friendly support agent for {{company}}. "
            "Welcome {{user_name}}! How can I assist you today?"
        ),
        "variables": [
            {"name": "user_name", "type": "string", "description": "Customer name"},
            {"name": "company", "type": "string", "description": "Company name"},
        ],
        "commit_message": "Add company variable + friendlier tone",
        "environment": "staging",
        "model_hint": "gpt-4o-mini",
    })

if r2.status_code == 201:
    v2 = r2.json()
    print(f"  v{v2['version']} committed to staging — id={v2['id'][:8]}…")
else:
    print(f"  ERROR {r2.status_code}: {r2.text}")


# ── Step 3 — Promote staging → production ─────────────────────────────────────

sep("Step 3 — POST /prompts/{name}/promote (staging → production)")

with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
    resp = client.post(f"/prompts/{PROMPT_NAME}/promote", json={
        "source_environment": "staging",
        "target_environment": "production",
        "commit_message": "Promote v2 to production",
    })

if resp.status_code == 201:
    promoted = resp.json()
    print(f"  Promoted: v{promoted['version']} → production  id={promoted['id'][:8]}…")
else:
    print(f"  ERROR {resp.status_code}: {resp.text}")


# ── Step 4 — Pull the latest production version via HTTP ──────────────────────

sep("Step 4 — GET /prompts/{name}/latest?environment=production")

with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
    resp = client.get(f"/prompts/{PROMPT_NAME}/latest", params={"environment": "production"})

if resp.status_code == 200:
    latest = resp.json()
    print(f"  Latest production: v{latest['version']}")
    print(f"  Model hint:  {latest['model_hint']}")
    print(f"  Content:     {latest['content'][:80]}…")
else:
    print(f"  ERROR {resp.status_code}: {resp.text}")


# ── Step 5 — SDK rl.get_prompt() with variable substitution ───────────────────

sep("Step 5 — rl.get_prompt() via SDK ({{variable}} substitution + 60s cache)")

try:
    from runledger_sdk import RunLedger  # type: ignore[import]

    rl = RunLedger()

    rendered = rl.get_prompt(
        PROMPT_NAME,
        environment="production",
        variables={"user_name": "Alice", "company": "Acme Corp"},
    )
    print(f"  Fetched version: v{rendered['version']}")
    print(f"  Rendered content:")
    print(f"    {rendered['content']}")

    # Second call hits the cache (no HTTP request)
    rendered2 = rl.get_prompt(PROMPT_NAME, environment="production",
                               variables={"user_name": "Bob", "company": "Globex"})
    print(f"  Second call (cached): {rendered2['content']}")

    rl.shutdown()

except ImportError:
    print("  runledger-sdk not installed — skipping SDK demo")
    print("  Install: pip install -e path/to/runledger/packages/sdk")


# ── Step 6 — Per-version metrics ──────────────────────────────────────────────

sep("Step 6 — GET /prompts/{name}/metrics (per-version run count + avg cost + avg score)")

with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
    resp = client.get(f"/prompts/{PROMPT_NAME}/metrics")

if resp.status_code == 200:
    items = resp.json()["items"]
    if not items:
        print("  No versions yet — run some agent calls with deployment_version set.")
    for item in items:
        avg_cost = f"${item['avg_cost_usd']:.4f}" if item["avg_cost_usd"] is not None else "—"
        avg_score = f"{item['avg_score']:.2f}" if item["avg_score"] is not None else "—"
        print(
            f"  v{item['version']:2d}  [{item['environment']:10s}]"
            f"  runs={item['run_count']:4d}  avg_cost={avg_cost:8s}  avg_score={avg_score}"
            f"  {item['commit_message'] or ''}"
        )
else:
    print(f"  ERROR {resp.status_code}: {resp.text}")


# ── Step 7 — List all prompts ──────────────────────────────────────────────────

sep("Step 7 — GET /prompts (list all prompts)")

with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
    resp = client.get("/prompts")

if resp.status_code == 200:
    items = resp.json()["items"]
    print(f"  {len(items)} prompt(s) in workspace:")
    for p in items:
        print(f"    {p['name']:30s}  env={p['default_environment']:10s}  created={p['created_at'][:10]}")
else:
    print(f"  ERROR {resp.status_code}: {resp.text}")


print("\n✓ Example 15 complete.\n")
print("Tip: set deployment_version=f'{PROMPT_NAME}:{version}' in rl.context() to")
print("link agent runs to prompt versions and see cost + score metrics per version.")
