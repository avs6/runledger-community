#!/usr/bin/env python3
"""Generate LocalAI-style OTLP trace traffic into a RunLedger workspace."""

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


def attr(key: str, value: Any) -> dict[str, Any]:
    if isinstance(value, bool):
        wrapped = {"boolValue": value}
    elif isinstance(value, int):
        wrapped = {"intValue": str(value)}
    elif isinstance(value, float):
        wrapped = {"doubleValue": value}
    else:
        wrapped = {"stringValue": str(value)}
    return {"key": key, "value": wrapped}


def ns(value: datetime) -> str:
    return str(int(value.timestamp() * 1_000_000_000))


def provider(model: str) -> str:
    lower = model.lower()
    if "llama" in lower:
        return "meta"
    if "gemma" in lower:
        return "google"
    if "qwen" in lower:
        return "alibaba"
    if "deepseek" in lower:
        return "deepseek"
    return "ollama"


def cost(model: str, input_tokens: int, output_tokens: int) -> float:
    pin, pout = PRICES.get(model, (0.05, 0.10))
    return round((input_tokens * pin + output_tokens * pout) / 1_000_000, 8)


def make_payload(trace_count: int, *, source: str, service_name: str) -> dict[str, Any]:
    resource_spans: list[dict[str, Any]] = []
    now = datetime.now(UTC)

    for _ in range(trace_count):
        feature, agent, skill, tool, team = random.choice(WORKFLOWS)
        model = random.choice(MODELS)
        trace_id = uuid.uuid4().hex
        agent_span = uuid.uuid4().hex[:16]
        llm_span = uuid.uuid4().hex[:16]
        tool_span = uuid.uuid4().hex[:16]
        start = now - timedelta(minutes=random.uniform(0, 60))
        llm_start = start + timedelta(milliseconds=random.randint(40, 180))
        tool_start = start + timedelta(milliseconds=random.randint(260, 900))
        end = start + timedelta(milliseconds=random.randint(900, 5200))
        input_tokens = random.randint(250, 4200)
        output_tokens = random.randint(80, 1600)
        amount = cost(model, input_tokens, output_tokens)

        resource_spans.append(
            {
                "resource": {
                    "attributes": [
                        attr("service.name", service_name),
                        attr("team", team),
                        attr("application", "LocalAI Agent Stack"),
                        attr("runledger.source", source),
                    ]
                },
                "scopeSpans": [
                    {
                        "scope": {"name": "runledger-localai-demo", "version": "1.0"},
                        "spans": [
                            {
                                "traceId": trace_id,
                                "spanId": agent_span,
                                "name": agent,
                                "kind": 1,
                                "startTimeUnixNano": ns(start),
                                "endTimeUnixNano": ns(end),
                                "attributes": [
                                    attr("openinference.span.kind", "AGENT"),
                                    attr("agent_name", agent),
                                    attr("skill", skill),
                                    attr("feature_tag", feature),
                                    attr("session.id", f"{source}-otlp-{random.randint(1, 80):03d}"),
                                    attr("end_user_id", f"{source}_user_{random.randint(1, 40)}"),
                                ],
                                "status": {"code": "STATUS_CODE_OK"},
                            },
                            {
                                "traceId": trace_id,
                                "spanId": llm_span,
                                "parentSpanId": agent_span,
                                "name": f"chat {model}",
                                "kind": 3,
                                "startTimeUnixNano": ns(llm_start),
                                "endTimeUnixNano": ns(end),
                                "attributes": [
                                    attr("openinference.span.kind", "LLM"),
                                    attr("gen_ai.system", provider(model)),
                                    attr("gen_ai.request.model", model),
                                    attr("gen_ai.response.model", model),
                                    attr("gen_ai.usage.input_tokens", input_tokens),
                                    attr("gen_ai.usage.output_tokens", output_tokens),
                                    attr("llm.cost.total", amount),
                                    attr("llm.request_id", f"localai-{uuid.uuid4().hex[:12]}"),
                                ],
                                "status": {"code": "STATUS_CODE_OK"},
                            },
                            {
                                "traceId": trace_id,
                                "spanId": tool_span,
                                "parentSpanId": agent_span,
                                "name": tool,
                                "kind": 1,
                                "startTimeUnixNano": ns(tool_start),
                                "endTimeUnixNano": ns(end),
                                "attributes": [
                                    attr("openinference.span.kind", "TOOL"),
                                    attr("tool.name", tool),
                                    attr("tool.risk_score", random.randint(1, 60)),
                                ],
                                "status": {"code": "STATUS_CODE_OK"},
                            },
                        ],
                    }
                ],
            }
        )

    return {"resourceSpans": resource_spans}


def post_json(url: str, key: str, payload: dict[str, Any]) -> None:
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        method="POST",
    )
    with request.urlopen(req, timeout=30) as resp:
        if resp.status != 200:
            raise RuntimeError(f"{url} -> {resp.status}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate LocalAI OTLP traffic into RunLedger.")
    parser.add_argument("--state-file", default="scripts/.localai-runledger.json")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--workspace", default="Open WebUI")
    parser.add_argument("--source", default="localai-otlp")
    parser.add_argument("--batches", type=int, default=2)
    parser.add_argument("--traces", type=int, default=40)
    parser.add_argument("--sleep", type=float, default=1.0)
    args = parser.parse_args()

    state = load_state(Path(args.state_file))
    base_url = (args.base_url or state.get("base_url") or "http://localhost:8201").rstrip("/")
    key = workspace_key(state, args.workspace)

    for batch in range(1, args.batches + 1):
        payload = make_payload(args.traces, source=args.source, service_name=args.workspace)
        post_json(f"{base_url}/v1/traces", key, payload)
        print(f"batch {batch}/{args.batches}: {args.traces} OTLP traces -> {args.workspace}")
        if batch < args.batches:
            time.sleep(args.sleep)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
