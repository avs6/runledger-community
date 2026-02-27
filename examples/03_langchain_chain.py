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
    pip install langchain-openai

Run it
──────
    export OPENAI_API_KEY=sk-...

    # Against a local RunLedger stack (docker compose up)
    export RUNLEDGER_API_KEY=rl_dev_...   # printed in: docker compose logs api
    python examples/03_langchain_chain.py

    # Or set local=True in the script below to print events to stdout
"""

from __future__ import annotations

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from runledger_sdk import RunLedger

rl = RunLedger(local=True)  # set local=False + RUNLEDGER_API_KEY for live API

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
