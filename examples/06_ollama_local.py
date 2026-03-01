"""
Example 6 — Local Ollama (OpenAI-compatible endpoint).

What this demonstrates
──────────────────────
- Pointing the OpenAI client at a local Ollama instance
- rl.instrument() works identically — no code changes needed vs cloud models
- model, input_tokens, output_tokens, latency_ms are all captured
- cost_usd will be NULL (no pricing row for local models — see note below)

Prerequisites
─────────────
1. Install and start Ollama:  https://ollama.com
2. Pull a model:
       ollama pull llama3.2          # ~2 GB, good default
       ollama pull mistral           # alternative
       ollama pull qwen2.5:7b        # another option
3. Confirm it's running:
       curl http://localhost:11434/api/tags

Install the SDK (not on PyPI yet — install from source)
────────────────────────────────────────────────────────
Option A — local path (recommended if you have the repo):
    pip install -e "/path/to/runledger/packages/sdk[openai]"

Option B — directly from GitHub (no clone needed):
    pip install "runledger-sdk[openai] @ git+https://github.com/avs6/runledger.git#subdirectory=packages/sdk"

Also install:
    pip install openai python-dotenv

Run it
──────
    # Copy .env.example → .env and fill in your values, then:
    python 06_ollama_local.py

Key .env variables used here:
    RUNLEDGER_API_KEY    — your workspace API key
    RUNLEDGER_BASE_URL   — http://localhost:8000  (local Docker stack)
    RUNLEDGER_LOCAL      — set "true" to print events instead of sending to the API
    OLLAMA_BASE_URL      — http://localhost:11434/v1
    OLLAMA_MODEL         — e.g. llama3.2

Note on cost_usd
────────────────
Local models have no pricing row in RunLedger so cost_usd will be NULL.
To add one, use the settings page or POST /providers/pricing:

    curl -X POST http://localhost:8000/providers/pricing \\
         -H "Authorization: Bearer $RUNLEDGER_API_KEY" \\
         -H "Content-Type: application/json" \\
         -d '{
               "provider": "ollama",
               "model": "llama3.2",
               "input_cost_per_1m": "0.00",
               "output_cost_per_1m": "0.00"
             }'

Or just leave it NULL — useful to still track token volume and latency for
local models even when there's no dollar cost.
"""

from __future__ import annotations

import os

import openai
from dotenv import load_dotenv

from runledger_sdk import RunLedger

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

# RUNLEDGER_LOCAL=true  → prints events as JSON to stdout (no running API needed)
# RUNLEDGER_LOCAL=false → sends events to your RunLedger container
LOCAL_MODE = os.getenv("RUNLEDGER_LOCAL", "false").lower() in ("1", "true", "yes")

print(f"Ollama base URL : {OLLAMA_BASE_URL}")
print(f"Ollama model    : {MODEL}")
print(f"RunLedger URL   : {os.getenv('RUNLEDGER_BASE_URL', 'http://localhost:8000')}")
print(f"Local mode      : {LOCAL_MODE}")

# ── 1. RunLedger client ───────────────────────────────────────────────────────
#
# Reads RUNLEDGER_API_KEY and RUNLEDGER_BASE_URL from .env automatically.
rl = RunLedger(local=LOCAL_MODE)

# ── 2. Instrument — patches openai.OpenAI so every call is captured ───────────
rl.instrument()

# ── 3. OpenAI client pointed at Ollama ────────────────────────────────────────
#
# Ollama exposes an OpenAI-compatible REST API at /v1.
# api_key can be any non-empty string — Ollama ignores it.
client = openai.OpenAI(
    base_url=OLLAMA_BASE_URL,
    api_key="ollama",
)


# ── Agent: simple multi-turn Q&A ──────────────────────────────────────────────

def run_chat(user_id: str, questions: list[str]) -> None:
    """Send a sequence of questions, maintaining conversation history."""

    history: list[dict[str, str]] = [
        {"role": "system", "content": "You are a concise, helpful assistant."},
    ]

    with rl.context(
        end_user_id=user_id,
        feature_tag="ollama-demo",
        deployment_version="v1.0",
    ) as run_id:
        print(f"\n[RunLedger] run_id={run_id}")
        print(f"[Model]     {MODEL}  ({OLLAMA_BASE_URL})\n")

        for question in questions:
            history.append({"role": "user", "content": question})

            response = client.chat.completions.create(
                model=MODEL,
                messages=history,  # type: ignore[arg-type]
                temperature=0.7,
            )

            answer = response.choices[0].message.content or ""
            history.append({"role": "assistant", "content": answer})

            print(f"Q: {question}")
            print(f"A: {answer}")
            print()


if __name__ == "__main__":
    run_chat(
        user_id="user-local",
        questions=[
            "What is a large language model? One sentence.",
            "Give me one real-world use case for it.",
            "What is the main cost driver when running these at scale?",
        ],
    )

    # Flush all buffered events before exit
    rl.shutdown()
