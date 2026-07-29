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
        self._post("/gateway/routes", body, f"route {alias}→{model}")

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
        # /budgets requires a workspace-admin **user session** (not an API key), so this is
        # skipped quietly under the simulator — create budgets from the dashboard.
        self.sim.post(
            "/budgets",
            body,
            key=self.key,
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
        self._post(
            "/alerts/rules",
            {"name": name, "metric": metric, "operator": operator, "threshold": threshold},
            f"alert {name}",
        )


class Sim:
    """Platform-level client: bootstrap the admin, then mint per-scenario workspaces."""

    def __init__(self, base_url: str, admin_secret: str) -> None:
        self.base = base_url.rstrip("/")
        self.admin_secret = admin_secret
        self.http = httpx.Client(timeout=60, follow_redirects=True)
        self.platform_key: str | None = None
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
        self.platform_key = data.get("api_key")
        if not self.platform_key:
            raise SystemExit("bootstrap failed — no api_key returned")
        say(f"  ✓ platform admin bootstrapped ({email})", "g")

    def workspace(self, org: str, name: str, *, plan: str = "growth") -> Workspace:
        """Create an org (tenant) and mint a workspace-scoped API key via the admin API.

        (New tenant admins are created email-unverified, so we can't log in as them —
        instead the platform admin mints a key for the org's workspace directly.)
        """
        slug = org.lower().replace(" ", "-")
        tenant = self.post(
            "/admin/tenants",
            {
                "name": org,
                "plan": plan,
                "admin_email": f"admin@{slug}.example.com",
                "admin_password": "Sim-Passw0rd!",
                "admin_full_name": f"{org} Admin",
            },
            key=self.platform_key,
            admin=True,
            label=f"org {org}",
        )
        tenant_id = tenant.get("id")
        if not tenant_id:
            # Org already exists (re-run — truncate preserves tenants). Look it up by name.
            listing = self.get("/admin/tenants", key=self.platform_key, admin=True) or []
            rows = listing if isinstance(listing, list) else listing.get("items", [])
            tenant_id = next((t.get("id") for t in rows if t.get("name") == org), None)
        key, ws_id = "", ""
        if tenant_id:
            wss = self.get(
                f"/admin/tenants/{tenant_id}/workspaces", key=self.platform_key, admin=True
            )
            rows = wss if isinstance(wss, list) else (wss or {}).get("items", [])
            if rows:
                ws_id = rows[0].get("id", "")
                resp = self.post(
                    f"/admin/workspaces/{ws_id}/api-keys",
                    {"name": "sim", "environment": "dev"},
                    key=self.platform_key,
                    admin=True,
                    label=f"key {org}",
                )
                key = resp.get("key", "")
        if not key:
            say(f"  ! could not obtain key for {org}; scenario data will be skipped", "y")
        ws = Workspace(self, org, name, key, ws_id)
        self.workspaces.append(ws)
        say(f"  ✓ {org} / {name}", "g")
        return ws

    def close(self) -> None:
        self.http.close()
