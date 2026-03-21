"""
Example 4 — LangGraph ReAct-style agent with full DAG instrumentation
        and runtime Tool Registry enforcement.

What this demonstrates
──────────────────────
- instrument_graph() wraps every node automatically via LangChain callbacks
- Span DAG follows the actual execution path (not just the graph definition)
- Tool calls become TOOL spans nested inside the agent run
- tool_enforcement=True: SDK checks workspace Tool Registry *before* each tool
  executes — blocked tools raise ToolBlockedError instead of running
- Handles loops: the agent calls tools, processes results, loops back

Agent description
─────────────────
A simple research agent with three tools:
  - search(query)       → returns a canned result (no real search needed)
  - calculator(expr)    → evaluates a Python math expression
  - send_email(to, msg) → BLOCKED by Tool Registry (policy=block)

Tool Registry setup (run once via API or dashboard)
────────────────────────────────────────────────────
    curl -X POST $RUNLEDGER_BASE_URL/tools/registry \\
         -H "Authorization: Bearer $RUNLEDGER_API_KEY" \\
         -H "Content-Type: application/json" \\
         -d '{"tool_name": "search", "policy": "allow", "runtime_enforcement": true}'

    curl -X POST $RUNLEDGER_BASE_URL/tools/registry \\
         -H "Authorization: Bearer $RUNLEDGER_API_KEY" \\
         -H "Content-Type: application/json" \\
         -d '{"tool_name": "calculator", "policy": "audit", "runtime_enforcement": true}'

    curl -X POST $RUNLEDGER_BASE_URL/tools/registry \\
         -H "Authorization: Bearer $RUNLEDGER_API_KEY" \\
         -H "Content-Type: application/json" \\
         -d '{"tool_name": "send_email", "policy": "block", "runtime_enforcement": true}'

Install the SDK
────────────────────────────────────────────────────
    pip install -e "/path/to/runledger/packages/sdk[langgraph]"
    pip install langchain-openai langgraph python-dotenv

Run it
──────
    python 04_langgraph_agent.py

Key .env variables:
    RUNLEDGER_API_KEY    — your workspace API key (tool registry + runs scoped to this workspace)
    RUNLEDGER_BASE_URL   — http://localhost:8000
    RUNLEDGER_LOCAL      — set "true" to print events instead of sending
    OPENAI_API_KEY       — your OpenAI key

Note: the Tool Registry curl commands above use RUNLEDGER_API_KEY — they register
tools in the workspace the key belongs to, not globally. Each workspace has its own
tool policy configuration.
"""

from __future__ import annotations

import math
import os
from typing import Annotated, Any, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from runledger_sdk import RunLedger
from runledger_sdk.exceptions import ToolBlockedError
from runledger_sdk.langgraph import instrument_graph

load_dotenv()

LOCAL_MODE = os.getenv("RUNLEDGER_LOCAL", "false").lower() in ("1", "true", "yes")

# tool_enforcement=True enables runtime Tool Registry checks before every tool call.
# The SDK will call GET /tools/check/{tool_name} before execution — blocked tools
# raise ToolBlockedError instead of running.
rl = RunLedger(local=LOCAL_MODE, tool_enforcement=True)

# ── Tools ──────────────────────────────────────────────────────────────────────


@tool
def search(query: str) -> str:
    """Search for information. Returns a brief answer."""
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


@tool
def send_email(to: str, message: str) -> str:
    """Send an email. (This tool is blocked by workspace policy.)"""
    return f"Email sent to {to}: {message}"


TOOLS = [search, calculator, send_email]

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
    """
    Execute any tool calls requested by the LLM.

    The RunLedger callback's on_tool_start hook fires before each tool
    and raises ToolBlockedError for blocked tools. We catch it here and
    return a structured error message so the agent can recover gracefully.
    """
    last = state["messages"][-1]
    assert isinstance(last, AIMessage)

    results: list[ToolMessage] = []
    for tool_call in last.tool_calls:
        fn = tool_map.get(tool_call["name"])
        if fn:
            try:
                output = fn.invoke(tool_call["args"])
                results.append(
                    ToolMessage(content=str(output), tool_call_id=tool_call["id"])
                )
            except ToolBlockedError as e:
                # Tool was blocked by workspace policy — tell the agent
                print(f"\n[ToolBlockedError] {e}")
                results.append(
                    ToolMessage(
                        content=f"Tool '{e.tool_name}' is blocked by workspace policy and cannot be used.",
                        tool_call_id=tool_call["id"],
                    )
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
# on_tool_start in the callback checks the Tool Registry before each tool runs
instrumented_graph = instrument_graph(graph, rl._get_sync_transport())


# ── Run the agent ──────────────────────────────────────────────────────────────


def run_agent(question: str, user_id: str = "anon") -> str:
    with rl.context(
        end_user_id=user_id,
        feature_tag="research-agent",
        deployment_version="v1.0",
    ) as run_id:
        print(f"\n[RunLedger] run_id={run_id}")
        print(f"[Question]  {question}\n")

        result = instrumented_graph.invoke(
            {"messages": [HumanMessage(content=question)]}
        )

        final_message = result["messages"][-1]
        return final_message.content


if __name__ == "__main__":
    questions = [
        # search tool: policy=allow → runs fine
        "How tall is the Eiffel Tower in feet? (1 metre = 3.28084 feet)",
        # calculator tool: policy=audit → runs but logged as security event
        "What is 2 to the power of 15?",
        # send_email tool: policy=block → ToolBlockedError, agent recovers gracefully
        "Send an email to ceo@example.com saying 'hello from the agent'",
    ]

    for q in questions:
        answer = run_agent(q, user_id="user-dave")
        print(f"Answer: {answer}\n{'─' * 60}")

    rl.shutdown()
