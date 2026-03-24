"""
Example 25 — Outcome & ROI Tracking
====================================
Expected cost: ~$0.0008 per call + outcome events (free)

Demonstrates:
- Recording binary / score / revenue outcomes against agent runs
- Querying outcome summary and workflow ROI
- Correlating quality scores with cost

Prerequisites:
    export RUNLEDGER_API_KEY=rl_live_...
    export OPENAI_API_KEY=sk-...
"""

from __future__ import annotations

import os
import random
import time
import uuid

import runledger_sdk as rl

BASE_URL = os.environ.get("RUNLEDGER_BASE_URL", "http://localhost:8000")
API_KEY = os.environ.get("RUNLEDGER_API_KEY", "")


def simulate_support_run(client: rl.RunLedger, ticket_id: str) -> str:
    """Simulate an AI support ticket resolution and record its outcome."""
    run_id = str(uuid.uuid4())

    client.run_start(
        run_id=run_id,
        feature_tag="support-resolution",
        session_id=ticket_id,
        deployment_version="support-agent:v2",
    )

    # Simulate LLM call (in production this would be rl.instrument())
    time.sleep(0.05)
    input_tokens = random.randint(200, 600)
    output_tokens = random.randint(80, 300)

    client.provider_call(
        run_id=run_id,
        model="gpt-4o-mini",
        provider="openai",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=random.randint(300, 1200),
    )

    # Simulate resolution success (70% of the time)
    resolved = random.random() < 0.70
    resolution_time_mins = random.uniform(1.5, 8.0)

    client.run_end(run_id=run_id, status="succeeded")

    # Record binary outcome: was the ticket resolved?
    client.outcome(
        run_id=run_id,
        outcome_type="binary",
        value=1.0 if resolved else 0.0,
        label="ticket_resolved",
        workflow="support-resolution",
    )

    # Record revenue outcome: saved 15 min of human agent time at $0.50/min
    if resolved:
        saved_usd = resolution_time_mins * 0.50
        client.outcome(
            run_id=run_id,
            outcome_type="revenue",
            value=saved_usd,
            label="agent_time_saved_usd",
            workflow="support-resolution",
        )

    status_str = "✓ resolved" if resolved else "✗ escalated"
    print(f"  Ticket {ticket_id[:8]}… {status_str}  tokens={input_tokens+output_tokens}")
    return run_id


def main() -> None:
    print("=== RunLedger Outcome & ROI Example ===\n")

    client = rl.RunLedger(api_key=API_KEY, base_url=BASE_URL)

    print("1. Simulating 10 support ticket resolutions…")
    run_ids = []
    for i in range(10):
        ticket_id = str(uuid.uuid4())
        rid = simulate_support_run(client, ticket_id)
        run_ids.append(rid)

    client.flush()

    # 2. Query outcome summary
    import httpx

    api = httpx.Client(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=10,
    )

    print("\n2. Outcome summary (last 30 days):")
    resp = api.get("/outcomes/summary")
    if resp.status_code == 200:
        s = resp.json()
        print(f"   total_outcomes  = {s.get('total_outcomes', 0)}")
        print(f"   success_rate    = {float(s.get('success_rate') or 0)*100:.1f}%")
        print(f"   total_revenue   = ${float(s.get('total_revenue_usd') or 0):.2f}")
        print(f"   avg_roi         = {float(s.get('avg_roi') or 0)*100:.1f}%")
    else:
        print(f"   (HTTP {resp.status_code})")

    print("\n3. Workflow ROI breakdown:")
    resp = api.get("/outcomes/workflows")
    if resp.status_code == 200:
        workflows = resp.json().get("items", [])
        for w in workflows[:5]:
            roi = float(w.get("roi") or 0) * 100
            print(
                f"   {w['workflow']:30s}  runs={w.get('run_count',0):4d}  "
                f"revenue=${float(w.get('total_revenue_usd') or 0):7.2f}  "
                f"roi={roi:+.1f}%"
            )
    else:
        print(f"   (HTTP {resp.status_code})")

    print("\n4. Quality-cost correlation (last 30 days):")
    resp = api.get("/outcomes/quality-correlation")
    if resp.status_code == 200:
        buckets = resp.json().get("items", [])
        for b in buckets:
            print(
                f"   cost_bucket={b.get('cost_bucket','?'):12s}  "
                f"avg_score={float(b.get('avg_score') or 0):.3f}  "
                f"runs={b.get('run_count',0)}"
            )
    else:
        print(f"   (HTTP {resp.status_code})")

    api.close()
    print("\n✓ Done.")


if __name__ == "__main__":
    main()
