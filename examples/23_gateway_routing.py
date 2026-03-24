"""
Example 23 — Model Gateway with Routing Policies
=================================================
Expected cost: ~$0.0015 per call (routed to cheapest model for each request)

Demonstrates:
- Creating a gateway route alias
- Creating a cost-optimised routing policy
- Sending completions through the gateway proxy
- Reading per-request decision_reason from the gateway log

Prerequisites:
    export RUNLEDGER_API_KEY=rl_live_...
    export OPENAI_API_KEY=sk-...
"""

from __future__ import annotations

import os

import httpx

BASE_URL = os.environ.get("RUNLEDGER_BASE_URL", "http://localhost:8000")
API_KEY = os.environ.get("RUNLEDGER_API_KEY", "")

headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
client = httpx.Client(base_url=BASE_URL, headers=headers, timeout=30)


def setup_route() -> str:
    """Create a gateway route for 'gpt-4o-mini' if it doesn't exist."""
    resp = client.get("/gateway/routes")
    resp.raise_for_status()
    existing = {r["alias"]: r["id"] for r in resp.json().get("items", [])}

    if "gpt-4o-mini" in existing:
        print(f"  Route exists: {existing['gpt-4o-mini'][:8]}…")
        return existing["gpt-4o-mini"]

    resp = client.post(
        "/gateway/routes",
        json={
            "alias": "gpt-4o-mini",
            "provider": "openai",
            "target_model": "gpt-4o-mini",
            "api_key_env_var": "OPENAI_API_KEY",
            "priority": 10,
        },
    )
    resp.raise_for_status()
    route_id = resp.json()["id"]
    print(f"  Created route: {route_id[:8]}…")
    return route_id


def setup_policy(route_id: str) -> str:
    """Create a cost-optimised routing policy."""
    resp = client.get("/gateway/policies")
    resp.raise_for_status()
    existing = {p["name"]: p["id"] for p in resp.json().get("items", [])}

    if "cost-optimised" in existing:
        print(f"  Policy exists: {existing['cost-optimised'][:8]}…")
        return existing["cost-optimised"]

    resp = client.post(
        "/gateway/policies",
        json={
            "name": "cost-optimised",
            "strategy": "cost_optimized",
            "config": {},
            "route_id": route_id,
        },
    )
    resp.raise_for_status()
    policy_id = resp.json()["id"]
    print(f"  Created policy: {policy_id[:8]}…")
    return policy_id


def send_completion(prompt: str) -> dict:
    """Send a chat completion through the gateway proxy."""
    resp = client.post(
        "/gateway/chat/completions",
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 100,
        },
    )
    resp.raise_for_status()
    return resp.json()


def show_request_log() -> None:
    """Print the last 5 gateway requests with routing decisions."""
    resp = client.get("/gateway/requests", params={"limit": 5})
    resp.raise_for_status()
    items = resp.json().get("items", [])
    print(f"\n  Last {len(items)} gateway request(s):")
    for req in items:
        cost = req.get("estimated_cost_usd") or 0
        print(
            f"    [{req['status']}] {req['alias']} → "
            f"${float(cost):.6f}  reason={req.get('decision_reason', '—')}"
        )


def main() -> None:
    print("=== RunLedger Model Gateway Example ===\n")

    print("1. Setting up gateway route…")
    route_id = setup_route()

    print("2. Setting up routing policy…")
    setup_policy(route_id)

    print("3. Sending completions through gateway…")
    prompts = [
        "Summarise the FinOps framework in one sentence.",
        "What is cost chargeback in cloud billing?",
        "Name three token-efficient prompt techniques.",
    ]
    for i, prompt in enumerate(prompts, 1):
        result = send_completion(prompt)
        content = result["choices"][0]["message"]["content"]
        tokens = result.get("usage", {})
        print(f"  [{i}] in={tokens.get('prompt_tokens', 0)}  out={tokens.get('completion_tokens', 0)}")
        print(f"       {content[:80]}…")

    print("\n4. Gateway request log:")
    show_request_log()

    # Gateway stats
    resp = client.get("/gateway/stats")
    resp.raise_for_status()
    stats = resp.json()
    print(f"\n5. Gateway stats:")
    print(f"   total_requests={stats.get('total_requests', 0)}")
    print(f"   cache_hits={stats.get('cache_hits', 0)}")
    print(f"   total_cost_usd=${float(stats.get('total_cost_usd') or 0):.4f}")
    print(f"   avg_latency_ms={stats.get('avg_latency_ms', 0):.0f}")

    client.close()
    print("\n✓ Done.")


if __name__ == "__main__":
    main()
