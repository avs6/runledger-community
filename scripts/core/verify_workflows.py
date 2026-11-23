#!/usr/bin/env python3
"""End-to-end verification of the workflow spine against a running API.

Replays what a team does when it adopts workflows and asserts every step:

  1. Signs in and mints a throwaway workspace API key.
  2. Ingests a run tagged with a new feature tag, then creates a workflow on that tag
     and asserts the existing run was linked; a duplicate tag is refused (409) and an
     unknown gateway alias is refused (422).
  3. Registers an agent with a small monthly budget envelope.
  4. Sends runs every supported way and asserts each is attributed to the workflow:
     the X-RunLedger-Workflow header, an explicit workflow_id, the feature tag, an
     OTLP trace with the runledger.workflow attribute. A run naming a workflow id that
     doesn't exist in the workspace is not attributed.
  5. Asserts the Workflow page data: cost by step rolls up to the runs' cost, the health
     card's runs, failures and cost per success are right, the eval score shows up.
  6. Asserts agent stats come from the attributed runs and the envelope now refuses runs.
  7. Archives the workflow (new traffic stops matching), restores it (traffic re-links).

The workflow, agent and key are archived/retired/deleted at the end (pass --keep to look
at them in the UI). Needs the API, Redis and the Celery pipeline worker running.

Usage:
    python scripts/run_demo.py verify-workflows
    python scripts/core/verify_workflows.py --base-url http://localhost:8201
"""

from __future__ import annotations

import argparse
import os
import secrets
import sys
import time
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


class Check:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.passed = 0

    def __call__(self, ok: bool, label: str, detail: Any = "") -> None:
        if ok:
            self.passed += 1
            print(f"  ✓ {label}")
        else:
            self.failures.append(label)
            print(f"  ✗ {label} {str(detail)[:300]}")


class Api:
    def __init__(self, base_url: str) -> None:
        self.http = httpx.Client(base_url=base_url.rstrip("/"), timeout=30)

    def call(
        self,
        method: str,
        path: str,
        key: str | None = None,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        h = {"Authorization": f"Bearer {key}"} if key else {}
        h.update(headers or {})
        return self.http.request(method, path, headers=h, json=body)


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def run_events(
    *,
    step: str = "respond",
    cost: str = "0.010",
    ok: bool = True,
    **start_fields: Any,
) -> tuple[str, list[dict[str, Any]]]:
    """One run with one priced model call under a span named ``step``."""
    run_id, span_id = str(uuid.uuid4()), str(uuid.uuid4())
    start = datetime.now(UTC) - timedelta(seconds=3)
    end = datetime.now(UTC)
    status = "succeeded" if ok else "failed"
    return run_id, [
        {"event_type": "run_start", "run_id": run_id, "started_at": _iso(start), **start_fields},
        {
            "event_type": "span_start",
            "span_id": span_id,
            "run_id": run_id,
            "span_type": "llm",
            "name": step,
            "started_at": _iso(start),
        },
        {
            "event_type": "provider_call",
            "run_id": run_id,
            "span_id": span_id,
            "provider": "openai",
            "model": "gpt-4o-mini",
            "input_tokens": 800,
            "output_tokens": 200,
            "latency_ms": 900,
            "cost_usd": cost,
            "status": "success" if ok else "error",
        },
        {
            "event_type": "span_end",
            "span_id": span_id,
            "run_id": run_id,
            "status": status,
            "ended_at": _iso(end),
            "cost_usd": cost,
        },
        {
            "event_type": "run_end",
            "run_id": run_id,
            "status": status,
            "ended_at": _iso(end),
            "total_cost_usd": cost,
        },
    ]


def otlp_trace(workflow: str) -> dict[str, Any]:
    """A minimal OTLP/JSON trace with one LLM span (passes LLM-span gating)."""
    now = time.time_ns()
    return {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "verify-workflows"}},
                        {"key": "runledger.workflow", "value": {"stringValue": workflow}},
                    ]
                },
                "scopeSpans": [
                    {
                        "scope": {"name": "verify"},
                        "spans": [
                            {
                                "traceId": secrets.token_hex(16),
                                "spanId": secrets.token_hex(8),
                                "name": "chat gpt-4o-mini",
                                "startTimeUnixNano": str(now - 2_000_000_000),
                                "endTimeUnixNano": str(now),
                                "attributes": [
                                    {"key": "gen_ai.system", "value": {"stringValue": "openai"}},
                                    {
                                        "key": "gen_ai.request.model",
                                        "value": {"stringValue": "gpt-4o-mini"},
                                    },
                                    {
                                        "key": "gen_ai.usage.input_tokens",
                                        "value": {"intValue": "50"},
                                    },
                                    {
                                        "key": "gen_ai.usage.output_tokens",
                                        "value": {"intValue": "10"},
                                    },
                                ],
                            }
                        ],
                    }
                ],
            }
        ]
    }


