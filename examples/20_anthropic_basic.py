"""
Example 20 — Anthropic Claude instrumentation with RunLedger.

Requirements:
    pip install anthropic

Run:
    python examples/20_anthropic_basic.py
"""

import os

from dotenv import load_dotenv

load_dotenv("examples/.env")

from runledger_sdk import RunLedger  # noqa: E402

rl = RunLedger()
rl.instrument_anthropic()

import anthropic  # noqa: E402

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

with rl.context(end_user_id="user_42", feature_tag="anthropic-demo"):
    message = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=256,
        messages=[
            {"role": "user", "content": "What is the capital of France? Answer in one sentence."}
        ],
    )
    print("Response:", message.content[0].text)

rl.flush()
print("Run tracked in RunLedger")
