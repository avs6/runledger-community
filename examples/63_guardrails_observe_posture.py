"""
Example: Guardrails observe posture — enforcement outcomes, latency, and feedback.

Demonstrates querying the guardrails-observe-posture endpoint that surfaces 30-day
evaluation breakdown (blocks, modifications, allows), rule coverage, mode breakdown,
false-positive feedback count, and latency impact.

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
    print("--- Guardrails Observe Posture ---")
    posture = api("GET", "/analytics/guardrails-observe-posture")
    print(json.dumps(posture, indent=2))

    rules = posture.get("rules", {})
    print(f"\nRules: {rules.get('active_rules', 0)} active of {rules.get('total_rules', 0)} total")

    evals = posture.get("evaluations", {})
    print(f"\nEvaluations (30d): {evals.get('total', 0):,}")
    print(f"Blocks: {evals.get('blocks', 0):,} ({evals.get('block_rate', 0) * 100:.1f}%)")
    print(f"Modifications: {evals.get('modifications', 0):,} ({evals.get('modification_rate', 0) * 100:.1f}%)")
    print(f"Allows: {evals.get('allows', 0):,}")
    print(f"Distinct rules fired: {evals.get('distinct_rules_fired', 0)}")
    print(f"Distinct models: {evals.get('distinct_models', 0)}")

    modes = posture.get("mode_breakdown", {})
    print(f"\nPre-call: {modes.get('pre_call', 0):,}")
    print(f"Post-call: {modes.get('post_call', 0):,}")

    feedback = posture.get("feedback", {})
    print(f"\nFalse positives: {feedback.get('false_positive_count', 0)}")

    perf = posture.get("performance", {})
    avg = perf.get("avg_latency_ms")
    mx = perf.get("max_latency_ms")
    print(f"Avg latency: {avg}ms" if avg else "Avg latency: --")
    print(f"Max latency: {mx}ms" if mx else "Max latency: --")


if __name__ == "__main__":
    main()
