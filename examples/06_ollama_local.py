"""
Example 6 — Local Ollama (OpenAI-compatible endpoint).

What this demonstrates
──────────────────────
- Pointing the OpenAI client at a local Ollama instance
- rl.instrument() works identically — no code changes needed vs cloud models
- model, input_tokens, output_tokens, latency_ms are all captured
- cost_usd will be NULL (no pricing row for local models — see note below)
- Routing via the RunLedger Model Gateway with an alias (USE_GATEWAY=true)

Prerequisites
─────────────
1. Install and start Ollama:  https://ollama.com
2. Pull a model:
       ollama pull llama3.2          # ~2 GB, good default
       ollama pull llama2            # classic alternative
       ollama pull mistral           # another option
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
    RUNLEDGER_API_KEY    — your workspace API key (workspace-scoped: all runs land in
                           the workspace this key belongs to; swap the key to switch
                           workspaces — you never pass workspace_id explicitly)
    RUNLEDGER_BASE_URL   — http://localhost:8000  (local Docker stack)
    RUNLEDGER_LOCAL      — set "true" to print events instead of sending to the API
    OLLAMA_BASE_URL      — http://localhost:11434/v1
    OLLAMA_MODEL         — e.g. llama3.2 or llama3.1:8b or llama2:latest
    USE_GATEWAY          — set "true" to route via RunLedger Model Gateway

⚠️  One process, one workspace
────────────────────────────────
rl.instrument() is a process-global patch — it can only be called once per process.
Calling it again with a different RunLedger(api_key=...) instance is silently ignored.

If you need to send data to multiple workspaces (e.g. multi-tenant testing), run
separate scripts / processes with different RUNLEDGER_API_KEY values, not multiple
RunLedger() instances in the same script.

Gateway setup (USE_GATEWAY=true)
─────────────────────────────────
Before running in gateway mode, create the "local" alias route in RunLedger:

    POST /gateway/routes
    {
      "alias": "local",
      "target_model": "llama3.2",
      "provider": "ollama",
      "base_url": "http://host.docker.internal:11434/v1",
      "priority": 1
    }

IMPORTANT — base_url must be "http://host.docker.internal:11434/v1" (NOT localhost).
The API container cannot reach localhost:11434 — that points to the container itself,
not your machine. host.docker.internal resolves to the host on Docker Desktop
(Mac/Windows) and via extra_hosts in docker-compose.yml (Linux).

You can also create this in the dashboard: Settings → Model Gateway → Add Route.

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
RUNLEDGER_BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
RUNLEDGER_API_KEY = os.getenv("RUNLEDGER_API_KEY", "")

# Set USE_GATEWAY=true to route via RunLedger Model Gateway instead of Ollama directly.
# The gateway alias "local" resolves to llama3.2 (primary) → mistral (fallback).
# See Gateway setup section in the docstring above for route configuration.
USE_GATEWAY = os.getenv("USE_GATEWAY", "false").lower() in ("1", "true", "yes")

# RUNLEDGER_LOCAL=true  → prints events as JSON to stdout (no running API needed)
# RUNLEDGER_LOCAL=false → sends events to your RunLedger container
LOCAL_MODE = os.getenv("RUNLEDGER_LOCAL", "false").lower() in ("1", "true", "yes")

if USE_GATEWAY:
    # Gateway endpoint is OpenAI-compatible — point the client at it.
    # The alias "local" is the model name; the gateway resolves the real model.
    EFFECTIVE_BASE_URL = f"{RUNLEDGER_BASE_URL}/gateway"
    EFFECTIVE_MODEL = "local"
    EFFECTIVE_API_KEY = RUNLEDGER_API_KEY
else:
    EFFECTIVE_BASE_URL = OLLAMA_BASE_URL
    EFFECTIVE_MODEL = MODEL
    EFFECTIVE_API_KEY = "ollama"

print(f"Mode            : {'gateway (local alias)' if USE_GATEWAY else 'direct Ollama'}")
print(f"Base URL        : {EFFECTIVE_BASE_URL}")
print(f"Model           : {EFFECTIVE_MODEL}")
print(f"RunLedger URL   : {RUNLEDGER_BASE_URL}")
print(f"Local mode      : {LOCAL_MODE}")

# ── 1. RunLedger client ───────────────────────────────────────────────────────
#
# Reads RUNLEDGER_API_KEY and RUNLEDGER_BASE_URL from .env automatically.
rl = RunLedger(local=LOCAL_MODE)

# ── 2. Instrument — patches openai.OpenAI so every call is captured ───────────
rl.instrument()

# ── 3. OpenAI client — direct Ollama or RunLedger gateway ────────────────────
#
# Both expose an OpenAI-compatible /chat/completions endpoint so the same
# client code works for both paths.
client = openai.OpenAI(
    base_url=EFFECTIVE_BASE_URL,
    api_key=EFFECTIVE_API_KEY,
)


# ── Agent: simple multi-turn Q&A ──────────────────────────────────────────────

QUESTIONS = [
    "What is a large language model? One sentence.",
    "Give me one real-world use case for it.",
    "What is the main cost driver when running these at scale?",
]


def run_chat(user_id: str, questions: list[str]) -> None:
    """Send a sequence of questions, maintaining conversation history."""

    history: list[dict[str, str]] = [
        {"role": "system", "content": "You are a concise, helpful assistant."},
    ]

    with rl.context(
        end_user_id=user_id,
        feature_tag="ollama-gateway-demo" if USE_GATEWAY else "ollama-demo",
        deployment_version="v1.0",
    ) as run_id:
        print(f"\n[RunLedger] run_id={run_id}")
        print(f"[Model]     {EFFECTIVE_MODEL}  ({EFFECTIVE_BASE_URL})\n")

        for question in questions:
            history.append({"role": "user", "content": question})

            response = client.chat.completions.create(
                model=EFFECTIVE_MODEL,
                messages=history,  # type: ignore[arg-type]
                temperature=0.7,
            )

            answer = response.choices[0].message.content or ""
            history.append({"role": "assistant", "content": answer})

            print(f"Q: {question}")
            print(f"A: {answer}")
            print()


if __name__ == "__main__":
    if USE_GATEWAY:
        print("\n── Via RunLedger Gateway (alias: local → llama3.2 / mistral fallback) ─")
        print("   Make sure you created the route with base_url=http://host.docker.internal:11434/v1")
        run_chat(user_id="user-gateway", questions=QUESTIONS)
    else:
        print("\n── Direct Ollama ──────────────────────────────────────────────────────")
        run_chat(user_id="user-direct", questions=QUESTIONS)

    # Flush all buffered events before exit
    rl.shutdown()
