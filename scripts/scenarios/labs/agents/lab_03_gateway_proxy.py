"""
Lab 03 - Model gateway proxy.

This exercises the LocalAIAgentStack / LiteLLM Gateway workspace through the
RunLedger gateway alias `qa-chat`.
"""

from __future__ import annotations

import openai
from _config import RUNLEDGER_BASE_URL, banner, dashboard_url, require_key
from runledger_sdk import RunLedger

ALIAS = "qa-chat"
QUESTION = "In one sentence, what does a regression test verify?"


def main() -> None:
    banner("Lab 03 - Model Gateway proxy - LocalAIAgentStack / LiteLLM Gateway")
    key = require_key()

    rl = RunLedger()
    rl.instrument()

    client = openai.OpenAI(base_url=f"{RUNLEDGER_BASE_URL}/gateway", api_key=key)

    for attempt in ("first call (cache miss)", "second call (semantic-cache hit)"):
        with rl.context(end_user_id="qa_bot", feature_tag="qa-regression"):
            resp = client.chat.completions.create(
                model=ALIAS,
                messages=[{"role": "user", "content": QUESTION}],
                temperature=0.0,
            )
            answer = (resp.choices[0].message.content or "").strip()
            print(f"\n[{attempt}]")
            print(f"  A: {answer[:200]}")

    rl.shutdown()
    print(f"\nDone. Open {dashboard_url()}/gateway and inspect the qa-chat route.")


if __name__ == "__main__":
    main()
