"""
Example 20 — Runtime Tool Registry enforcement with Ollama (local LLM).

What this demonstrates
──────────────────────
- Tool Registry as a RUNTIME FIREWALL — not just post-hoc auditing
- Ollama running locally with function/tool calling (llama3.1, qwen2.5, mistral-nemo)
- Three enforcement tiers shown in one script:
    allow  → tool runs, no log entry
    audit  → tool runs, security event written to RunLedger
    block  → ToolBlockedError raised BEFORE the tool executes, run=failed
- SDK-side in-memory cache (60 s TTL) — only 1 HTTP call per tool per minute
- Fail-open: if RunLedger API is unreachable, all tools run (never blocks user)
- Full run/span telemetry captured for every agent turn

Architecture
────────────
Agent asks Ollama → Ollama returns tool_calls → SDK intercepts response →
  checks /tools/check/{tool_name} (Redis-cached, <5 ms) →
    allow/audit → tool runs → result returned to agent
    block       → ToolBlockedError raised → agent receives structured error

Prerequisites
─────────────
1. Ollama running locally:
       ollama serve
2. A model with tool support pulled:
       ollama pull llama3.1          # best tool support, ~4 GB
       ollama pull qwen2.5:7b        # good alternative, ~5 GB
       ollama pull mistral-nemo      # compact option, ~7 GB
3. RunLedger stack running:
       docker compose up             # from repo root
4. API key in .env (RUNLEDGER_API_KEY)

Install
───────
    pip install -e "/path/to/runledger/packages/sdk[openai]"
    pip install openai python-dotenv

Setup: register tools (run once)
─────────────────────────────────
The script auto-registers tool policies on startup if SETUP_REGISTRY=true.
Or do it manually:

    # allow — web_search runs silently
    curl -X POST $RUNLEDGER_BASE_URL/tools/registry \\
         -H "Authorization: Bearer $RUNLEDGER_API_KEY" \\
         -H "Content-Type: application/json" \\
         -d '{"tool_name":"web_search","policy":"allow","runtime_enforcement":true,"description":"Public web search"}'

    # audit — read_file runs but is logged
    curl -X POST $RUNLEDGER_BASE_URL/tools/registry \\
         -H "Authorization: Bearer $RUNLEDGER_API_KEY" \\
         -H "Content-Type: application/json" \\
         -d '{"tool_name":"read_file","policy":"audit","runtime_enforcement":true,"description":"Read a file from disk"}'

    # block — delete_record is blocked at runtime
    curl -X POST $RUNLEDGER_BASE_URL/tools/registry \\
         -H "Authorization: Bearer $RUNLEDGER_API_KEY" \\
         -H "Content-Type: application/json" \\
         -d '{"tool_name":"delete_record","policy":"block","runtime_enforcement":true,"description":"Delete a database record"}'

    # block — send_email is blocked at runtime
    curl -X POST $RUNLEDGER_BASE_URL/tools/registry \\
         -H "Authorization: Bearer $RUNLEDGER_API_KEY" \\
         -H "Content-Type: application/json" \\
         -d '{"tool_name":"send_email","policy":"block","runtime_enforcement":true,"description":"Send an email"}'

Run it
──────
    python 20_tool_registry_ollama.py

    # Auto-register tool policies then run:
    SETUP_REGISTRY=true python 20_tool_registry_ollama.py

Key .env variables:
    RUNLEDGER_API_KEY    — your workspace API key
    RUNLEDGER_BASE_URL   — http://localhost:8000
    OLLAMA_BASE_URL      — http://localhost:11434/v1  (default)
    OLLAMA_MODEL         — llama3.1  (default; needs tool-calling support)
    SETUP_REGISTRY       — set "true" to auto-register tool policies
    RUNLEDGER_LOCAL      — set "true" to print events only (no running API)
"""

from __future__ import annotations

import json
import os

import httpx
import openai
from dotenv import load_dotenv
from runledger_sdk import RunLedger
from runledger_sdk.exceptions import ToolBlockedError

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")  # must support tool calling
RUNLEDGER_BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
RUNLEDGER_API_KEY = os.getenv("RUNLEDGER_API_KEY", "")
LOCAL_MODE = os.getenv("RUNLEDGER_LOCAL", "false").lower() in ("1", "true", "yes")
SETUP_REGISTRY = os.getenv("SETUP_REGISTRY", "false").lower() in ("1", "true", "yes")

print(f"Ollama model    : {MODEL}")
print(f"Ollama URL      : {OLLAMA_BASE_URL}")
print(f"RunLedger URL   : {RUNLEDGER_BASE_URL}")
print(f"Local mode      : {LOCAL_MODE}")

