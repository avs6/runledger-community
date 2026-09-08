"""
Lab 05 - Business outcomes and evaluation scores.

This uses HomeLab / AgentTest to attach quality scores and business outcomes to runs.
"""

from __future__ import annotations

import random

import openai
from _config import OLLAMA_BASE_URL, OLLAMA_MODEL, banner, dashboard_url, require_key
from runledger_sdk import RunLedger

TICKETS = [
    ("cust_201", "My invoice looks wrong, can you help?"),
    ("cust_202", "How do I export my data?"),
    ("cust_203", "The app crashes when I upload a file."),
    ("cust_204", "Can I change my subscription plan?"),
    ("cust_205", "I was charged twice this month."),
]


def main() -> None:
    banner("Lab 05 - Outcomes + scores - HomeLab / AgentTest")
    require_key()

    rl = RunLedger()
    rl.instrument()
    client = openai.OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")

    for user_id, question in TICKETS:
        with rl.context(end_user_id=user_id, feature_tag="support-chat") as run_id:
            resp = client.chat.completions.create(
                model=OLLAMA_MODEL,
                messages=[
                    {"role": "system", "content": "You are a concise support agent."},
                    {"role": "user", "content": question},
                ],
                temperature=0.3,
            )
            _ = (resp.choices[0].message.content or "").strip()

            quality = round(random.uniform(0.7, 0.98), 2)
            rl.score("resolution_quality", quality, label="judged", source="llm")

            resolved = quality > 0.75
            rl.outcome(
                "ticket_resolved",
                success=resolved,
                end_user_id=user_id,
                value_usd=round(random.uniform(6, 18), 2) if resolved else None,
                labels={"channel": random.choice(["email", "chat", "in-app"])},
            )
            print(
                f"  [run {run_id[:8]}] {user_id}  quality={quality}  "
                f"resolved={'yes' if resolved else 'no'}"
            )

    rl.shutdown()
    print(f"\nDone. See {dashboard_url()}/outcomes and {dashboard_url()}/evaluation.")


if __name__ == "__main__":
    main()
