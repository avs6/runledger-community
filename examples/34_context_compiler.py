"""
Example 34 — Context Compiler

Shrinks an oversized `messages` array before it reaches the model, in five fail-open stages:
dedup → tool-output compression → rerank+prune → conversation compaction → token budget.

This example calls the compiler service directly so you can see the `token_report`
(before / after / saved, per stage). In production you enable it on a gateway route
(context_compiler_enabled, or the dashboard "Compiler ON/OFF" badge) or per request
(`"context_compiler": true` in the gateway body).

Prerequisites
─────────────
  • The optimization services are up (reranker + context-compiler):
        docker compose up -d
  • A local LLM on the host (Ollama) for the compaction stage — set OLLAMA_BASE_URL if needed.

Install
───────
    pip install httpx python-dotenv

Run it
──────
    python 34_context_compiler.py

Key .env variables:
    CONTEXT_COMPILER_URL  — http://localhost:8207  (default)
"""

from __future__ import annotations

import json
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

COMPILER_URL = os.getenv("CONTEXT_COMPILER_URL", "http://localhost:8207")


def sep(title: str) -> None:
    print(f"\n{'─' * 60}\n  {title}\n{'─' * 60}")


# A deliberately bloated request: a duplicated context block, a verbose tool output,
# a mix of relevant and irrelevant RAG paragraphs, and the real question at the end.
RAG = (
    "The parental leave policy grants 16 weeks of paid leave to all full-time employees.\n\n"
    "The office kitchen is restocked every Tuesday and Friday morning.\n\n"
    "Parental leave may be taken continuously or split into two blocks within the first year.\n\n"
    "The quarterly all-hands is held on the last Thursday of the quarter.\n\n"
    "Reimbursement for home-office equipment is capped at $500 per calendar year.\n\n"
    "Employees on parental leave keep full health benefits during the leave period.\n\n"
)
TOOL_OUTPUT = "\n".join(["INFO heartbeat ok"] * 200) + "\nERROR disk usage 94% on /var\n" + "\n".join(
    ["INFO heartbeat ok"] * 200
)

messages = [
    {"role": "system", "content": "You are a concise HR assistant.\n\n" + RAG},
    {"role": "system", "content": "You are a concise HR assistant.\n\n" + RAG},  # duplicate → dedup
    {"role": "tool", "content": TOOL_OUTPUT},  # verbose → tool-output compression
    {"role": "user", "content": "How much parental leave do employees get, and do benefits continue?"},
]

config = {
    "reranker_model": "flashrank",
    "token_threshold": 0,   # 0 = always engage
    "token_budget": 400,    # low, so rerank + compaction actively prune
    "stages": {"dedup": True, "tool_output": True, "rerank": True, "compaction": True},
}

sep("POST /compile")
with httpx.Client(timeout=60.0) as client:
    resp = client.post(f"{COMPILER_URL}/compile", json={"messages": messages, "config": config})

if resp.status_code != 200:
    print(f"  ERROR {resp.status_code}: {resp.text[:200]}")
    raise SystemExit(1)

data = resp.json()
tr = data["token_report"]
print(f"  Before:  {tr['before']} tokens")
print(f"  After:   {tr['after']} tokens")
print(f"  Saved:   {tr['saved']} tokens  ({round(100 * tr['saved'] / max(1, tr['before']))}%)")
print(f"  Per stage: {json.dumps(tr['per_stage'])}")
if data.get("dropped"):
    print("  What changed:")
    for d in data["dropped"]:
        print(f"    • {d}")
print(f"  Degraded (a stage was skipped on error): {data.get('degraded')}")

sep("Enable it on a gateway route")
print("  Persistent:  POST /gateway/routes  with  \"context_compiler_enabled\": true")
print("               (or toggle the 'Compiler ON/OFF' badge on the dashboard Gateway page)")
print("  Ad-hoc:      add  \"context_compiler\": true  to a /gateway/chat/completions body")

print("\n✓ Example 34 complete.\n")
