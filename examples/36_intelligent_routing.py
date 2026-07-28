"""
Example 36 — Intelligent Routing

Classifies a request along complexity × risk (+ reasoning effort) and maps it to a model tier,
so simple/low-risk work goes to a cheap model and only hard/high-risk work reaches a frontier model.

This example calls the router service directly so you can see the classification. In production it's
an opt-in gateway stage (`intelligent_routing_enabled` on a route, or `"intelligent_routing": true`
per request) that forwards to the resolved tier's alias.

Prerequisites
─────────────
  • The router service is up:  docker compose up -d
  • For the LLM/hybrid classifier, a local Ollama model on the host (else it falls back to heuristic).

Install
───────
    pip install httpx python-dotenv

Run it
──────
    python 36_intelligent_routing.py

Key .env variables:
    ROUTER_URL  — http://localhost:8210  (default)
"""

from __future__ import annotations

import json
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

ROUTER_URL = os.getenv("ROUTER_URL", "http://localhost:8210")

CONFIG = {
    "classifier_mode": "hybrid",  # hybrid | llm | heuristic
    "tiers": {"cheap": "gpt-4o-mini", "mid": "gpt-4o", "frontier": "o1"},
    "matrix": {
        "simple": {"low": "cheap", "high": "mid"},
        "medium": {"low": "mid", "high": "frontier"},
        "complex": {"low": "frontier", "high": "frontier"},
    },
    "reasoning_effort": True,
    "on_failure": "passthrough",
}

CASES = [
    ("Simple, low-risk", "Summarize this meeting transcript in three bullets."),
    ("Looks simple, high-risk", "Does this contract create regulatory compliance exposure for us?"),
]


def sep(t: str) -> None:
    print(f"\n{'─' * 60}\n  {t}\n{'─' * 60}")


with httpx.Client(timeout=60.0) as client:
    for label, prompt in CASES:
        sep(label)
        resp = client.post(
            f"{ROUTER_URL}/classify",
            json={"messages": [{"role": "user", "content": prompt}], "config": CONFIG},
        )
        if resp.status_code != 200:
            print(f"  ERROR {resp.status_code}: {resp.text[:200]}")
            continue
        d = resp.json()
        print(f"  prompt:     {prompt!r}")
        print(f"  complexity: {d['complexity']}   risk: {d['risk']}   effort: {d['reasoning_effort']}")
        print(f"  → tier:     {d['tier']}  →  alias: {d['alias']}   ({d['method']})")

sep("Enable it on a gateway route")
print("  Persistent:  POST /gateway/routes  with  \"intelligent_routing_enabled\": true")
print("               + a routing_config:")
print("               " + json.dumps(CONFIG))
print("  Ad-hoc:      add  \"intelligent_routing\": true  to a /gateway/chat/completions body")

print("\n✓ Example 36 complete.\n")
