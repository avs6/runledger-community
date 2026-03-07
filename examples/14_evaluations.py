"""
Example 14 — Evaluations & Scores

Demonstrates:
  1. rl.score()  — submit a quality score from the SDK (run_id from context)
  2. POST /evaluations/scores  — submit a score directly via HTTP
  3. GET  /evaluations/scores  — list recent scores
  4. GET  /analytics/scores/summary    — avg score per name + delta %
  5. GET  /analytics/scores/regressions — names where avg dropped >20%

Install
───────
    pip install httpx python-dotenv

    # SDK (for steps 1 only):
    pip install -e "path/to/runledger/packages/sdk[openai]"

Run it
──────
    # Copy .env.example → .env, then:
    python 14_evaluations.py

Key .env variables:
    RUNLEDGER_API_KEY   — your workspace API key
    RUNLEDGER_BASE_URL  — http://localhost:8000  (default)
    OPENAI_API_KEY      — optional; only needed for step 1 if you use rl.instrument()
"""

from __future__ import annotations

import os
import sys
import uuid

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")

if not API_KEY:
    print("ERROR: RUNLEDGER_API_KEY env var is required", file=sys.stderr)
    sys.exit(1)

HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def sep(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print("─" * 60)


# ── Step 1 — rl.score() via SDK ───────────────────────────────────────────────

sep("Step 1 — rl.score() via SDK (local mode — no OpenAI key needed)")

try:
    from runledger_sdk import RunLedger  # type: ignore[import]

    rl = RunLedger(local=True)

    run_id = str(uuid.uuid4())
    with rl.context(end_user_id="demo-user", feature_tag="support-chat", run_id=run_id) as rid:
        # Simulate agent work
        print(f"  [context] run_id = {rid}")

        # Score from within context — run_id is picked up automatically
        rl.score("helpfulness", 0.9, label="good", source="human")
        rl.score("relevance", 0.75, confidence=0.9)

    print("  SDK scores logged (local mode — events printed above, not sent to API)")

except ImportError:
    print("  runledger-sdk not installed — skipping SDK demo")
    print("  Install: pip install -e path/to/runledger/packages/sdk")


# ── Step 2 — POST /evaluations/scores via HTTP ────────────────────────────────

sep("Step 2 — POST /evaluations/scores (HTTP)")

score_payload = {
    "name": "helpfulness",
    "value": 0.88,
    "label": "good",
    "source": "human",
    "confidence": 0.95,
}

with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
    resp = client.post("/evaluations/scores", json=score_payload)

if resp.status_code == 201:
    score = resp.json()
    print(f"  Created score: id={score['id']}")
    print(f"    name={score['name']}  value={score['value']}  source={score['source']}")
    created_score_id = score["id"]
else:
    print(f"  ERROR {resp.status_code}: {resp.text}")
    created_score_id = None

# Submit a second score with a run_id
score_with_run = {
    "name": "relevance",
    "value": 0.72,
    "label": "neutral",
    "source": "rule",
    "run_id": str(uuid.uuid4()),
}

with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
    resp2 = client.post("/evaluations/scores", json=score_with_run)

if resp2.status_code == 201:
    s2 = resp2.json()
    print(f"  Created score: id={s2['id']}  run_id={s2['run_id']}")


# ── Step 3 — GET /evaluations/scores ─────────────────────────────────────────

sep("Step 3 — GET /evaluations/scores")

with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
    resp = client.get("/evaluations/scores", params={"limit": 10})

if resp.status_code == 200:
    data = resp.json()
    items = data["items"]
    print(f"  {len(items)} recent score(s):")
    for item in items[:5]:
        run_tag = f"  run={item['run_id'][:8]}…" if item["run_id"] else ""
        print(f"    [{item['name']}] {item['value']}  ({item['source']}){run_tag}")
else:
    print(f"  ERROR {resp.status_code}: {resp.text}")


# ── Step 4 — GET /analytics/scores/summary ───────────────────────────────────

sep("Step 4 — GET /analytics/scores/summary")

with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
    resp = client.get("/analytics/scores/summary")

if resp.status_code == 200:
    summary = resp.json()
    items = summary["items"]
    if not items:
        print("  No score data yet. Scores appear after the next rollup (or immediately in summary).")
    for item in items:
        delta = f"  Δ {float(item['change_pct']):+.1f}%" if item["change_pct"] is not None else ""
        print(
            f"  {item['name']:20s}  avg={float(item['avg_value']):.4f}"
            f"  n={item['sample_count']}{delta}"
        )
else:
    print(f"  ERROR {resp.status_code}: {resp.text}")


# ── Step 5 — GET /analytics/scores/regressions ───────────────────────────────

sep("Step 5 — GET /analytics/scores/regressions (>20% drop)")

with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
    resp = client.get("/analytics/scores/regressions")

if resp.status_code == 200:
    regressions = resp.json()
    if not regressions:
        print("  No score regressions detected — all scores are stable. ✓")
    else:
        print(f"  {len(regressions)} regression(s) detected!")
        for r in regressions:
            print(
                f"    [{r['name']}]  current={float(r['current_avg']):.4f}"
                f"  prior={float(r['prior_avg']):.4f}"
                f"  change={float(r['change_pct']):+.1f}%"
                f"  n={r['sample_count']}"
            )
else:
    print(f"  ERROR {resp.status_code}: {resp.text}")

print("\n✓ Example 14 complete.\n")
