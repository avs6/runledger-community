"""
Shared helpers for RunLedger simulation scenarios.

Everything here talks to the RunLedger **REST API** — no direct database access — so a
simulation exercises the real ingest / gateway / budgets / outcomes paths exactly as a
client would. A scenario receives a ready `Sim` and creates one or more `Workspace`s,
then populates each with runs, routes, budgets, outcomes, scores, prompts, and alerts.

Design notes
------------
* Run ids are generated **client-side** so a scenario can attach outcomes and scores to
  the runs it just ingested (the ingest pipeline is async; ids don't come back from it).
* Every write is **best-effort**: a non-2xx warns and continues, so one unfamiliar
  endpoint never aborts a whole simulation.
* Costs are computed from a small pricing table so analytics/budgets show real numbers
  even when the underlying model is local (Ollama) and free.
"""

from __future__ import annotations

import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import yaml

# The simulation pricing catalog. Loaded from scripts/pricing.yaml so the cost of every
# ingested run matches the catalog that full_simulate imports into RunLedger — including
# your priced local Ollama models. Edit scripts/pricing.yaml to change either.
PRICING_FILE = Path(__file__).resolve().parent.parent / "pricing.yaml"

# (input $/1M, output $/1M) per model, and provider per model — built from the YAML.
PRICING: dict[str, tuple[float, float]] = {}
PROVIDER_OF: dict[str, str] = {}


