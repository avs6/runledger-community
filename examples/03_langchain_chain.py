"""
Example 3 — LangChain chain with RunLedgerCallbackHandler.

What this demonstrates
──────────────────────
- rl.callback_handler() wraps any LangChain Runnable
- Full span DAG: chain → llm spans with parent-child linking
- Works with prompt | llm | parser chains
- run_start / run_end events fire automatically at chain boundaries

Dependencies
────────────
    pip install runledger-sdk[langchain] langchain-openai

Run it
──────
    export RUNLEDGER_API_KEY=rl_live_...
    export OPENAI_API_KEY=sk-...
    uv run python examples/03_langchain_chain.py
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
