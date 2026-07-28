"""
Example 38 — Dynamic Tool Filtering + Skill Injection

Two Context Compiler stages that give the model only what's relevant to *this* request:
  • Tool filtering — keep only the tools relevant to the question (fewer tool-schema tokens).
  • Skill injection — inject the body of matched skills from the registry (inject-body-on-match).

Prerequisites
─────────────
  docker compose up -d

Install
───────
    pip install httpx python-dotenv

Run it
──────
    python 38_tool_filtering_skills.py
"""

from __future__ import annotations

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

COMPILER_URL = os.getenv("CONTEXT_COMPILER_URL", "http://localhost:8207")
SKILL_URL = os.getenv("SKILL_URL", "http://localhost:8213")
WS = "demo-p6"


def tool(name: str, desc: str) -> dict:
    return {"type": "function", "function": {"name": name, "description": desc, "parameters": {}}}


TOOLS = [
    tool("salesforce_search", "Search Salesforce opportunities and accounts"),
    tool("salesforce_opportunity", "Get a Salesforce opportunity by id"),
    tool("jira_create_issue", "Create a Jira issue"),
    tool("slack_send", "Send a Slack message"),
    tool("github_pr", "Open a GitHub pull request"),
    tool("datadog_query", "Query Datadog metrics"),
    tool("aws_ec2_list", "List AWS EC2 instances"),
    tool("k8s_scale", "Scale a Kubernetes deployment"),
    tool("stripe_refund", "Issue a Stripe refund"),
    tool("google_calendar", "Create a calendar event"),
    tool("notion_page", "Create a Notion page"),
    tool("pagerduty_ack", "Acknowledge a PagerDuty incident"),
    tool("salesforce_account", "Get a Salesforce account by id"),
    tool("zendesk_ticket", "Create a Zendesk ticket"),
]


def sep(t: str) -> None:
    print(f"\n{'─' * 60}\n  {t}\n{'─' * 60}")


with httpx.Client(timeout=120.0) as c:
    sep(f"Tool filtering — {len(TOOLS)} tools → relevant subset")
    r = c.post(f"{COMPILER_URL}/select-tools",
               json={"query": "Check my Salesforce opportunity for Acme Corp", "tools": TOOLS})
    d = r.json()
    kept = [t["function"]["name"] for t in d.get("tools", [])]
    print(f"  kept {len(kept)} tools: {kept}")
    print(f"  saved ~{d.get('saved_tokens')} tokens of tool schema")

    sep("Skill injection (inject-body-on-match)")
    c.post(f"{SKILL_URL}/skills", json={"workspace": WS, "name": "refund-policy",
           "description": "How to process a customer refund and the approval thresholds",
           "content": "Refunds under $100 are auto-approved. $100-1000 need manager sign-off. "
                      "Over $1000 need finance approval. Always log the reason.", "version": 1})
    msgs = [{"role": "user", "content": "A customer wants a $250 refund — what's the process?"}]
    r = c.post(f"{COMPILER_URL}/compile", json={"messages": msgs, "workspace": WS,
               "config": {"token_threshold": 0, "stages": {"skills": True, "rerank": False,
                          "tool_output": False, "dedup": False, "compaction": False}}})
    d = r.json()
    print("  what changed:", d.get("dropped"))
    injected = [m for m in d["messages"] if m["role"] == "system" and "Relevant skill" in m.get("content", "")]
    if injected:
        print("  injected skill block:\n   ", injected[0]["content"][:160], "…")

print("\n✓ Example 38 complete.\n")
