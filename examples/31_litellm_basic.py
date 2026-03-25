"""
Example 31 — LiteLLM SDK Instrumentation
=========================================

One ``rl.instrument_litellm()`` call tracks every provider that LiteLLM
supports — OpenAI, Anthropic, Gemini, Mistral, Groq, Ollama, Bedrock,
Azure, Together AI, and 100+ more — through a single RunLedger workspace.

What this example demonstrates
───────────────────────────────
1. Instrument LiteLLM with one line
2. Multi-model calls routed by LiteLLM (GPT-4o, Claude, Gemini)
3. Context manager for per-user cost attribution
4. Budget enforcement across providers
5. Cost comparison query across the three calls
6. Async completion (``litellm.acompletion``)

How provider detection works
────────────────────────────
LiteLLM model names follow a "provider/model" prefix convention:
  gpt-4o                              → openai
  claude-3-5-sonnet-20241022          → anthropic
  gemini/gemini-1.5-pro               → google
  mistral/mistral-large-latest        → mistral
  groq/llama3-70b-8192                → groq
  ollama/llama3                       → ollama
  azure/gpt-4                         → azure
  bedrock/anthropic.claude-3-5-…      → bedrock

RunLedger automatically extracts the provider so spend-by-provider
and cost-per-model analytics work out of the box.

LiteLLM cost estimates
───────────────────────
LiteLLM computes its own cost estimate on each response (available on
``result._hidden_params["response_cost"]``).  RunLedger captures this
as ``reported_cost_usd`` (cost_source="litellm") alongside its own
pricing-engine calculation — giving you two independent cost signals
for reconciliation.

Install
───────
    pip install litellm runledger-sdk python-dotenv

Run
───
    # All three API keys must be set in .env for all three calls to work.
    # Comment out any call whose key you don't have.
    python 31_litellm_basic.py

.env variables:
    RUNLEDGER_API_KEY   — your workspace API key
    RUNLEDGER_BASE_URL  — http://localhost:8000  (default)
    OPENAI_API_KEY      — required for gpt-4o call
    ANTHROPIC_API_KEY   — required for claude call
    GOOGLE_API_KEY      — required for gemini call
"""

from __future__ import annotations

import asyncio
import os
import sys

import httpx
import litellm
from dotenv import load_dotenv

from runledger_sdk import RunLedger

load_dotenv()

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")

if not API_KEY:
    print("ERROR: RUNLEDGER_API_KEY env var is required", file=sys.stderr)
    sys.exit(1)

# ── 1. Initialise RunLedger and instrument LiteLLM ───────────────────────────

rl = RunLedger(
    api_key=API_KEY,
    base_url=BASE_URL,
    budget_check=True,  # optional: enforce spend guardrails pre-call
)
rl.instrument_litellm()

print("✓ LiteLLM instrumented — all provider calls will be tracked")

# ── 2. Multi-model calls with per-user context ────────────────────────────────

PROMPT = "In one sentence, what is the capital of France?"

models = [
    ("gpt-4o", "openai", os.getenv("OPENAI_API_KEY")),
    ("claude-3-5-sonnet-20241022", "anthropic", os.getenv("ANTHROPIC_API_KEY")),
    ("gemini/gemini-1.5-flash", "google", os.getenv("GOOGLE_API_KEY")),
]

run_ids = []

for model, provider, key in models:
    if not key:
        print(f"  ⚠  Skipping {model} — no API key found")
        continue

    with rl.context(
        end_user_id="demo-user-42",
        feature_tag="capital-quiz",
        deployment_version="v1.0",
    ):
        print(f"\n── {provider} / {model} ──────────────────────────────────────")
        try:
            response = litellm.completion(
                model=model,
                messages=[{"role": "user", "content": PROMPT}],
                api_key=key,
            )
            content = response.choices[0].message.content
            tokens_in = response.usage.prompt_tokens
            tokens_out = response.usage.completion_tokens

            # LiteLLM's own cost estimate
            cost_estimate = None
            hidden = getattr(response, "_hidden_params", {})
            if isinstance(hidden, dict):
                cost_estimate = hidden.get("response_cost")

            print(f"  Response:  {content}")
            print(f"  Tokens:    {tokens_in} in / {tokens_out} out")
            if cost_estimate is not None:
                print(f"  LiteLLM cost estimate: ${cost_estimate:.6f}")

        except Exception as exc:
            print(f"  Error: {exc}")

# ── 3. Async completion ───────────────────────────────────────────────────────


async def async_example() -> None:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        print("\n⚠  Skipping async example — OPENAI_API_KEY not set")
        return

    print("\n── Async completion ─────────────────────────────────────────────")
    with rl.context(end_user_id="demo-user-async", feature_tag="async-demo"):
        response = await litellm.acompletion(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'hello' in three languages."}],
            api_key=key,
        )
        print(f"  {response.choices[0].message.content}")


asyncio.run(async_example())

# ── 4. Flush and check analytics ─────────────────────────────────────────────

rl.flush()
print("\n✓ Events flushed to RunLedger")

# Query spend broken down by provider
print("\n── Spend by provider (last hour) ───────────────────────────────────")
try:
    resp = httpx.get(
        f"{BASE_URL}/analytics/spend-by-model",
        headers={"Authorization": f"Bearer {API_KEY}"},
        params={"limit": 10},
        timeout=10,
    )
    if resp.status_code == 200:
        for row in resp.json().get("items", []):
            print(
                f"  {row['provider']:12s}  {row['model']:40s}"
                f"  ${float(row['cost_usd']):.6f}  "
                f"({row['call_count']} calls)"
            )
    else:
        print(f"  Analytics returned {resp.status_code}")
except Exception as exc:
    print(f"  Could not fetch analytics: {exc}")

print("\nDone.  Open the RunLedger dashboard to view the Runs Explorer and")
print("Economics page for a cross-provider cost breakdown.")
