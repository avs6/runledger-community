"""
Lab 01 - Inline SDK instrumentation.

This is the code a developer in HomeLab / AgentTest would write. The RunLedger SDK
patches the OpenAI client so every model call is captured automatically.
"""

from __future__ import annotations

import openai
from _config import OLLAMA_BASE_URL, OLLAMA_MODEL, banner, dashboard_url, require_key
from runledger_sdk import RunLedger

FAQ = (
    "Refunds are processed within 5 business days. "
    "You can reset your password from the login page. "
    "Our support hours are 9am-6pm Eastern, Monday to Friday."
)

TICKETS = [
    ("cust_101", "How long do refunds take?"),
    ("cust_102", "I forgot my password, what do I do?"),
    ("cust_103", "Are you open on weekends?"),
]


def main() -> None:
    banner("Lab 01 - Inline SDK instrumentation - HomeLab / AgentTest")
    require_key()

    rl = RunLedger()
    rl.instrument()

    client = openai.OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")

    for user_id, question in TICKETS:
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
            rl.score("helpfulness", 0.9, label="good", source="human")

            print(f"\n[run {run_id[:8]}]  {user_id}")
            print(f"  Q: {question}")
            print(f"  A: {answer[:200]}")

    rl.shutdown()
    print(f"\nDone. Open {dashboard_url()}/runs and filter by feature 'support-chat'.")


if __name__ == "__main__":
    main()
