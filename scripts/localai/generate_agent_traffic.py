#!/usr/bin/env python3
"""Generate continuous LocalAI-style agent traffic into a RunLedger workspace."""

from __future__ import annotations

import argparse
import json
import random
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib import request


MODELS = [
    "llama3.2",
    "llama3.2:3b",
    "gemma3:latest",
    "qwen3.5:latest",
    "qwen2.5-coder:14b",
    "deepseek-r1:8b",
    "deepseek-r1:14b",
    "nomic-embed-text",
]

WORKFLOWS = [
    ("research-summary", "Research Agent", "web_research", "searxng_search", "Research"),
    ("code-review", "Code Agent", "review_patch", "repo_reader", "Engineering"),
    ("ticket-triage", "Ticket Agent", "classify_ticket", "ticket_router", "Support"),
    ("billing-help", "Billing Agent", "invoice_lookup", "billing_policy", "Finance"),
    ("agent-planning", "Planner Agent", "plan_task", "memory_recall", "Operations"),
    ("knowledge-search", "RAG Agent", "knowledge_search", "vector_search", "Support"),
]

PRICES = {
    "llama3.2": (0.05, 0.10),
    "llama3.2:3b": (0.03, 0.06),
    "gemma3:latest": (0.04, 0.08),
    "qwen3.5:latest": (0.06, 0.12),
    "qwen2.5-coder:14b": (0.12, 0.24),
    "deepseek-r1:8b": (0.08, 0.16),
    "deepseek-r1:14b": (0.14, 0.30),
    "nomic-embed-text": (0.01, 0.0),
}


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"State file not found: {path}. Run bootstrap_runledger_org.py first.")
    return json.loads(path.read_text(encoding="utf-8"))


def workspace_key(state: dict[str, Any], name: str) -> str:
    key = state.get("workspaces", {}).get(name, {}).get("api_key")
    if not key:
        raise SystemExit(f"No key for workspace '{name}' in state file.")
    return key


def post_json(url: str, key: str, payload: dict[str, Any], expected: tuple[int, ...] = (200, 202)) -> None:
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        method="POST",
    )
    with request.urlopen(req, timeout=30) as resp:
        if resp.status not in expected:
            raise RuntimeError(f"{url} -> {resp.status}")


def cost(model: str, input_tokens: int, output_tokens: int) -> float:
    pin, pout = PRICES.get(model, (0.05, 0.10))
    return round((input_tokens * pin + output_tokens * pout) / 1_000_000, 8)


def make_events(batch_size: int, *, source: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    now = datetime.now(UTC)
    for _ in range(batch_size):
        feature, agent, skill, tool, team = random.choice(WORKFLOWS)
        model = random.choice(MODELS)
        input_tokens = random.randint(200, 4200)
        output_tokens = random.randint(80, 1800)
        cached_tokens = random.randint(0, input_tokens // 2) if random.random() < 0.28 else 0
        latency = random.randint(250, 5200)
        ok = random.random() > 0.07
        run_id = str(uuid.uuid4())
        span_id = str(uuid.uuid4())
        started = now - timedelta(seconds=random.randint(0, 300))
        ended = started + timedelta(milliseconds=latency)
        amount = cost(model, max(0, input_tokens - cached_tokens), output_tokens)
        status = "succeeded" if ok else "failed"
        provider_status = "success" if ok else "error"
        events.extend(
            [
                {
                    "event_type": "run_start",
                    "run_id": run_id,
                    "started_at": started.isoformat().replace("+00:00", "Z"),
                    "end_user_id": f"{source}_user_{random.randint(1, 40)}",
                    "session_id": f"{source}_sess_{random.randint(1, 20)}",
                    "feature_tag": feature,
                    "agent_name": agent,
                    "metadata": {
                        "source": source,
                        "skill": skill,
                        "team": team,
                        "application": "LocalAI Agent Stack",
                    },
                },
                {
                    "event_type": "span_start",
                    "span_id": span_id,
                    "run_id": run_id,
                    "span_type": "agent",
                    "name": agent,
                    "started_at": started.isoformat().replace("+00:00", "Z"),
                },
                {
                    "event_type": "provider_call",
                    "run_id": run_id,
                    "span_id": span_id,
                    "provider": "ollama",
                    "model": model,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cached_input_tokens": cached_tokens,
                    "latency_ms": latency,
                    "cost_usd": amount,
                    "status": provider_status,
                },
                {
                    "event_type": "tool_call",
                    "run_id": run_id,
                    "span_id": span_id,
                    "tool_name": tool,
                    "tool_type": "read" if random.random() > 0.2 else "privileged",
                    "duration_ms": random.randint(40, 1300),
                    "risk_score": random.randint(1, 75),
                    "status": provider_status,
                },
                {
                    "event_type": "outcome",
                    "run_id": run_id,
                    "outcome_type": "task_completed",
                    "success": ok,
                    "value_usd": round(random.uniform(1.5, 18.0), 2) if ok else 0,
                    "labels": {"team": team, "source": source},
                },
                {
                    "event_type": "span_end",
                    "span_id": span_id,
                    "run_id": run_id,
                    "status": status,
                    "ended_at": ended.isoformat().replace("+00:00", "Z"),
                    "cost_usd": amount,
                },
                {
                    "event_type": "run_end",
                    "run_id": run_id,
                    "status": status,
                    "ended_at": ended.isoformat().replace("+00:00", "Z"),
                    "total_cost_usd": amount,
                    "total_input_tokens": input_tokens,
                    "total_output_tokens": output_tokens,
                },
            ]
        )
    return events


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate LocalAI/agent traffic into RunLedger.")
    parser.add_argument("--state-file", default="scripts/.localai-runledger.json")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--workspace", default="Python Console")
    parser.add_argument("--source", default="python-console")
    parser.add_argument("--batches", type=int, default=12)
    parser.add_argument("--batch-size", type=int, default=25)
    parser.add_argument("--sleep", type=float, default=2.0)
    args = parser.parse_args()

    state = load_state(Path(args.state_file))
    base_url = (args.base_url or state.get("base_url") or "http://localhost:8201").rstrip("/")
    key = workspace_key(state, args.workspace)

    for batch in range(1, args.batches + 1):
        events = make_events(args.batch_size, source=args.source)
        post_json(f"{base_url}/ingest/v1/batch", key, {"events": events})
        print(f"batch {batch}/{args.batches}: {args.batch_size} runs -> {args.workspace}")
        if batch < args.batches:
            time.sleep(args.sleep)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
