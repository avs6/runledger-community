"""
Generate test runs across multiple workspaces/orgs to populate billing data.
Uses the /ingest/v1/batch endpoint with the correct event format.
"""
from __future__ import annotations

import asyncio
import random
import uuid
from datetime import UTC, datetime, timedelta

import httpx

BASE_URL = "http://localhost:8000"

WORKSPACES = [
    {"name": "Default Org / default",       "key": "rl_test_oDZzUDR-1RncfIEdu0tufvqKqHQjWA7fBsRXpzK-mDQ"},
    {"name": "Default Org / ML Research",   "key": "rl_test_9SXLH5zP7uQEPizpSYhq0cZRzmHfTHtpv8D-XGP7jMM"},
    {"name": "Alpha Labs / Alpha Labs WS",  "key": "rl_test_QSEB5FFfUtOBsRyAYRxfq30M9FmnRn3iUwEc8bx3jrE"},
]

# (provider, model, in_tok, out_tok)
MODELS = [
    ("ollama", "llama3.2",    800,  1200),
    ("ollama", "llama3.1:8b", 600,  900),
    ("ollama", "llama3.2",    1500, 2000),
    ("openai", "gpt-4o-mini", 400,  600),
    ("openai", "gpt-4o",      1000, 1500),
]

USERS = ["u_alice", "u_bob", "u_carol", "u_dave"]
AGENTS = ["rag-pipeline", "summarizer", "code-reviewer", "classifier"]


def make_run_events(started_at: datetime) -> list[dict]:
    run_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    provider, model, in_tok, out_tok = random.choice(MODELS)
    user_id = random.choice(USERS)
    agent = random.choice(AGENTS)
    latency = random.randint(800, 4000)
    ended_at = started_at + timedelta(milliseconds=latency)

    ts_start = started_at.isoformat().replace("+00:00", "Z")
    ts_end = ended_at.isoformat().replace("+00:00", "Z")

    return [
        {"event_type": "run_start",    "run_id": run_id, "agent_name": agent,
         "user_id": user_id, "started_at": ts_start},
        {"event_type": "span_start",   "span_id": span_id, "run_id": run_id,
         "span_type": "llm", "name": "llm-call", "started_at": ts_start},
        {"event_type": "provider_call","run_id": run_id, "span_id": span_id,
         "provider": provider, "model": model,
         "input_tokens": in_tok, "output_tokens": out_tok, "latency_ms": latency,
         "status": "success"},
        {"event_type": "span_end",     "span_id": span_id, "run_id": run_id,
         "ended_at": ts_end, "status": "succeeded"},
        {"event_type": "run_end",      "run_id": run_id, "ended_at": ts_end,
         "status": "succeeded"},
    ]


async def ingest_workspace(client: httpx.AsyncClient, ws: dict, n_runs: int = 30) -> int:
    hdrs = {"Authorization": f"Bearer {ws['key']}", "Content-Type": "application/json"}
    now = datetime.now(UTC)
    all_events: list[dict] = []

    for _ in range(n_runs):
        started_at = now - timedelta(days=random.uniform(0, 7), hours=random.uniform(0, 23))
        all_events.extend(make_run_events(started_at))

    resp = await client.post(
        f"{BASE_URL}/ingest/v1/batch",
        headers=hdrs,
        json={"events": all_events},
    )
    if resp.status_code == 202:
        return n_runs
    print(f"  ERROR {resp.status_code}: {resp.text[:200]}")
    return 0


async def main() -> None:
    async with httpx.AsyncClient(timeout=30) as client:
        for ws in WORKSPACES:
            print(f"→ {ws['name']}")
            ok = await ingest_workspace(client, ws, n_runs=30)
            print(f"  {ok} runs batched")

    print("\nDone. Waiting ~60s for Celery cost enrichment…")
    await asyncio.sleep(65)

    # Report totals
    async with httpx.AsyncClient(timeout=10) as client:
        for ws in WORKSPACES:
            hdrs = {"Authorization": f"Bearer {ws['key']}"}
            r = await client.get(f"{BASE_URL}/analytics/summary", headers=hdrs)
            d = r.json()
            cost = d.get("total_cost_usd", "?")
            runs = d.get("total_runs", "?")
            print(f"  {ws['name']}: {runs} runs, ${cost} total")


if __name__ == "__main__":
    asyncio.run(main())