# ── RunLedger client (tool_enforcement=True is the key flag) ──────────────────
#
# tool_enforcement=True tells the SDK to call GET /tools/check/{tool_name}
# before every tool execution. Results are cached for 60 s per tool name.
rl = RunLedger(
    local=LOCAL_MODE,
    tool_enforcement=True,   # ← runtime firewall enabled
)
rl.instrument()  # monkey-patches openai.OpenAI

# ── OpenAI client pointing at Ollama ──────────────────────────────────────────
client = openai.OpenAI(
    base_url=OLLAMA_BASE_URL,
    api_key="ollama",  # Ollama ignores this but the client requires it
)

# ── Tool definitions (OpenAI function-calling format) ─────────────────────────

TOOL_DEFS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for information. Policy: ALLOW.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read contents of a local file. Policy: AUDIT (runs but logged).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to read"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_record",
            "description": "Delete a record from the database. Policy: BLOCK (will never execute).",
            "parameters": {
                "type": "object",
                "properties": {
                    "record_id": {"type": "string"},
                },
                "required": ["record_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Send an email. Policy: BLOCK (will never execute).",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "message": {"type": "string"},
                },
                "required": ["to", "message"],
            },
        },
    },
]


# ── Tool implementations ───────────────────────────────────────────────────────
# These only run if the Tool Registry allows it.


def web_search(query: str) -> str:
    """Canned search results — swap for real search in production."""
    database = {
        "llm": "A Large Language Model (LLM) is a neural network trained on vast text data.",
        "ollama": "Ollama lets you run open-source LLMs locally on your machine.",
        "runledger": "RunLedger is a FinOps control plane for AI agents.",
        "tool registry": "A tool registry controls which tools agents are allowed to call.",
    }
    ql = query.lower()
    for key, value in database.items():
        if key in ql:
            return value
    return f"Search result for '{query}': No specific result found in local database."


def read_file(path: str) -> str:
    """Read a file — policy=audit means this runs but is logged as a security event."""
    try:
        with open(path) as f:
            return f.read(500)  # truncate to 500 chars for demo
    except FileNotFoundError:
        return f"[demo] File '{path}' not found — returning placeholder content."
    except Exception as e:
        return f"Error reading file: {e}"


def delete_record(record_id: str) -> str:
    """This implementation never runs because the tool is blocked at the SDK level."""
    return f"Deleted record {record_id}"  # unreachable


def send_email(to: str, message: str) -> str:
    """This implementation never runs because the tool is blocked at the SDK level."""
    return f"Email sent to {to}"  # unreachable


TOOL_FN_MAP = {
    "web_search": web_search,
    "read_file": read_file,
    "delete_record": delete_record,
    "send_email": send_email,
}


# ── Optional: auto-register tool policies ─────────────────────────────────────


def setup_tool_registry() -> None:
    """Register tool policies via the RunLedger API (idempotent — upserts)."""
    if LOCAL_MODE or not RUNLEDGER_API_KEY:
        print("[setup] Skipping registry setup (local mode or no API key)")
        return

    policies = [
        {"tool_name": "web_search", "policy": "allow", "runtime_enforcement": True,
         "description": "Public web search — allowed, no log"},
        {"tool_name": "read_file", "policy": "audit", "runtime_enforcement": True,
         "description": "Read local files — allowed but every call is logged"},
        {"tool_name": "delete_record", "policy": "block", "runtime_enforcement": True,
         "description": "Delete DB records — BLOCKED, raises ToolBlockedError"},
        {"tool_name": "send_email", "policy": "block", "runtime_enforcement": True,
         "description": "Send emails — BLOCKED, raises ToolBlockedError"},
    ]

    headers = {
        "Authorization": f"Bearer {RUNLEDGER_API_KEY}",
        "Content-Type": "application/json",
    }

    print("\n[setup] Registering tool policies…")
    for policy in policies:
        try:
            r = httpx.post(
                f"{RUNLEDGER_BASE_URL}/tools/registry",
                json=policy,
                headers=headers,
                timeout=5.0,
            )
            status = "✓" if r.status_code in (200, 201) else f"✗ ({r.status_code})"
            print(f"  {status}  {policy['tool_name']:20s} → {policy['policy']}")
        except Exception as e:
            print(f"  ✗  {policy['tool_name']:20s} → error: {e}")
    print()


# ── Agent loop ────────────────────────────────────────────────────────────────


def dispatch_tool(tool_call: dict) -> str:
    """
    Execute a tool call, handling ToolBlockedError gracefully.

    When the SDK raises ToolBlockedError (policy=block + runtime_enforcement=True),
    we return a structured error message so the agent can tell the user what happened.
    """
    name = tool_call["function"]["name"]
    try:
        args = json.loads(tool_call["function"]["arguments"])
    except json.JSONDecodeError:
        args = {}

    fn = TOOL_FN_MAP.get(name)
    if not fn:
        return f"Unknown tool: {name}"

    try:
        return fn(**args)
    except ToolBlockedError as e:
        # The SDK blocked this tool *before* our function ran
        return (
            f"⛔ Tool '{e.tool_name}' is blocked by workspace policy. "
            "This action is not permitted."
        )


