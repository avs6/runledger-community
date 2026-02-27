"""
Example 2 — OpenAI multi-turn conversation with session tracking.

What this demonstrates
──────────────────────
- session_id groups multiple runs from the same user conversation
- Nested contexts: outer sets the user, inner overrides feature_tag per step
- Accessing run_id mid-flight for your own logging
- Proper shutdown after a chat loop

Run it
──────
    export RUNLEDGER_API_KEY=rl_live_...
    export OPENAI_API_KEY=sk-...
    uv run python examples/02_openai_multi_turn.py
"""

from __future__ import annotations

import openai

from runledger_sdk import RunLedger

rl = RunLedger(local=True)  # set local=False + RUNLEDGER_API_KEY for live API
rl.instrument()

client = openai.OpenAI()

SYSTEM_PROMPT = "You are a helpful coding assistant. Keep answers short."


def chat_session(user_id: str, session_id: str, turns: list[str]) -> None:
    """Run a multi-turn chat session, tracking each turn separately."""
    history: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]

    print(f"\n── Session {session_id} ──────────────────")

    for i, user_message in enumerate(turns, start=1):
        history.append({"role": "user", "content": user_message})

        # Each turn gets its own run_id (nested feature_tag for drill-down)
        with rl.context(
            end_user_id=user_id,
            session_id=session_id,
            feature_tag=f"chat-turn-{i}",
        ) as run_id:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=history,  # type: ignore[arg-type]
            )
            assistant_reply = response.choices[0].message.content or ""
            history.append({"role": "assistant", "content": assistant_reply})

        print(f"[Turn {i}] run_id={run_id[:8]}…")
        print(f"  User: {user_message}")
        print(f"  Bot:  {assistant_reply}\n")


if __name__ == "__main__":
    chat_session(
        user_id="user-bob",
        session_id="sess-abc123",
        turns=[
            "What is a Python list comprehension?",
            "Give me one example.",
            "How is it different from a generator expression?",
        ],
    )
    rl.shutdown()
