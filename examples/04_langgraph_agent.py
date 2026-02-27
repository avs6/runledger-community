"""
Example 4 — LangGraph ReAct-style agent with full DAG instrumentation.

What this demonstrates
──────────────────────
- instrument_graph() wraps every node automatically via LangChain callbacks
- Span DAG follows the actual execution path (not just the graph definition)
- Tool calls become TOOL spans nested inside the agent run
- Handles loops: the agent calls tools, processes results, loops back

Agent description
─────────────────
A simple research agent with two tools:
  - search(query)     → returns a canned result (no real search needed)
  - calculator(expr)  → evaluates a Python math expression

Install the SDK (not on PyPI yet — install from source)
────────────────────────────────────────────────────────
Option A — local path (recommended if you have the repo):
    pip install -e "/path/to/runledger/packages/sdk[langgraph]"

Option B — directly from GitHub (no clone needed):
    pip install "runledger-sdk[langgraph] @ git+https://github.com/avs6/runledger.git#subdirectory=packages/sdk"

Also install:
    pip install langchain-openai langgraph

Run it
──────
    export OPENAI_API_KEY=sk-...

    # Against a local RunLedger stack (docker compose up)
    export RUNLEDGER_API_KEY=rl_dev_...   # printed in: docker compose logs api
    python examples/04_langgraph_agent.py

    # Or set local=True in the script below to print events to stdout
"""

from __future__ import annotations

import json
import math
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from runledger_sdk import RunLedger
from runledger_sdk.langgraph import instrument_graph

rl = RunLedger(local=True)  # set local=False + RUNLEDGER_API_KEY for live API

# ── Tools ──────────────────────────────────────────────────────────────────────


@tool
def search(query: str) -> str:
    """Search for information. Returns a brief answer."""
    # Canned responses — swap out for real search in production
    database = {
        "eiffel tower height": "The Eiffel Tower is 330 metres tall.",
        "python creator": "Python was created by Guido van Rossum.",
        "speed of light": "The speed of light is 299,792,458 metres per second.",
    }
    query_lower = query.lower()
    for key, value in database.items():
        if any(word in query_lower for word in key.split()):
            return value
    return f"No result found for: {query}"


@tool
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression. Example: '2 ** 10' or 'math.sqrt(144)'."""
    try:
        result = eval(expression, {"__builtins__": {}, "math": math})  # noqa: S307
        return str(result)
    except Exception as exc:
        return f"Error: {exc}"


TOOLS = [search, calculator]

# ── Agent graph ────────────────────────────────────────────────────────────────


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
llm_with_tools = llm.bind_tools(TOOLS)

tool_map = {t.name: t for t in TOOLS}


def agent_node(state: AgentState) -> dict[str, Any]:
    """Call the LLM with the current message history."""
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}


def tool_node(state: AgentState) -> dict[str, Any]:
    """Execute any tool calls requested by the LLM."""
    last = state["messages"][-1]
    assert isinstance(last, AIMessage)

    results: list[ToolMessage] = []
    for tool_call in last.tool_calls:
        fn = tool_map.get(tool_call["name"])
        if fn:
            output = fn.invoke(tool_call["args"])
            results.append(
                ToolMessage(content=str(output), tool_call_id=tool_call["id"])
            )
        else:
            results.append(
                ToolMessage(content="Tool not found.", tool_call_id=tool_call["id"])
            )
    return {"messages": results}


def should_continue(state: AgentState) -> str:
    """Route: call tools if the LLM asked for them, otherwise finish."""
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        return "tools"
    return END


# ── Build + instrument graph ───────────────────────────────────────────────────
builder: StateGraph = StateGraph(AgentState)
builder.add_node("agent", agent_node)
builder.add_node("tools", tool_node)
builder.set_entry_point("agent")
builder.add_conditional_edges("agent", should_continue)
builder.add_edge("tools", "agent")

graph = builder.compile()

# Attach RunLedger instrumentation — every node fires span_start/span_end
instrumented_graph = instrument_graph(graph, rl._get_sync_transport())


# ── Run the agent ──────────────────────────────────────────────────────────────


def run_agent(question: str, user_id: str = "anon") -> str:
    with rl.context(
        end_user_id=user_id,
        feature_tag="research-agent",
        deployment_version="v1.0",
    ) as run_id:
        print(f"\n[RunLedger] run_id={run_id}")
        print(f"[Question] {question}\n")

        result = instrumented_graph.invoke(
            {"messages": [HumanMessage(content=question)]}
        )

        final_message = result["messages"][-1]
        return final_message.content


if __name__ == "__main__":
    questions = [
        "How tall is the Eiffel Tower in feet? (1 metre = 3.28084 feet)",
        "What is 2 to the power of 15?",
    ]

    for q in questions:
        answer = run_agent(q, user_id="user-dave")
        print(f"Answer: {answer}\n{'─' * 60}")

    rl.shutdown()
