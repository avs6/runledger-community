"""
Lab 05 — Business outcomes + evaluation scores.

WHAT THIS IS
────────────
Tokens and latency tell you what an agent *cost*. Outcomes and scores tell you
what it was *worth*. Here the **AI Support Team** links each run to:
  • an eval score  — quality of the answer (0–1), and
  • a business outcome — e.g. a resolved ticket, optionally with a dollar value.
That's what powers RunLedger's cost-per-outcome / ROI analytics.

Both `rl.score(...)` and `rl.outcome(...)` are posted synchronously and attach to
the current run's context automatically.

PREREQUISITES
─────────────
  • AI Support Team workspace key in agents/.env
  • pip install -r requirements.txt

RUN
───
    python lab_05_outcomes_scores.py

THEN VERIFY
───────────
  • dashboard → Evaluation : the "resolution_quality" scores show up.
  • dashboard → Outcomes   : "ticket_resolved" outcomes with $ value; ROI /
    cost-per-outcome becomes meaningful once pricing is uploaded and cost enriches.
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
    banner("Lab 05 · Outcomes + scores · AI Support Team")
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

            # A quality score for this answer (an LLM judge or human reviewer in real life).
            quality = round(random.uniform(0.7, 0.98), 2)
            rl.score("resolution_quality", quality, label="judged", source="llm")

            # A business outcome: was the ticket resolved, and what was it worth?
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
    print(f"\n✓ Done. See {dashboard_url()}/outcomes and {dashboard_url()}/evaluation.")


if __name__ == "__main__":
    main()
