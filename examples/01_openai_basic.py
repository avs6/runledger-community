"""
Example 1 — OpenAI instrumentation (simplest possible setup).

What this demonstrates
──────────────────────
- One-line instrumentation via rl.instrument()
- Attaching user / session / feature metadata via rl.context()
- Automatic capture of: model, input_tokens, output_tokens, latency_ms, cost_usd
- run_id is auto-generated and returned by the context manager

Run it
──────
    export RUNLEDGER_API_KEY=rl_live_...
    export OPENAI_API_KEY=sk-...
    uv run python examples/01_openai_basic.py
"""

from __future__ import annotations

import openai

from runledger_sdk import RunLedger

# ── 1. Create the RunLedger client ────────────────────────────────────────────
#
# local=True  → events are printed to stdout as JSON (no API key needed)
# Drop local=True and set RUNLEDGER_API_KEY to send to the real API.
rl = RunLedger(
    api_key=None,   # reads RUNLEDGER_API_KEY env var automatically
    local=True,     # remove this line once you have a live API running
)

# ── 2. Instrument OpenAI ──────────────────────────────────────────────────────
#
# This monkey-patches openai.OpenAI and openai.AsyncOpenAI so every
# chat.completions.create call is automatically captured.  Call once at
# startup — it's idempotent.
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
