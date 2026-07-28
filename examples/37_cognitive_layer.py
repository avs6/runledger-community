"""
Example 37 — Cognitive Layer (memory · knowledge graph · skills)

RunLedger's shared cognitive layer: persistent memory (Letta-backed), a knowledge graph (Kùzu),
and a skill registry — all workspace-scoped and exposed over MCP so multiple clients share them.
This example calls each microservice directly.

Prerequisites
─────────────
  • docker compose up -d   (memory-svc needs Letta + runledger-memory-db; first memory call may be slow)

Install
───────
    pip install httpx python-dotenv

Run it
──────
    python 37_cognitive_layer.py
"""

from __future__ import annotations

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

MEMORY_URL = os.getenv("MEMORY_URL", "http://localhost:8211")
KG_URL = os.getenv("KG_URL", "http://localhost:8212")
SKILL_URL = os.getenv("SKILL_URL", "http://localhost:8213")
WS = "demo-workspace"


def sep(t: str) -> None:
    print(f"\n{'─' * 60}\n  {t}\n{'─' * 60}")


with httpx.Client(timeout=120.0) as c:
    sep("Skill Registry")
    c.post(f"{SKILL_URL}/skills", json={"workspace": WS, "name": "deploy",
           "description": "How to deploy the service", "content": "1. build 2. push 3. rollout", "version": 1})
    print("  skills:", c.get(f"{SKILL_URL}/skills", params={"workspace": WS}).json())

    sep("Knowledge Graph")
    c.post(f"{KG_URL}/entities", json={"workspace": WS, "id": "svc-api", "type": "service", "name": "API"})
    c.post(f"{KG_URL}/entities", json={"workspace": WS, "id": "db-pg", "type": "database", "name": "Postgres"})
    c.post(f"{KG_URL}/relations", json={"workspace": WS, "from_id": "svc-api", "to_id": "db-pg", "type": "depends_on"})
    print("  neighbors(svc-api):", c.get(f"{KG_URL}/neighbors", params={"workspace": WS, "entity": "svc-api"}).json())

    sep("Memory (Letta-backed)")
    r = c.post(f"{MEMORY_URL}/memory", json={"workspace": WS, "kind": "decision",
               "text": "We standardized on Qdrant for all vector search."})
    print("  store:", r.json())
    r = c.post(f"{MEMORY_URL}/recall", json={"workspace": WS, "query": "what vector database do we use?", "k": 3})
    print("  recall:", r.json())
    print("  (memory is Letta-backed; if it shows empty/unavailable, give Letta a moment to warm up)")

sep("Over MCP")
print("  All of the above are also MCP tools on the RunLedger MCP server:")
print("  memory_store · memory_recall · kg_add_entity · kg_add_relation · kg_neighbors · skill_list · skill_get")

print("\n✓ Example 37 complete.\n")
