"""
Lab 03 — Model Gateway proxy.

WHAT THIS IS
────────────
The **AI Test Team** doesn't want provider details baked into agent code. Instead
they call a stable **alias** ("qa-chat") through the RunLedger Gateway, and an
org admin decides which real model serves it, applies semantic caching, and records
every call. Swapping the underlying model is a dashboard change — no redeploy.

This is the *proxy* path: your OpenAI client points at RunLedger's OpenAI-compatible
`/gateway` endpoint instead of at a provider. RunLedger is in the request path here
(unlike Labs 01/02), so it can cache and route.

DO THIS FIRST (dashboard -> Gateway, org admin)
───────────────────────────────────
Create a route so the alias resolves:
    Alias:        qa-chat
    Provider:     ollama
    Target model: llama3.2
    Base URL:     http://host.docker.internal:11434/v1      ← NOT localhost!
    Priority:     1
    Semantic cache: ON
(The Gateway runs *inside Docker*; it reaches your host's Ollama via
host.docker.internal, never localhost — localhost would mean the container itself.)

PREREQUISITES
─────────────
  • Workspace API key in agents/.env  (this key authenticates to the gateway)
  • The "qa-chat" route created above by an org admin
  • pip install -r requirements.txt

RUN
───
    python lab_03_gateway_proxy.py

THEN VERIFY (dashboard → Gateway, then Runs)
────────────────────────────────────────────
  • Gateway page: request count on the qa-chat route goes up.
  • We send the SAME question twice — with semantic cache ON the second call is a
    cache HIT (near-zero latency, no Ollama round-trip). Watch the cache stats.
  • Runs page: the calls appear as usual, tagged feature_tag="qa-regression".
"""

from __future__ import annotations

import openai
from _config import RUNLEDGER_BASE_URL, banner, dashboard_url, require_key
from runledger_sdk import RunLedger

ALIAS = "qa-chat"  # must match the route alias you created in the Gateway page
QUESTION = "In one sentence, what does a regression test verify?"


def main() -> None:
    banner("Lab 03 · Model Gateway proxy · AI Test Team")
    key = require_key()

    # Inline SDK is optional here; we add it so runs are also tagged with context.
    rl = RunLedger()
    rl.instrument()

    # The OpenAI client points at RunLedger's gateway, using the workspace key.
    # The "model" is the ALIAS — the gateway resolves it to the real Ollama model.
    client = openai.OpenAI(base_url=f"{RUNLEDGER_BASE_URL}/gateway", api_key=key)

    for attempt in ("first call (cache miss)", "second call (semantic-cache hit)"):
        with rl.context(end_user_id="qa_bot", feature_tag="qa-regression"):
            resp = client.chat.completions.create(
                model=ALIAS,
                messages=[{"role": "user", "content": QUESTION}],
                temperature=0.0,  # deterministic → ideal for cache demonstration
            )
            answer = (resp.choices[0].message.content or "").strip()
            print(f"\n[{attempt}]")
            print(f"  A: {answer[:200]}")

    rl.shutdown()
    print(f"\n✓ Done. Open {dashboard_url()}/gateway — check the qa-chat route + cache stats.")


if __name__ == "__main__":
    main()
