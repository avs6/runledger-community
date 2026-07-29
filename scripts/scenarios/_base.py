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
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

# (input $/1M, output $/1M) — enough to make analytics realistic.
PRICING: dict[str, tuple[float, float]] = {
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "o1": (15.00, 60.00),
    "claude-opus-4": (15.00, 75.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-haiku-4-5": (0.80, 4.00),
    "gemini-1.5-pro": (1.25, 5.00),
    "llama3.1:8b": (0.0, 0.0),
    "llama3.2": (0.0, 0.0),
    "llama3.2:3b": (0.0, 0.0),
    "mistral-large": (2.00, 6.00),
}

PROVIDER_OF: dict[str, str] = {
    "gpt-4o": "openai", "gpt-4o-mini": "openai", "o1": "openai",
    "claude-opus-4": "anthropic", "claude-sonnet-4-6": "anthropic", "claude-haiku-4-5": "anthropic",
    "gemini-1.5-pro": "google",
    "llama3.1:8b": "ollama", "llama3.2": "ollama", "llama3.2:3b": "ollama",
    "mistral-large": "mistral",
}

# ── console ──────────────────────────────────────────────────────────────────
_C = {"g": "\033[32m", "y": "\033[33m", "b": "\033[34m", "d": "\033[2m", "x": "\033[0m"}


def say(msg: str, c: str = "x") -> None:
    print(f"{_C.get(c, '')}{msg}{_C['x']}")


def _provider(model: str) -> str:
    return PROVIDER_OF.get(model, "openai")


def _cost(model: str, in_tok: int, out_tok: int) -> float:
    pin, pout = PRICING.get(model, (0.5, 1.5))
    return round(in_tok * pin / 1_000_000 + out_tok * pout / 1_000_000, 6)


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
    """A workspace handle scoped to one API key, with data-population helpers."""

    sim: Sim
    org: str
    name: str
    key: str
    workspace_id: str
    runs: list[RunRef] = field(default_factory=list)

    def _post(self, path: str, body: dict[str, Any], label: str) -> dict[str, Any]:
        return self.sim.post(path, body, key=self.key, label=label)

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
            start = now - timedelta(
                days=random.uniform(0, days), hours=random.uniform(0, 23)
            )
            end = start + timedelta(milliseconds=latency)
            ts_s = start.isoformat().replace("+00:00", "Z")
            ts_e = end.isoformat().replace("+00:00", "Z")
            pc_status = "success" if success else "error"
            end_status = "succeeded" if success else "failed"
            run_start: dict[str, Any] = {
                "event_type": "run_start", "run_id": run_id, "started_at": ts_s,
                "end_user_id": user, "feature_tag": feature, "agent_name": feature,
            }
            if session_ids:
                run_start["session_id"] = random.choice(session_ids)
            events += [
                run_start,
                {"event_type": "span_start", "span_id": span_id, "run_id": run_id,
                 "span_type": "llm", "name": "llm-call", "started_at": ts_s},
                {"event_type": "provider_call", "run_id": run_id, "span_id": span_id,
                 "provider": _provider(model), "model": model, "input_tokens": in_tok,
                 "output_tokens": out_tok, "latency_ms": latency, "cost_usd": cost,
                 "status": pc_status},
                {"event_type": "span_end", "span_id": span_id, "run_id": run_id,
                 "status": end_status, "ended_at": ts_e, "cost_usd": cost},
                {"event_type": "run_end", "run_id": run_id, "status": end_status,
                 "ended_at": ts_e, "total_cost_usd": cost,
                 "total_input_tokens": in_tok, "total_output_tokens": out_tok},
            ]
            made.append(RunRef(run_id, model, feature, user, cost, success))
        self.sim.post("/ingest/v1/batch", {"events": events}, key=self.key,
                      label=f"ingest {n} runs", expect=(202, 200))
        self.runs.extend(made)
        say(f"    · {n} runs ingested", "d")
        return made

    # ── gateway ──────────────────────────────────────────────────────────────
    def add_route(self, alias: str, model: str, *, priority: int = 10, **flags: Any) -> None:
        body = {"alias": alias, "provider": _provider(model), "target_model": model,
                "priority": priority, **flags}
        self._post("/gateway/routes", body, f"route {alias}→{model}")

    # ── finops ───────────────────────────────────────────────────────────────
    def add_budget(self, scope_type: str, limit_usd: float, *, period_type: str = "monthly",
                   action: str = "notify", scope_id: str | None = None) -> None:
        body: dict[str, Any] = {"scope_type": scope_type, "period_type": period_type,
                                "limit_usd": limit_usd, "action": action}
        if scope_id:
            body["scope_id"] = scope_id
        self._post("/budgets", body, f"budget {scope_type} ${limit_usd}/{period_type}")

    def record_outcome(self, run: RunRef, outcome_type: str, *, success: bool = True,
                       value_usd: float | None = None, labels: dict[str, Any] | None = None) -> None:
        body: dict[str, Any] = {"outcome_type": outcome_type, "success": success,
                                "run_id": run.run_id, "end_user_id": run.user,
                                "labels": labels or {}}
        if value_usd is not None:
            body["value_usd"] = value_usd
        self._post("/outcomes", body, f"outcome {outcome_type}")

    def score(self, run: RunRef, metric_name: str, value: float, label: str | None = None) -> None:
        body = {"run_id": run.run_id, "metric_name": metric_name, "score": value, "label": label}
        self._post("/evaluations/scores", body, f"score {metric_name}={value}")

    # ── quality / governance (best-effort) ───────────────────────────────────
    def add_alert(self, name: str, metric: str, operator: str, threshold: float) -> None:
        self._post("/alerts/rules", {"name": name, "metric": metric, "operator": operator,
                                     "threshold": threshold}, f"alert {name}")


class Sim:
    """Platform-level client: bootstrap the admin, then mint per-scenario workspaces."""

    def __init__(self, base_url: str, admin_secret: str) -> None:
        self.base = base_url.rstrip("/")
        self.admin_secret = admin_secret
        self.http = httpx.Client(timeout=60, follow_redirects=True)
        self.platform_key: str | None = None
        self.workspaces: list[Workspace] = []

    # ── low-level ────────────────────────────────────────────────────────────
    def post(self, path: str, body: dict[str, Any], *, key: str | None = None,
             admin: bool = False, label: str = "", expect: tuple[int, ...] = (200, 201, 202, 204)) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        if admin:
            headers["X-Admin-Secret"] = self.admin_secret
        try:
            r = self.http.post(f"{self.base}{path}", json=body, headers=headers)
        except Exception as exc:  # noqa: BLE001
            say(f"    ! {label or path}: {exc}", "y")
            return {}
        if r.status_code not in expect:
            say(f"    ! {label or path}: {r.status_code} {r.text[:120]}", "y")
            return {}
        return r.json() if r.status_code != 204 and r.content else {}

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
        data = self.post("/admin/bootstrap", {"email": email, "password": password,
                                              "full_name": "Platform Admin", "org_name": org_name},
                         admin=True, label="bootstrap", expect=(200, 201))
        self.platform_key = data.get("api_key")
        if not self.platform_key:
            raise SystemExit("bootstrap failed — no api_key returned")
        say(f"  ✓ platform admin bootstrapped ({email})", "g")

    def workspace(self, org: str, name: str, *, plan: str = "growth") -> Workspace:
        """Create an org (tenant) with its own admin, then log in for a scoped key."""
        slug = org.lower().replace(" ", "-")
        admin_email = f"admin@{slug}.example.com"
        admin_password = "Sim-Passw0rd!"
        self.post("/admin/tenants", {"name": org, "plan": plan, "admin_email": admin_email,
                                     "admin_password": admin_password, "admin_full_name": f"{org} Admin"},
                  key=self.platform_key, admin=True, label=f"org {org}")
        login = self.post("/auth/login", {"email": admin_email, "password": admin_password},
                          label=f"login {org}", expect=(200, 201))
        key = login.get("api_key")
        ws_id = login.get("workspace_id", "")
        if not key:
            say(f"  ! could not obtain key for {org}; skipping", "y")
            key = ""
        ws = Workspace(self, org, name, key, ws_id)
        self.workspaces.append(ws)
        say(f"  ✓ {org} / {name}", "g")
        return ws

    def close(self) -> None:
        self.http.close()
