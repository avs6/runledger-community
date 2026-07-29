"""
Lab 01 — Inline SDK instrumentation (the "2-line" integration).

WHAT THIS IS
────────────
This is the code a developer on the **AI Support Team** would write. The
RunLedger SDK patches the OpenAI client, so every model call your agent makes is
captured automatically — model, tokens, latency, and cost — with zero changes to
your actual agent logic. This is the *inline* path: the SDK sits in-process with
your agent.

We point the standard OpenAI client at your local Ollama, so no cloud key is
needed. The same code works unchanged against OpenAI/Anthropic in production.

PREREQUISITES
─────────────
  • The stack is up and you minted a workspace API key → agents/.env
  • Ollama is running with a model pulled:  ollama pull llama3.2
  • pip install -r requirements.txt

RUN
───
    python lab_01_inline_sdk.py

THEN VERIFY (dashboard → Runs)
──────────────────────────────
  • New runs tagged feature_tag="support-chat", end_user_id="cust_*"
  • Each run shows tokens + latency; cost appears once you've uploaded pricing
    (Lab guide Module 2) and Celery enriches it (~30–60s).
  • Open a run to see the provider_call (model=llama3.2) and the quality score.
"""

from __future__ import annotations

import openai
from _config import OLLAMA_BASE_URL, OLLAMA_MODEL, banner, dashboard_url, require_key
from runledger_sdk import RunLedger

# A tiny "knowledge base" so the support bot has something to answer from.
FAQ = (
    "Refunds are processed within 5 business days. "
    "You can reset your password from the login page. "
    "Our support hours are 9am–6pm Eastern, Monday to Friday."
)

TICKETS = [
    ("cust_101", "How long do refunds take?"),
    ("cust_102", "I forgot my password, what do I do?"),
    ("cust_103", "Are you open on weekends?"),
]


def main() -> None:
    banner("Lab 01 · Inline SDK instrumentation · AI Support Team")
    require_key()

    # ── 1. One line: create the client. It reads RUNLEDGER_API_KEY + BASE_URL from env.
    rl = RunLedger()

    # ── 2. One line: patch the OpenAI SDK. Every call is now tracked.
    rl.instrument()

    # ── 3. Your normal OpenAI client — just pointed at Ollama.
    client = openai.OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")

    for user_id, question in TICKETS:
        # A `context` groups all model calls in the block into one "run" and tags
        # it with who the end user is and what feature they were using.
        with rl.context(end_user_id=user_id, feature_tag="support-chat") as run_id:
            resp = client.chat.completions.create(
                model=OLLAMA_MODEL,
                messages=[
                    {"role": "system", "content": f"You are a support bot. Facts: {FAQ}"},
                    {"role": "user", "content": question},
                ],
                temperature=0.2,
            )
            answer = (resp.choices[0].message.content or "").strip()

            # Attach a quality score to this run (source="human" simulates an agent rating).
            # In real life this could come from a human reviewer or an LLM judge.
            rl.score("helpfulness", 0.9, label="good", source="human")

            print(f"\n[run {run_id[:8]}]  {user_id}")
            print(f"  Q: {question}")
            print(f"  A: {answer[:200]}")

    # ── 4. Flush buffered events before the process exits.
    rl.shutdown()

    print(f"\n✓ Done. Open {dashboard_url()}/runs — filter by feature 'support-chat'.")


if __name__ == "__main__":
    main()