def _load_pricing() -> None:
    """Populate PRICING / PROVIDER_OF from scripts/pricing.yaml (best-effort)."""
    try:
        doc = yaml.safe_load(PRICING_FILE.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001 — fall back to an empty catalog
        return
    for m in doc.get("models", []):
        if not isinstance(m, dict) or not m.get("model"):
            continue
        model = str(m["model"])
        PRICING[model] = (float(m.get("input_per_1m", 0.0)), float(m.get("output_per_1m", 0.0)))
        PROVIDER_OF[model] = str(m.get("provider", "openai"))


_load_pricing()

# ── console ──────────────────────────────────────────────────────────────────
_C = {"g": "\033[32m", "y": "\033[33m", "b": "\033[34m", "d": "\033[2m", "x": "\033[0m"}


def say(msg: str, c: str = "x") -> None:
    print(f"{_C.get(c, '')}{msg}{_C['x']}")


def _provider(model: str) -> str:
    return PROVIDER_OF.get(model, "openai")


def _cost(model: str, in_tok: int, out_tok: int) -> float:
    pin, pout = PRICING.get(model, (0.5, 1.5))
    return round(in_tok * pin / 1_000_000 + out_tok * pout / 1_000_000, 6)


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _ns(dt: datetime) -> str:
    return str(int(dt.timestamp() * 1_000_000_000))


@dataclass
class RunRef:
    """A run that was ingested — enough to attach outcomes / scores to it."""

    run_id: str
    model: str
    feature: str
    user: str
    cost: float
    success: bool


@dataclass
class Workspace:
    """A workspace handle with separate management and data-plane credentials."""

    sim: Sim
    org: str
    name: str
    key: str
    workspace_id: str
    admin_key: str = ""
    runs: list[RunRef] = field(default_factory=list)

    def _post(self, path: str, body: dict[str, Any], label: str) -> dict[str, Any]:
        return self.sim.post(path, body, key=self.key, label=label)

    def _manage_post(self, path: str, body: dict[str, Any], label: str) -> dict[str, Any]:
        return self.sim.post(path, body, key=self.admin_key or self.key, label=label)

    # ── runs ─────────────────────────────────────────────────────────────────
    def ingest_runs(
        self,
        n: int,
        *,
        models: list[str],
        features: list[str],
        users: list[str],
        days: int = 30,
        success_rate: float = 0.94,
        sessions: int = 0,
    ) -> list[RunRef]:
        """Ingest ``n`` synthetic runs spread over the last ``days`` and return them."""
        multiplier = max(1, int(getattr(self.sim, "traffic_multiplier", 1)))
        n = n * multiplier
        events: list[dict[str, Any]] = []
        made: list[RunRef] = []
        session_ids = [f"sess_{uuid.uuid4().hex[:8]}" for _ in range(sessions)]
        now = datetime.now(UTC)
        for _ in range(n):
            model = random.choice(models)
            feature = random.choice(features)
            user = random.choice(users)
            in_tok = random.randint(300, 6000)
            out_tok = random.randint(150, 2200)
            success = random.random() < success_rate
            latency = random.randint(300, 4000)
            cost = _cost(model, in_tok, out_tok)
            run_id, span_id = str(uuid.uuid4()), str(uuid.uuid4())
            start = now - timedelta(days=random.uniform(0, days), hours=random.uniform(0, 23))
            end = start + timedelta(milliseconds=latency)
            ts_s = start.isoformat().replace("+00:00", "Z")
            ts_e = end.isoformat().replace("+00:00", "Z")
            pc_status = "success" if success else "error"
            end_status = "succeeded" if success else "failed"
            run_start: dict[str, Any] = {
                "event_type": "run_start",
                "run_id": run_id,
                "started_at": ts_s,
                "end_user_id": user,
                "feature_tag": feature,
                "agent_name": feature,
            }
            if session_ids:
                run_start["session_id"] = random.choice(session_ids)
            events += [
                run_start,
                {
                    "event_type": "span_start",
                    "span_id": span_id,
                    "run_id": run_id,
                    "span_type": "llm",
                    "name": "llm-call",
                    "started_at": ts_s,
                },
                {
                    "event_type": "provider_call",
                    "run_id": run_id,
                    "span_id": span_id,
                    "provider": _provider(model),
                    "model": model,
                    "input_tokens": in_tok,
                    "output_tokens": out_tok,
                    "latency_ms": latency,
                    "cost_usd": cost,
                    "status": pc_status,
                },
                {
                    "event_type": "span_end",
                    "span_id": span_id,
                    "run_id": run_id,
                    "status": end_status,
                    "ended_at": ts_e,
                    "cost_usd": cost,
                },
                {
                    "event_type": "run_end",
                    "run_id": run_id,
                    "status": end_status,
                    "ended_at": ts_e,
                    "total_cost_usd": cost,
                    "total_input_tokens": in_tok,
                    "total_output_tokens": out_tok,
                },
            ]
            made.append(RunRef(run_id, model, feature, user, cost, success))
        self.sim.post(
            "/ingest/v1/batch",
            {"events": events},
            key=self.key,
            label=f"ingest {n} runs",
            expect=(202, 200),
        )
        self.runs.extend(made)
        say(f"    · {n} runs ingested", "d")
        return made

    def ingest_rich_runs(
        self,
        n: int,
        *,
        models: list[str],
        workflows: list[dict[str, Any]],
        users: list[str],
        days: int = 7,
        success_rate: float = 0.94,
        sessions: int = 80,
        batch_runs: int = 120,
    ) -> list[RunRef]:
        """Ingest dense, dashboard-friendly traffic with agents, tools, skills, cache, and outcomes."""
        multiplier = max(1, int(getattr(self.sim, "traffic_multiplier", 1)))
        total = n * multiplier
        made: list[RunRef] = []
        session_ids = [f"{self.name.lower().replace(' ', '-')}-{i:04d}" for i in range(1, sessions + 1)]
        now = datetime.now(UTC)

        for batch_start in range(0, total, batch_runs):
            events: list[dict[str, Any]] = []
            for _ in range(batch_start, min(batch_start + batch_runs, total)):
                workflow = random.choice(workflows)
                model = random.choice(models)
                user = random.choice(users)
                in_tok = random.randint(180, 3200)
                out_tok = random.randint(60, 1800)
                cached = random.randint(35, max(40, in_tok // 2)) if random.random() < workflow.get("cache_rate", 0.2) else 0
                success = random.random() < success_rate
                latency = random.randint(220, 4600)
                billable_in = max(0, in_tok - cached)
                cost = _cost(model, billable_in, out_tok) + (_cost(model, cached, 0) * 0.15 if cached else 0)
                run_id, span_id = str(uuid.uuid4()), str(uuid.uuid4())
                start = now - timedelta(days=random.uniform(0, days), minutes=random.uniform(0, 1440))
                end = start + timedelta(milliseconds=latency)
                ts_s, ts_e = _iso(start), _iso(end)
                pc_status = "success" if success else "error"
                end_status = "succeeded" if success else "failed"
                deployment_version = workflow.get("deployment_version") or f"{workflow['prompt_name']}:1"

                events += [
                    {
                        "event_type": "run_start",
                        "run_id": run_id,
                        "started_at": ts_s,
                        "end_user_id": user,
                        "session_id": random.choice(session_ids),
                        "feature_tag": workflow["feature"],
                        "deployment_version": deployment_version,
                        "metadata": {
                            "agent_name": workflow["agent"],
                            "skill": workflow["skill"],
                            "team": workflow.get("team", "Support"),
                            "application": workflow.get("application", self.name),
                            "route_alias": workflow.get("route", "local-routing"),
                            "intent": workflow["feature"].replace("-", " "),
                        },
                    },
                    {
                        "event_type": "span_start",
                        "span_id": span_id,
                        "run_id": run_id,
                        "span_type": "agent",
                        "name": workflow["agent"],
                        "started_at": ts_s,
                    },
                    {
                        "event_type": "provider_call",
                        "run_id": run_id,
                        "span_id": span_id,
                        "provider": _provider(model),
                        "model": model,
                        "input_tokens": in_tok,
                        "output_tokens": out_tok,
                        "cached_input_tokens": cached,
                        "latency_ms": latency,
                        "cost_usd": round(cost, 8),
                        "status": pc_status,
                        "error_type": None if success else random.choice(["timeout", "tool_error", "provider_error"]),
                    },
                    {
                        "event_type": "tool_call",
                        "run_id": run_id,
                        "span_id": span_id,
                        "tool_name": workflow["tool"],
                        "tool_type": workflow.get("tool_type", "read"),
                        "risk_score": random.randint(1, 55 if success else 85),
                        "duration_ms": random.randint(60, 1400),
                        "status": pc_status,
                    },
                    {
                        "event_type": "span_end",
                        "span_id": span_id,
                        "run_id": run_id,
                        "status": end_status,
                        "ended_at": ts_e,
                        "cost_usd": round(cost, 8),
                        "metadata": {
                            "selected_model": model,
                            "route_alias": workflow.get("route", "local-routing"),
                            "workflow_agent": workflow["agent"],
                            "skill": workflow["skill"],
                        },
                    },
                    {
                        "event_type": "outcome",
                        "run_id": run_id,
                        "outcome_type": workflow.get("outcome_type", "resolved"),
                        "success": success and random.random() > 0.08,
                        "labels": {
                            "team": workflow.get("team", "Support"),
                            "model": model,
                            "route": workflow.get("route", "local-routing"),
                        },
                    },
                    {
                        "event_type": "run_end",
                        "run_id": run_id,
                        "status": end_status,
                        "ended_at": ts_e,
                        "total_cost_usd": round(cost, 8),
                        "total_input_tokens": in_tok,
                        "total_output_tokens": out_tok,
                    },
                ]
                made.append(RunRef(run_id, model, workflow["feature"], user, cost, success))

            self.sim.post(
                "/ingest/v1/batch",
                {"events": events},
                key=self.key,
                label=f"ingest {len(events)} rich events",
                expect=(202, 200),
            )
        self.runs.extend(made)
        say(f"    · {len(made)} rich runs ingested", "d")
        return made

    def ingest_otlp_traces(self, n: int, *, models: list[str], workflows: list[dict[str, Any]]) -> None:
        """Send OpenTelemetry GenAI/OpenInference-style trace JSON to the OTLP receiver."""
        multiplier = max(1, int(getattr(self.sim, "traffic_multiplier", 1)))
        total = n * multiplier
        now = datetime.now(UTC)
        resource_spans: list[dict[str, Any]] = []
        for _ in range(total):
            workflow = random.choice(workflows)
            model = random.choice(models)
            trace_id = uuid.uuid4().hex
            agent_span = uuid.uuid4().hex[:16]
            llm_span = uuid.uuid4().hex[:16]
            tool_span = uuid.uuid4().hex[:16]
            start = now - timedelta(hours=random.uniform(0, 24))
            llm_start = start + timedelta(milliseconds=80)
            tool_start = start + timedelta(milliseconds=random.randint(220, 700))
            end = start + timedelta(milliseconds=random.randint(900, 5200))
            in_tok = random.randint(250, 2800)
            out_tok = random.randint(80, 1400)
            cost = _cost(model, in_tok, out_tok)

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

            resource_spans.append({
                "resource": {
                    "attributes": [
                        attr("service.name", self.name),
                        attr("team", workflow.get("team", "Support")),
                        attr("application", workflow.get("application", self.name)),
                    ]
                },
                "scopeSpans": [
                    {
                        "scope": {"name": "runledger-simulator", "version": "1.0"},
                        "spans": [
                            {
                                "traceId": trace_id,
                                "spanId": agent_span,
                                "name": workflow["agent"],
                                "kind": 1,
                                "startTimeUnixNano": _ns(start),
                                "endTimeUnixNano": _ns(end),
                                "attributes": [
                                    attr("openinference.span.kind", "AGENT"),
                                    attr("agent_name", workflow["agent"]),
                                    attr("skill", workflow["skill"]),
                                    attr("feature_tag", workflow["feature"]),
                                    attr("session.id", f"otlp-{random.randint(1, 80):03d}"),
                                ],
                                "status": {"code": "STATUS_CODE_OK"},
                            },
                            {
                                "traceId": trace_id,
                                "spanId": llm_span,
                                "parentSpanId": agent_span,
                                "name": f"chat {model}",
                                "kind": 3,
                                "startTimeUnixNano": _ns(llm_start),
                                "endTimeUnixNano": _ns(end),
                                "attributes": [
                                    attr("openinference.span.kind", "LLM"),
                                    attr("gen_ai.system", _provider(model)),
                                    attr("gen_ai.request.model", model),
                                    attr("gen_ai.usage.input_tokens", in_tok),
                                    attr("gen_ai.usage.output_tokens", out_tok),
                                    attr("llm.cost.total", cost),
                                ],
                                "status": {"code": "STATUS_CODE_OK"},
                            },
                            {
                                "traceId": trace_id,
                                "spanId": tool_span,
                                "parentSpanId": agent_span,
                                "name": workflow["tool"],
                                "kind": 1,
                                "startTimeUnixNano": _ns(tool_start),
                                "endTimeUnixNano": _ns(end),
                                "attributes": [
                                    attr("openinference.span.kind", "TOOL"),
                                    attr("tool.name", workflow["tool"]),
                                    attr("tool.risk_score", random.randint(1, 60)),
                                ],
                                "status": {"code": "STATUS_CODE_OK"},
                            },
                        ],
                    }
                ],
            })

        self.sim.post(
            "/v1/traces",
            {"resourceSpans": resource_spans},
            key=self.key,
            label=f"otlp {total} traces",
            expect=(200,),
        )
        say(f"    · {total} OTLP traces sent", "d")

    def seed_prompt_eval_assets(self, *, prompts: list[dict[str, Any]], dataset_name: str, models: list[str]) -> None:
        """Create prompt versions, eval dataset, and experiment records through the API."""
        prompt_version: int | None = None
        prompt_name = prompts[0]["name"] if prompts else None
        for prompt in prompts:
            created = self._post(
                "/prompts",
                {
                    "name": prompt["name"],
                    "description": prompt.get("description"),
                    "default_environment": prompt.get("environment", "production"),
                },
                f"prompt {prompt['name']}",
            )
            if not created:
                self.sim.get(f"/prompts/{prompt['name']}", key=self.key)
            for version in prompt.get("versions", []):
                response = self._post(
                    f"/prompts/{prompt['name']}/versions",
                    {
                        "content": version["content"],
                        "variables": version.get("variables", []),
                        "commit_message": version.get("commit_message", "Simulator seed"),
                        "environment": version.get("environment", "production"),
                        "model_hint": version.get("model_hint"),
                    },
                    f"prompt version {prompt['name']}",
                )
                if prompt["name"] == prompt_name and response.get("version"):
                    prompt_version = int(response["version"])

        dataset = self._post(
            "/datasets",
            {
                "name": dataset_name,
                "description": "Simulator-seeded evaluation set for local agent quality checks.",
                "source": "simulator",
                "items": [
                    {
                        "input": "Customer asks why a refund has not arrived.",
                        "expected_output": "Explain refund timeline and next step clearly.",
                        "metadata": {"intent": "refund-policy", "difficulty": "medium"},
                    },
                    {
                        "input": "Customer reports duplicate billing after plan upgrade.",
                        "expected_output": "Acknowledge issue, inspect invoice, and offer escalation path.",
                        "metadata": {"intent": "billing-help", "difficulty": "hard"},
                    },
                    {
                        "input": "Customer needs a concise setup answer from the help center.",
                        "expected_output": "Return a short answer with article reference.",
                        "metadata": {"intent": "faq-answer", "difficulty": "easy"},
                    },
                    {
                        "input": "Angry customer says the bot is not helping.",
                        "expected_output": "Detect sentiment, apologize, and route appropriately.",
                        "metadata": {"intent": "sentiment-routing", "difficulty": "hard"},
                    },
                ],
            },
            f"dataset {dataset_name}",
        )
        dataset_id = dataset.get("id")
        experiment = self._post(
            "/experiments",
            {
                "name": f"{dataset_name} - local model bakeoff",
                "description": "Compare local Ollama models for support quality, cost, and latency.",
                "dataset_id": dataset_id,
                "prompt_name": prompt_name,
                "prompt_version": prompt_version,
                "models": [
                    {"model": model, "provider": _provider(model), "label": model.replace(":latest", "")}
                    for model in models[:5]
                ],
            },
            f"experiment {dataset_name}",
        )
        if experiment.get("id"):
            self.sim.post(
                f"/experiments/{experiment['id']}/run",
                {},
                key=self.key,
                label=f"run experiment {dataset_name}",
                expect=(200, 409, 422),
            )

    def sample(self, runs: list[RunRef], k: int = 60) -> list[RunRef]:
        """A random subset of runs — keeps per-run scores/outcomes under the API's
        management rate limit (60/min) so a scenario seeds quickly."""
        return random.sample(runs, min(k, len(runs)))

    # ── gateway ──────────────────────────────────────────────────────────────
    def add_route(self, alias: str, model: str, *, priority: int = 10, **flags: Any) -> None:
        body = {
            "alias": alias,
            "provider": _provider(model),
            "target_model": model,
            "priority": priority,
            **flags,
        }
        self._manage_post("/gateway/routes", body, f"route {alias}→{model}")

    # ── finops ───────────────────────────────────────────────────────────────
    def add_budget(
        self,
        scope_type: str,
        limit_usd: float,
        *,
        period_type: str = "monthly",
        action: str = "notify",
        scope_id: str | None = None,
    ) -> None:
        body: dict[str, Any] = {
            "scope_type": scope_type,
            "period_type": period_type,
            "limit_usd": limit_usd,
            "action": action,
        }
        if scope_id:
            body["scope_id"] = scope_id
        # /budgets requires a workspace-admin user session; org admins are also workspace
        # admins for their default workspace, so the simulator uses the dashboard session.
        self.sim.post(
            "/budgets",
            body,
            key=self.admin_key or self.key,
            label=f"budget {scope_type}",
            expect=(200, 201, 401, 403),
        )

    def record_outcome(
        self,
        run: RunRef,
        outcome_type: str,
        *,
        success: bool = True,
        value_usd: float | None = None,
        labels: dict[str, Any] | None = None,
    ) -> None:
        body: dict[str, Any] = {
            "outcome_type": outcome_type,
            "success": success,
            "run_id": run.run_id,
            "end_user_id": run.user,
            "labels": labels or {},
        }
        if value_usd is not None:
            body["value_usd"] = value_usd
        self._post("/outcomes", body, f"outcome {outcome_type}")

    def score(self, run: RunRef, metric_name: str, value: float, label: str | None = None) -> None:
        # /evaluations/scores expects ScoreCreate: {run_id, name, value, source, label}.
        body: dict[str, Any] = {
            "run_id": run.run_id,
            "name": metric_name,
            "value": value,
            "source": "human",
        }
        if label:
            body["label"] = label
        self._post("/evaluations/scores", body, f"score {metric_name}={value}")

    # ── quality / governance (best-effort) ───────────────────────────────────
    def add_alert(self, name: str, metric: str, operator: str, threshold: float) -> None:
        self._manage_post(
            "/alerts/rules",
            {"name": name, "metric": metric, "operator": operator, "threshold": threshold},
            f"alert {name}",
        )

    def create_approval_request(
        self,
        request_type: str,
        reason: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"request_type": request_type, "reason": reason}
        if metadata:
            body["metadata"] = metadata
        return self.sim.post(
            "/approvals",
            body,
            key=self.admin_key or self.key,
            label=f"approval {request_type}",
            expect=(200, 201, 401, 403),
        )

    def add_auto_approval_policy(
        self,
        request_type: str,
        *,
        max_amount: float | None = None,
        conditions: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"request_type": request_type}
        if max_amount is not None:
            body["max_amount"] = max_amount
        if conditions:
            body["conditions"] = conditions
        return self.sim.post(
            "/approvals/auto-policies",
            body,
            key=self.admin_key or self.key,
            label=f"auto-approval {request_type}",
            expect=(200, 201, 401, 403),
        )

    def add_chargeback_rule(
        self,
        name: str,
        match_field: str,
        match_value: str,
        cost_center: str,
        *,
        split_percent: float = 100.0,
    ) -> dict[str, Any]:
        return self.sim.post(
            "/billing/chargeback-rules",
            {
                "name": name,
                "match_field": match_field,
                "match_value": match_value,
                "cost_center": cost_center,
                "split_percent": split_percent,
            },
            key=self.admin_key or self.key,
            label=f"chargeback rule {name}",
            expect=(200, 201, 401, 403),
        )

    def generate_runbook(self, run: RunRef) -> dict[str, Any]:
        return self.sim.post(
            f"/runs/{run.run_id}/runbook",
            {},
            key=self.key,
            label=f"runbook for {run.run_id[:8]}",
            expect=(200, 201, 404, 422),
        )

    def create_route_recommendation(
        self,
        experiment_id: str,
        config_index: int,
        reason: str,
    ) -> dict[str, Any]:
        return self.sim.post(
            "/gateway/route-recommendations",
            {
                "experiment_id": experiment_id,
                "config_index": config_index,
                "reason": reason,
            },
            key=self.admin_key or self.key,
            label=f"route recommendation",
            expect=(200, 201, 401, 403, 404, 422),
        )

    def get_governance_audit_pack(self) -> dict[str, Any]:
        return self.sim.get(
            "/governance/audit-pack",
            key=self.admin_key or self.key,
        ) or {}

    # ── Phase 14: Guardrails ─────────────────────────────────────────────────

    def create_guardrail_rule(
        self,
        name: str,
        mode: str = "pre_call",
        rule_type: str = "custom",
        logic: str | None = None,
        config: dict[str, Any] | None = None,
        severity: str = "medium",
        priority: int = 100,
        status: str = "active",
        template_id: str | None = None,
        description: str | None = None,
        skip_system_messages: bool = False,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "name": name,
            "mode": mode,
            "rule_type": rule_type,
            "severity": severity,
            "priority": priority,
            "status": status,
            "skip_system_messages": skip_system_messages,
        }
        if logic:
            body["logic"] = logic
        if config:
            body["config"] = config
        if template_id:
            body["template_id"] = template_id
        if description:
            body["description"] = description
        return self._manage_post("/guardrails", body, f"guardrail rule '{name}'")

    def activate_content_filters(
        self,
        filters: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return self.sim.put(
            "/guardrails/filters",
            {"filters": filters},
            key=self.admin_key or self.key,
            label="content filters",
        )

    def create_partner_guardrail(
        self,
        provider: str,
        name: str,
        mode: str = "pre_call",
        endpoint_url: str | None = None,
        config: dict[str, Any] | None = None,
        timeout_ms: int = 2000,
        fallback_action: str = "allow",
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "provider": provider,
            "name": name,
            "mode": mode,
            "timeout_ms": timeout_ms,
            "fallback_action": fallback_action,
        }
        if endpoint_url:
            body["endpoint_url"] = endpoint_url
        if config:
            body["config"] = config
        return self._manage_post("/guardrails/partners", body, f"partner guardrail '{name}'")

    def test_guardrail(
        self,
        guardrail_id: str,
        texts: list[str],
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"texts": texts}
        if metadata:
            body["metadata"] = metadata
        return self._manage_post(
            f"/guardrails/{guardrail_id}/test",
            body,
            "guardrail test",
        )

    def test_all_guardrails(
        self,
        texts: list[str],
        model: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"texts": texts}
        if model:
            body["model"] = model
        if metadata:
            body["metadata"] = metadata
        return self._manage_post("/guardrails/test", body, "guardrails test all")

    def create_guardrail_test_case(
        self,
        guardrail_rule_id: str,
        name: str,
        input_text: str,
        expected_decision: str,
        input_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "guardrail_rule_id": guardrail_rule_id,
            "name": name,
            "input_text": input_text,
            "expected_decision": expected_decision,
        }
        if input_metadata:
            body["input_metadata"] = input_metadata
        return self._manage_post("/guardrails/test-cases", body, f"test case '{name}'")

    def run_guardrail_regression(self, guardrail_id: str) -> dict[str, Any]:
        return self._manage_post(
            f"/guardrails/{guardrail_id}/regression",
            {},
            "guardrail regression",
        )

    def get_guardrail_stats(self, hours: int = 24) -> dict[str, Any]:
        return self.sim.get(
            f"/guardrails/stats?hours={hours}",
            key=self.admin_key or self.key,
        ) or {}

    def list_guardrail_events(self, limit: int = 20) -> dict[str, Any]:
        return self.sim.get(
            f"/guardrails/events?limit={limit}",
            key=self.admin_key or self.key,
        ) or {}

    def submit_guardrail_feedback(
        self,
        event_id: str,
        is_false_positive: bool = True,
        reason: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"is_false_positive": is_false_positive}
        if reason:
            body["reason"] = reason
        return self._manage_post(
            f"/guardrails/events/{event_id}/feedback",
            body,
            "guardrail feedback",
        )

    def evaluate_guardrail_alerts(
        self,
        window_hours: int = 1,
        baseline_hours: int = 24,
    ) -> list[dict[str, Any]]:
        return self._manage_post(
            f"/guardrails/alerts/evaluate?window_hours={window_hours}&baseline_hours={baseline_hours}",
            {},
            "guardrail alert evaluation",
        )

    def list_guardrail_alerts(
        self,
        alert_type: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        params = f"?limit={limit}"
        if alert_type:
            params += f"&alert_type={alert_type}"
        if status:
            params += f"&status={status}"
        return self.sim.get(
            f"/guardrails/alerts{params}",
            key=self.admin_key or self.key,
        ) or {}

    def acknowledge_guardrail_alert(self, alert_id: str) -> dict[str, Any]:
        return self._manage_post(
            f"/guardrails/alerts/{alert_id}/acknowledge",
            {},
            "guardrail alert acknowledge",
        )

    # ── ML Intelligence helpers ─────────────────────────────────────────

    def list_anomalies(
        self,
        anomaly_type: str | None = None,
        severity: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit}
        if anomaly_type:
            params["anomaly_type"] = anomaly_type
        if severity:
            params["severity"] = severity
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        return self._analytics_get(f"/intelligence/anomalies?{qs}", "list anomalies")

    def get_anomaly_summary(self, hours: int = 24) -> dict[str, Any]:
        return self._analytics_get(f"/intelligence/anomalies/summary?hours={hours}", "anomaly summary")

    def acknowledge_anomaly(self, anomaly_id: str) -> dict[str, Any]:
        return self._manage_post(f"/intelligence/anomalies/{anomaly_id}/acknowledge", {}, "acknowledge anomaly")

    def get_cost_forecast(self) -> dict[str, Any]:
        return self._analytics_get("/intelligence/forecasts/cost", "cost forecast")

    def get_token_forecast(self) -> dict[str, Any]:
        return self._analytics_get("/intelligence/forecasts/tokens", "token forecast")

    def generate_forecast(
        self,
        forecast_type: str = "cost_daily",
        horizon_days: int = 14,
        dimension_key: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"forecast_type": forecast_type, "horizon_days": horizon_days}
        if dimension_key:
            body["dimension_key"] = dimension_key
        return self._manage_post("/intelligence/forecasts/generate", body, "generate forecast")

    def get_top_k(
        self,
        dimension: str = "model",
        metric: str = "cost",
        k: int = 10,
    ) -> dict[str, Any]:
        return self._analytics_get(
            f"/intelligence/top-k?dimension={dimension}&metric={metric}&k={k}",
            f"top-k {dimension}/{metric}",
        )

    def list_patterns(self, dimension: str | None = None) -> dict[str, Any]:
        qs = f"?dimension={dimension}" if dimension else ""
        return self._analytics_get(f"/intelligence/patterns{qs}", "list patterns")

    def get_cost_per_outcome(self) -> dict[str, Any]:
        return self._analytics_get("/intelligence/cost-per-outcome", "cost per outcome")

    def retrain_complexity(self) -> dict[str, Any]:
        return self._manage_post("/intelligence/complexity/retrain", {}, "retrain complexity")

    def get_complexity_scores(self, hours: int = 24) -> dict[str, Any]:
        return self._analytics_get(f"/intelligence/complexity/scores?hours={hours}", "complexity scores")

    def get_feature_importances(self) -> dict[str, Any]:
        return self._analytics_get("/intelligence/complexity/importances", "feature importances")

    def get_adaptive_suggestions(self) -> dict[str, Any]:
        return self._analytics_get("/intelligence/alerts/adaptive-suggestions", "adaptive suggestions")

    def enable_adaptive_alert(self, rule_id: str) -> dict[str, Any]:
        return self._manage_post(f"/intelligence/alerts/{rule_id}/enable-adaptive", {}, "enable adaptive")

    def get_ml_dashboard(self) -> dict[str, Any]:
        return self._analytics_get("/intelligence/dashboard", "ML dashboard")

    def list_ml_models(self) -> dict[str, Any]:
        return self._analytics_get("/intelligence/models", "ML models")

    # ── Advanced Budget Engine helpers ──────────────────────────────────

    def create_budget_tier(
        self,
        name: str,
        *,
        max_spend_usd: float | None = None,
        period_type: str = "monthly",
        rpm_limit: int | None = None,
        tpm_limit: int | None = None,
        allowed_models: list[str] | None = None,
        is_default: bool = False,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"name": name, "period_type": period_type, "is_default": is_default}
        if max_spend_usd is not None:
            body["max_spend_usd"] = max_spend_usd
        if rpm_limit is not None:
            body["rpm_limit"] = rpm_limit
        if tpm_limit is not None:
            body["tpm_limit"] = tpm_limit
        if allowed_models:
            body["allowed_models"] = allowed_models
        return self._manage_post("/budget-tiers", body, f"budget tier '{name}'")

    def assign_tier_to_key(self, key_id: str, tier_id: str | None = None) -> dict[str, Any]:
        qs = f"?tier_id={tier_id}" if tier_id else ""
        return self.sim.put(
            f"/budget-tiers/assign/{key_id}{qs}",
            {},
            key=self.admin_key or self.key,
            label=f"assign tier to key",
        )

    def create_model_budget(
        self,
        key_id: str,
        model_pattern: str,
        *,
        max_spend_usd: float | None = None,
        period_type: str = "monthly",
        rpm_limit: int | None = None,
        tpm_limit: int | None = None,
        action: str = "notify",
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"model_pattern": model_pattern, "period_type": period_type, "action": action}
        if max_spend_usd is not None:
            body["max_spend_usd"] = max_spend_usd
        if rpm_limit is not None:
            body["rpm_limit"] = rpm_limit
        if tpm_limit is not None:
            body["tpm_limit"] = tpm_limit
        return self._manage_post(f"/api-keys/{key_id}/model-budgets", body, f"model budget '{model_pattern}'")

    def create_budget_override(
        self,
        budget_id: str,
        override_limit_usd: float,
        starts_at: str,
        expires_at: str,
        *,
        reason: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "override_limit_usd": override_limit_usd,
            "starts_at": starts_at,
            "expires_at": expires_at,
        }
        if reason:
            body["reason"] = reason
        return self._manage_post(f"/budgets/{budget_id}/override", body, "budget override")

    def list_budget_overrides(self, budget_id: str) -> dict[str, Any]:
        return self.sim.get(
            f"/budgets/{budget_id}/overrides",
            key=self.admin_key or self.key,
        ) or {}

    def revoke_budget_override(self, budget_id: str, override_id: str) -> dict[str, Any]:
        return self._manage_post(
            f"/budgets/{budget_id}/override/{override_id}/revoke",
            {},
            "revoke override",
        )

    def get_billing_summary(self, months: int = 3) -> dict[str, Any]:
        return self.sim.get(
            f"/budgets/billing-summary?months={months}",
            key=self.admin_key or self.key,
        ) or {}


class Sim:
    """Platform-level client: bootstrap the admin, then mint per-scenario workspaces."""

    def __init__(self, base_url: str, admin_secret: str, *, traffic_multiplier: int = 1) -> None:
        self.base = base_url.rstrip("/")
        self.admin_secret = admin_secret
        self.traffic_multiplier = max(1, traffic_multiplier)
        self.http = httpx.Client(timeout=60, follow_redirects=True)
        self.platform_key: str | None = None
        self.platform_email: str | None = None
        self.platform_password: str | None = None
        self.workspaces: list[Workspace] = []

    # ── low-level ────────────────────────────────────────────────────────────
    def post(
        self,
        path: str,
        body: dict[str, Any],
        *,
        key: str | None = None,
        admin: bool = False,
        label: str = "",
        expect: tuple[int, ...] = (200, 201, 202, 204),
    ) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        if admin:
            headers["X-Admin-Secret"] = self.admin_secret
        # Management endpoints are rate-limited (60/min per key); retry on 429 by waiting
        # out the sliding window so bulk seeding completes instead of dropping writes.
        for attempt in range(8):
            try:
                r = self.http.post(f"{self.base}{path}", json=body, headers=headers)
            except Exception as exc:  # noqa: BLE001
                say(f"    ! {label or path}: {exc}", "y")
                return {}
            if r.status_code == 429:
                time.sleep(float(r.headers.get("Retry-After", 0)) or (2 + attempt * 2))
                continue
            if r.status_code not in expect:
                say(f"    ! {label or path}: {r.status_code} {r.text[:120]}", "y")
                return {}
            return r.json() if r.status_code != 204 and r.content else {}
        say(f"    ! {label or path}: still rate-limited after retries", "y")
        return {}

    def get(self, path: str, *, key: str | None = None, admin: bool = False) -> Any:
        headers: dict[str, str] = {}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        if admin:
            headers["X-Admin-Secret"] = self.admin_secret
        try:
            r = self.http.get(f"{self.base}{path}", headers=headers)
            return r.json() if r.status_code == 200 and r.content else None
        except Exception:  # noqa: BLE001
            return None

    def put(
        self,
        path: str,
        body: dict[str, Any],
        *,
        key: str | None = None,
        label: str = "",
        expect: tuple[int, ...] = (200, 201, 202, 204),
    ) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        try:
            r = self.http.put(f"{self.base}{path}", json=body, headers=headers)
        except Exception as exc:  # noqa: BLE001
            say(f"    ! {label or path}: {exc}", "y")
            return {}
        if r.status_code not in expect:
            say(f"    ! {label or path}: {r.status_code} {r.text[:120]}", "y")
            return {}
        return r.json() if r.status_code != 204 and r.content else {}

    def _login(self, email: str, password: str, workspace_id: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"email": email, "password": password}
        if workspace_id:
            body["workspace_id"] = workspace_id
        return self.post("/auth/login", body, label=f"login {email}", expect=(200,))

    def _switch_workspace(self, key: str, workspace_id: str) -> dict[str, Any]:
        return self.post(
            "/auth/switch-workspace",
            {"workspace_id": workspace_id},
            key=key,
            label=f"switch workspace {workspace_id}",
            expect=(200,),
        )

    def wait_healthy(self, timeout: float = 120) -> None:
        say(f"→ waiting for {self.base} …", "b")
        deadline = datetime.now(UTC) + timedelta(seconds=timeout)
        while datetime.now(UTC) < deadline:
            try:
                if self.http.get(f"{self.base}/health/ready").status_code == 200:
                    say("  ✓ API ready", "g")
                    return
            except Exception:  # noqa: BLE001
                pass
            import time

            time.sleep(2)
        raise SystemExit(f"API at {self.base} not ready after {timeout}s")

    # ── bootstrap / orgs ─────────────────────────────────────────────────────
    def bootstrap(self, email: str, password: str, org_name: str) -> None:
        data = self.post(
            "/admin/bootstrap",
            {
                "email": email,
                "password": password,
                "full_name": "Platform Admin",
                "org_name": org_name,
            },
            admin=True,
            label="bootstrap",
            expect=(200, 201),
        )
        self.platform_email = email
        self.platform_password = password
        self.platform_key = self._login(email, password).get("api_key") or data.get("api_key")
        if not self.platform_key:
            raise SystemExit("bootstrap failed - no dashboard session api_key returned")
        say(f"  ✓ platform admin bootstrapped ({email})", "g")

    def workspace(self, org: str, name: str, *, plan: str = "growth") -> Workspace:
        """Create an org, log in as its org admin, and mint a workspace API key."""
        slug = org.lower().replace(" ", "-")
        admin_email = f"admin@{slug}.example.com"
        admin_password = "Sim-Passw0rd!"
        tenant = self.post(
            "/org/tenants",
            {
                "name": org,
                "admin_email": admin_email,
                "admin_password": admin_password,
                "admin_full_name": f"{org} Admin",
                "skip_verification": True,
            },
            key=self.platform_key,
            label=f"org {org}",
        )
        tenant_id = tenant.get("id")
        if not tenant_id:
            listing = self.get("/org/tenants", key=self.platform_key) or []
            rows = listing if isinstance(listing, list) else listing.get("items", [])
            tenant_id = next((t.get("id") for t in rows if t.get("name") == org), None)
        if tenant_id:
            self.put(
                f"/org/tenants/{tenant_id}",
                {"plan": plan},
                key=self.platform_key,
                label=f"org plan {org}",
                expect=(200,),
            )

        key, ws_id, org_admin_key = "", "", ""
        login = self._login(admin_email, admin_password)
        org_admin_key = login.get("api_key", "")
        ws_id = login.get("workspace_id", "")
        if org_admin_key and ws_id:
            self.put(
                f"/org/workspaces/{ws_id}",
                {"name": name},
                key=org_admin_key,
                label=f"workspace rename {org}/{name}",
                expect=(200, 409),
            )
            resp = self.post(
                "/settings/api-keys",
                {"name": "sim", "workspace_id": ws_id},
                key=org_admin_key,
                label=f"key {org}",
            )
            key = resp.get("key", "")

        if not tenant_id:
            say(f"  ! could not create or find org {org}; scenario data may be incomplete", "y")
        if not key:
            say(f"  ! could not obtain key for {org}; scenario data will be skipped", "y")
        ws = Workspace(self, org, name, key, ws_id, org_admin_key)
        self.workspaces.append(ws)
        say(f"  âœ“ {org} / {name}", "g")
        return ws

    def close(self) -> None:
        self.http.close()
