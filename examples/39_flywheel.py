"""
Example 39 — Optimization Flywheel (cost × quality SLA)

The flywheel closes the loop: it learns the cheapest optimization configuration per traffic
segment that still holds your quality SLA, then recommends (or auto-applies) it.

Two ways to use it:
  1. The stateless analyzer directly (flywheel-svc /analyze) — feed it observations, get
     recommendations. No auth, no DB. Great for what-if analysis.
  2. The workspace API — configure the SLA, run the loop over your own recorded traffic,
     and review / apply recommendations.

Prerequisites
─────────────
  docker compose up -d
  # For part 2, set RUNLEDGER_API_KEY in .env (POST /auth/login returns one).

Install
───────
    pip install httpx python-dotenv

Run it
──────
    python 39_flywheel.py
"""

from __future__ import annotations

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

FLYWHEEL_URL = os.getenv("FLYWHEEL_URL", "http://localhost:8215")
API_URL = os.getenv("RUNLEDGER_BASE_URL_LOCAL", "http://localhost:8201")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")


def part1_analyzer() -> None:
    """Call the stateless analyzer directly with hand-built observations."""
    print("── 1. Analyzer: cheapest config per segment that holds the SLA ──")
    payload = {
        "segment_by": "outcome_type",
        "min_quality": 0.85,
        "min_sample_size": 20,
        # Only allow the flywheel to change the model here.
        "action_space": ["model", "routing"],
        "segments": [
            {
                "segment_key": "refund_resolved",
                "observations": [
                    # Expensive frontier model — most traffic runs here (the "current" config).
                    {"config": {"model": "gpt-4o"}, "n": 140, "avg_cost_per_req": 0.028, "quality": 0.94},
                    # Cheaper model that still clears the 0.85 SLA.
                    {"config": {"model": "gpt-4o-mini"}, "n": 90, "avg_cost_per_req": 0.006, "quality": 0.90},
                ],
            },
        ],
    }
    r = httpx.post(f"{FLYWHEEL_URL}/analyze", json=payload, timeout=30)
    r.raise_for_status()
    for rec in r.json()["recommendations"]:
        pct = rec["est_cost_delta_pct"]
        print(
            f"  [{rec['kind']}] {rec['segment_key']}: "
            f"{rec['current_config'].get('model')} → {rec['proposed_config'].get('model')} "
            f"({pct * 100:.0f}% cost, quality {rec['current_quality']:.2f}→{rec['proposed_quality']:.2f}, "
            f"{rec['confidence']} confidence)"
        )
        print(f"      {rec['rationale']}")


def part2_api() -> None:
    """Configure the SLA, run the loop over recorded traffic, review recommendations."""
    if not API_KEY:
        print("\n── 2. Workspace API: set RUNLEDGER_API_KEY to try this part ──")
        return
    print("\n── 2. Workspace API: configure SLA, run, review ──")
    h = {"Authorization": f"Bearer {API_KEY}"}

    # Configure: enable, hold a 0.85 quality SLA, segment by outcome type, propose only.
    settings = httpx.put(
        f"{API_URL}/gateway/flywheel/settings",
        headers=h,
        json={
            "enabled": True,
            "apply_mode": "approval",
            "segment_by": "outcome_type",
            "min_quality": 0.85,
            "quality_metric": {"type": "blend", "weight": 0.5},
        },
        timeout=30,
    ).json()
    print(f"  settings: enabled={settings['enabled']} SLA={settings['min_quality']} mode={settings['apply_mode']}")

    # Run the analysis now (normally a nightly beat job does this).
    run = httpx.post(f"{API_URL}/gateway/flywheel/run", headers=h, timeout=60).json()
    print(f"  run: {run['status']} · {run['recommendations']} recommendation(s)")

    # Review pending recommendations.
    recs = httpx.get(
        f"{API_URL}/gateway/flywheel/recommendations?status=pending", headers=h, timeout=30
    ).json()
    for rec in recs["items"]:
        print(f"  • [{rec['kind']}] {rec['segment_key']} — {rec['rationale']}")
        # To apply:  httpx.post(f"{API_URL}/gateway/flywheel/recommendations/{rec['id']}/apply", headers=h)
    if not recs["items"]:
        print("  (no recommendations yet — the flywheel needs traffic + outcomes to learn from)")


if __name__ == "__main__":
    part1_analyzer()
    part2_api()
