"""
Example: Gateway build & improve posture — prompts, agents, workflows, evaluation, and replay.

Demonstrates querying the gateway-build-posture endpoint that surfaces gateway context
(active routes, routing policies, guardrail rules, active guardrails), prompt count,
agent count, workflow count and runs, evaluation datasets and experiments, and replay
datasets and experiments.

Required env vars:
  RUNLEDGER_BASE_URL
  RUNLEDGER_API_KEY
"""

from __future__ import annotations

import json
import os

import requests

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8201")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")


def api(method: str, path: str, params: dict | None = None):
    response = requests.request(
        method,
        f"{BASE_URL}{path}",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        params=params,
        timeout=30,
    )
    response.raise_for_status()
    return response.json() if response.content else None


def main():
    print("--- Gateway Build & Improve Posture ---")
    posture = api("GET", "/analytics/gateway-build-posture")
    print(json.dumps(posture, indent=2))

    gw = posture.get("gateway_context", {})
    print(f"\nActive routes: {gw.get('active_routes', 0)}")
    print(f"Routing policies: {gw.get('routing_policies', 0)}")
    print(f"Guardrail rules: {gw.get('guardrail_rules', 0)}")
    print(f"Active guardrails: {gw.get('active_guardrails', 0)}")

    prompts = posture.get("prompts", {})
    print(f"\nPrompts: {prompts.get('total', 0)}")

    agents = posture.get("agents", {})
    print(f"Agents: {agents.get('total', 0)}")

    workflows = posture.get("workflows", {})
    print(f"Workflows: {workflows.get('total', 0)}")
    print(f"Workflow runs: {workflows.get('runs', 0)}")

    evaluation = posture.get("evaluation", {})
    print(f"\nEval datasets: {evaluation.get('datasets', 0)}")
    print(f"Eval experiments: {evaluation.get('experiments', 0)}")

    replay = posture.get("replay", {})
    print(f"\nReplay datasets: {replay.get('datasets', 0)}")
    print(f"Replay experiments: {replay.get('experiments', 0)}")


if __name__ == "__main__":
    main()
