"""
Example 3 — LangChain chain with RunLedgerCallbackHandler.

What this demonstrates
──────────────────────
- rl.callback_handler() wraps any LangChain Runnable
- Full span DAG: chain → llm spans with parent-child linking
- Works with prompt | llm | parser chains
- run_start / run_end events fire automatically at chain boundaries

Install the SDK (not on PyPI yet — install from source)
────────────────────────────────────────────────────────
Option A — local path (recommended if you have the repo):
    pip install -e "/path/to/runledger/packages/sdk[langchain]"

Option B — directly from GitHub (no clone needed):
    pip install "runledger-sdk[langchain] @ git+https://github.com/avs6/runledger.git#subdirectory=packages/sdk"

Also install:
    pip install langchain-openai python-dotenv

Run it
──────
    # Copy .env.example → .env and fill in your values, then:
    python 03_langchain_chain.py

Key .env variables used here:
    RUNLEDGER_API_KEY    — your workspace API key
    RUNLEDGER_BASE_URL   — http://localhost:8000  (local Docker stack)
    RUNLEDGER_LOCAL      — set "true" to print events instead of sending to the API
    OPENAI_API_KEY       — your OpenAI key
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from runledger_sdk import RunLedger

load_dotenv()

LOCAL_MODE = os.getenv("RUNLEDGER_LOCAL", "false").lower() in ("1", "true", "yes")

rl = RunLedger(local=LOCAL_MODE)

# ── Build a LangChain chain ───────────────────────────────────────────────────
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "You are an expert at explaining technical concepts simply."),
        ("human", "Explain {topic} in one sentence."),
    ]
)

chain = prompt | llm | StrOutputParser()

# ── Get the callback handler ──────────────────────────────────────────────────
#
# Pass this to chain.invoke() / chain.stream() / chain.ainvoke() etc.
handler = rl.callback_handler()


def explain(topic: str, user_id: str = "anon") -> str:
    with rl.context(end_user_id=user_id, feature_tag="explain-chain") as run_id:
        print(f"[RunLedger] run_id={run_id}")

        result = chain.invoke(
            {"topic": topic},
            config={"callbacks": [handler]},
        )
        return result


if __name__ == "__main__":
    topics = ["recursive functions", "gradient descent", "idempotency"]
    for topic in topics:
        explanation = explain(topic, user_id="user-carol")
        print(f"{topic!r}: {explanation}\n")

    rl.shutdown()
