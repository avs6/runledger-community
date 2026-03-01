"""
Example 1 — OpenAI instrumentation (simplest possible setup).

What this demonstrates
──────────────────────
- One-line instrumentation via rl.instrument()
- Attaching user / session / feature metadata via rl.context()
- Automatic capture of: model, input_tokens, output_tokens, latency_ms, cost_usd
- run_id is auto-generated and returned by the context manager

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
    python 01_openai_basic.py

Key .env variables used here:
    RUNLEDGER_API_KEY    — your workspace API key
    RUNLEDGER_BASE_URL   — http://localhost:8000  (local Docker stack)
    RUNLEDGER_LOCAL      — set "true" to print events instead of sending to the API
    OPENAI_API_KEY       — your OpenAI key
"""

from __future__ import annotations

import os

import openai
from dotenv import load_dotenv

from runledger_sdk import RunLedger

# Load variables from .env file (copy .env.example → .env first)
load_dotenv()

# RUNLEDGER_LOCAL=true  → prints events as JSON to stdout (no running API needed)
# RUNLEDGER_LOCAL=false → sends events to your RunLedger API container
LOCAL_MODE = os.getenv("RUNLEDGER_LOCAL", "false").lower() in ("1", "true", "yes")

# ── 1. Create the RunLedger client ────────────────────────────────────────────
#
# Reads RUNLEDGER_API_KEY and RUNLEDGER_BASE_URL from .env automatically.
rl = RunLedger(local=LOCAL_MODE)

# ── 2. Instrument OpenAI ──────────────────────────────────────────────────────
#
# Monkey-patches openai.OpenAI and openai.AsyncOpenAI so every
# chat.completions.create call is automatically captured. Idempotent.
rl.instrument()

# ── 3. Create an ordinary OpenAI client ───────────────────────────────────────
client = openai.OpenAI()


def answer_question(user_id: str, question: str) -> str:
    """Ask a single question and return the answer."""

    # ── 4. Open a RunLedger context ───────────────────────────────────────────
    #
    # Everything inside the `with` block is tagged with this metadata.
    # run_id is a UUID auto-generated for this run.
    with rl.context(
        end_user_id=user_id,
        feature_tag="qa-demo",
        deployment_version="v1.0",
    ) as run_id:
        print(f"[RunLedger] run_id={run_id}")

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a concise, helpful assistant."},
                {"role": "user", "content": question},
            ],
        )

        return response.choices[0].message.content or ""


if __name__ == "__main__":
    answer = answer_question(
        user_id="user-alice",
        question="What is the capital of France? One word only.",
    )
    print(f"Answer: {answer}")

    # ── 5. Flush and shut down ────────────────────────────────────────────────
    #
    # Ensures all buffered events are sent before the process exits.
    # In a long-running server you can omit this and rely on periodic flushing.
    rl.shutdown()