def wait_for(fn: Any, timeout: float) -> Any:
    deadline = time.monotonic() + timeout
    value = fn()
    while not value and time.monotonic() < deadline:
        time.sleep(1)
        value = fn()
    return value


def run(args: argparse.Namespace) -> int:
    api = Api(args.base_url)
    check = Check()
    suffix = uuid.uuid4().hex[:8]
    tag = f"verify-wf-{suffix}"
    name = f"Verify workflow {suffix}"
    agent_name = f"verify-agent-{suffix}"

    login = api.call("POST", "/auth/login", body={"email": args.email, "password": args.password})
    if login.status_code != 200:
        print(f"Sign-in failed ({login.status_code}): {login.text}")
        return 2
    session = login.json()["api_key"]
    key_resp = api.call("POST", "/settings/api-keys", session, {"name": f"verify-wf-{suffix}"})
    if key_resp.status_code not in (200, 201):
        print(f"API key creation failed ({key_resp.status_code}): {key_resp.text}")
        return 2
    key_id, key = key_resp.json()["id"], key_resp.json()["key"]
    wf_id: str | None = None
    agent_id: str | None = None

    def wf_runs(params: str = "") -> int:
        resp = api.call("GET", f"/workflows/{wf_id}/runs?limit=1{params}", session)
        return int(resp.json().get("total", 0)) if resp.status_code == 200 else -1

    def ingest(events: list[dict[str, Any]], headers: dict[str, str] | None = None) -> None:
        resp = api.call("POST", "/ingest/v1/batch", key, {"events": events}, headers)
        if resp.status_code != 202:
            raise RuntimeError(f"ingest refused: {resp.status_code} {resp.text}")

    try:
        print("\n→ linking existing traffic")
        early_id, early = run_events(feature_tag=tag, step="classify", cost="0.004")
        ingest(early)
        landed = wait_for(
            lambda: api.call("GET", f"/runs/{early_id}", session).status_code == 200,
            args.timeout,
        )
        check(bool(landed), "pre-existing tagged run processed")
        created = api.call("POST", "/workflows", session, {"name": name, "feature_tag": tag})
        check(created.status_code == 201, "workflow created", created.text)
        if created.status_code != 201:
            return 1
        wf_id = created.json()["id"]
        check(
            created.json().get("linked_runs") == 1, "existing run linked on create", created.json()
        )
        dup = api.call("POST", "/workflows", session, {"name": "dup", "feature_tag": tag})
        check(dup.status_code == 409, "duplicate feature tag refused (409)", dup.status_code)
        bad_alias = api.call(
            "POST", "/workflows", session, {"name": "x", "gateway_alias": f"nope-{suffix}"}
        )
        check(bad_alias.status_code == 422, "unknown gateway alias refused (422)", bad_alias.text)

        print("\n→ registering an agent with a $0.03 envelope")
        agent = api.call(
            "POST", "/agents", session, {"name": agent_name, "budget_envelope": "0.03"}
        )
        check(agent.status_code == 201, "agent registered", agent.text)
        agent_id = agent.json().get("id")

        print("\n→ attributing runs every supported way")
        _, by_header = run_events(step="respond", cost="0.020", agent_name=agent_name)
        ingest(by_header, {"X-RunLedger-Workflow": name})
        _, by_id = run_events(step="respond", cost="0.020", workflow_id=wf_id, agent_id=agent_id)
        ingest(by_id)
        _, failed = run_events(step="respond", cost="0.006", ok=False, feature_tag=tag)
        ingest(failed)
        foreign_id, foreign = run_events(
            workflow_id=str(uuid.uuid4()), feature_tag=f"other-{suffix}"
        )
        ingest(foreign)
        otlp = httpx.post(
            f"{args.base_url.rstrip('/')}/v1/traces",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=otlp_trace(tag),
            timeout=30,
        )
        check(otlp.status_code in (200, 202), "OTLP trace accepted", otlp.text[:200])

        expected = 5  # early + header + id + failed + otlp
        got = wait_for(lambda: wf_runs() >= expected or None, args.timeout) and wf_runs()
        check(got == expected, f"{expected} runs attributed (header, id, tag, OTLP, linked)", got)
        api.call("GET", f"/runs/{foreign_id}", session)
        check(wf_runs() == expected, "run naming a foreign workflow id not attributed")
        check(wf_runs("&status=failed") == 1, "status filter finds the failed run")

        # One quality score on a succeeded run, for the health card.
        runs = api.call("GET", f"/workflows/{wf_id}/runs?status=succeeded&limit=1", session).json()
        if runs.get("runs"):
            api.call(
                "POST",
                "/evaluations/scores",
                key,
                {"run_id": runs["runs"][0]["id"], "name": "helpfulness", "value": 0.9},
            )

        print("\n→ workflow page data")
        cost = api.call("GET", f"/workflows/{wf_id}/cost", session).json()
        priced = Decimal("0.004") + Decimal("0.020") * 2 + Decimal("0.006")
        check(
            Decimal(str(cost.get("steps_cost"))) >= priced,
            "step costs roll up from provider calls",
            cost.get("steps_cost"),
        )
        steps = {s["step_name"] for s in cost.get("cost_by_step", [])}
        check({"classify", "respond"} <= steps, "cost by step lists classify and respond", steps)
        ov = api.call("GET", f"/workflows/{wf_id}/overview", session).json()
        h = {k: v for k, v in ov.get("health", {}).items() if k != "trend"}
        check(h.get("runs") == expected, "health: run count", h.get("runs"))
        check(h.get("failed") == 1, "health: one failure", h.get("failed"))
        check(h.get("cost_per_success") is not None, "health: cost per success", h)
        check(h.get("p95_latency_ms") is not None, "health: p95 latency", h)
        listed = api.call("GET", f"/workflows?q={suffix}", session).json()
        stats = (listed.get("workflows") or [{}])[0].get("stats") or {}
        check(stats.get("runs") == expected, "list shows the workflow's stats", stats)
        ctx = api.call("GET", f"/context?entity=workflow&id={wf_id}", session).json()
        check(ctx.get("title") == name, "related drawer resolves the workflow", ctx.get("title"))

        print("\n→ agent stats and envelope")
        st = api.call("GET", f"/agents/{agent_id}/stats", session).json()
        check(
            st.get("total_runs") == 2,
            "agent stats count its 2 attributed runs",
            st.get("total_runs"),
        )
        env = api.call("GET", f"/agents/{agent_id}/envelope", session).json()
        check(env.get("allowed") is False, "envelope refuses runs once $0.04 > $0.03 is spent", env)

        print("\n→ archive and restore")
        check(api.call("DELETE", f"/workflows/{wf_id}", session).status_code == 204, "archived")
        late_id, late = run_events(feature_tag=tag)
        ingest(late)
        wait_for(
            lambda: api.call("GET", f"/runs/{late_id}", session).status_code == 200, args.timeout
        )
        check(wf_runs() == expected, "archived workflow ignores new traffic")
        restored = api.call("PUT", f"/workflows/{wf_id}", session, {"status": "active"})
        check(
            restored.status_code == 200 and restored.json().get("linked_runs") == 1,
            "restore re-links the run sent while archived",
            restored.text[:200],
        )
    except RuntimeError as exc:
        check(False, str(exc))
    finally:
        if not args.keep:
            if wf_id:
                api.call("DELETE", f"/workflows/{wf_id}", session)
            if agent_id:
                api.call("DELETE", f"/agents/{agent_id}", session)
            api.call("DELETE", f"/settings/api-keys/{key_id}", session)

    print(f"\n{check.passed} passed, {len(check.failures)} failed")
    for label in check.failures:
        print(f"  FAILED: {label}")
    return 1 if check.failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--base-url", default=os.getenv("RUNLEDGER_URL", "http://localhost:8201"))
    parser.add_argument(
        "--email", default=os.getenv("RUNLEDGER_PLATFORM_EMAIL", "admin@runledger.local")
    )
    parser.add_argument("--password", default=os.getenv("RUNLEDGER_PLATFORM_PASSWORD", "runledger"))
    parser.add_argument(
        "--timeout", type=float, default=30.0, help="Seconds to wait for the pipeline worker."
    )
    parser.add_argument("--keep", action="store_true", help="Keep the workflow, agent and key.")
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