def run_agent(question: str, user_id: str = "demo-user", max_turns: int = 5) -> str:
    """
    Simple agentic loop: LLM → tool calls → results → LLM → ...

    The RunLedger OpenAI wrapper intercepts the response after the LLM call.
    If any tool_call in the response is blocked (policy=block, runtime_enforcement=True),
    ToolBlockedError is raised *before* we enter the dispatch loop.

    In that case we catch it here, convert it to a tool result message, and let
    the model continue gracefully.
    """
    messages: list[dict] = [
        {
            "role": "system",
            "content": (
                "You are a helpful assistant with access to tools. "
                "Use tools when needed. If a tool is blocked by policy, "
                "explain this to the user and suggest alternatives."
            ),
        },
        {"role": "user", "content": question},
    ]

    with rl.context(
        end_user_id=user_id,
        feature_tag="tool-registry-demo",
        deployment_version="v1.0",
    ) as run_id:
        print(f"\n[RunLedger] run_id={run_id}")
        print(f"[Question]  {question}")
        print(f"[Model]     {MODEL}  ({OLLAMA_BASE_URL})\n")

        for turn in range(max_turns):
            try:
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=messages,  # type: ignore[arg-type]
                    tools=TOOL_DEFS,    # type: ignore[arg-type]
                    tool_choice="auto",
                    temperature=0,
                )
            except ToolBlockedError as e:
                # The SDK intercepted a blocked tool_call in the LLM response
                # before returning the response object. We add a synthetic
                # assistant + tool message pair so the model can recover.
                print(f"[blocked-in-response] {e}")
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "blocked_call",
                            "type": "function",
                            "function": {"name": e.tool_name, "arguments": "{}"},
                        }
                    ],
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": "blocked_call",
                    "content": (
                        f"Tool '{e.tool_name}' is blocked by workspace policy. "
                        "Cannot execute this action."
                    ),
                })
                continue

            choice = response.choices[0]
            finish_reason = choice.finish_reason
            message = choice.message

            if finish_reason == "stop" or not getattr(message, "tool_calls", None):
                # Agent is done
                return message.content or ""

            # Process tool calls
            tool_results = []
            for tc in message.tool_calls:
                print(f"  → tool call: {tc.function.name}({tc.function.arguments[:80]})")
                result = dispatch_tool({
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                })
                print(f"  ← result:    {result[:100]}")
                tool_results.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

            # Add assistant message + tool results to history
            messages.append(message)  # type: ignore[arg-type]
            messages.extend(tool_results)

        return "[max turns reached]"


# ── Demo scenarios ─────────────────────────────────────────────────────────────


SCENARIOS = [
    {
        "user_id": "user-alice",
        "question": "What is Ollama? Search for it.",
        "expected": "web_search runs (policy=allow) — no security event",
    },
    {
        "user_id": "user-bob",
        "question": "Read the contents of /etc/hostname for me.",
        "expected": "read_file runs (policy=audit) — security event logged in RunLedger",
    },
    {
        "user_id": "user-charlie",
        "question": "Delete record ID 'user-42' from the database.",
        "expected": "delete_record BLOCKED (policy=block) — ToolBlockedError, agent recovers",
    },
    {
        "user_id": "user-dana",
        "question": "Send an email to admin@example.com saying the build passed.",
        "expected": "send_email BLOCKED (policy=block) — ToolBlockedError, agent recovers",
    },
]


if __name__ == "__main__":
    if SETUP_REGISTRY:
        setup_tool_registry()

    print("=" * 70)
    print("  RunLedger Tool Registry — Runtime Enforcement Demo (Ollama)")
    print("=" * 70)
    print()
    print("Policy matrix:")
    print("  web_search    → allow  (runs silently)")
    print("  read_file     → audit  (runs + security event logged)")
    print("  delete_record → block  (ToolBlockedError before execution)")
    print("  send_email    → block  (ToolBlockedError before execution)")
    print()

    for i, scenario in enumerate(SCENARIOS, 1):
        print(f"{'─' * 70}")
        print(f"Scenario {i}: {scenario['expected']}")
        try:
            answer = run_agent(
                question=scenario["question"],
                user_id=scenario["user_id"],
            )
            print(f"\nAnswer: {answer}")
        except Exception as e:
            print(f"\nUnhandled exception: {type(e).__name__}: {e}")
        print()

    print("─" * 70)
    print("\nDone. Check RunLedger dashboard:")
    print("  • Monitoring → Security Events — blocked calls + audit events")
    print("  • Runs — all 4 runs with tool spans and status")
    print()

    rl.shutdown()
