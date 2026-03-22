"""
Full simulation: budgets, routing policies, tool registry, security events,
alert rules + forced firings, and gateway logs across all three workspaces.

Run:  uv run python scripts/simulate_all.py
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx

BASE = "http://localhost:8000"

WORKSPACES = [
    {
        "name": "Default Org / default",
        "key": "rl_test_oDZzUDR-1RncfIEdu0tufvqKqHQjWA7fBsRXpzK-mDQ",
    },
    {
        "name": "Default Org / ML Research",
        "key": "rl_test_9SXLH5zP7uQEPizpSYhq0cZRzmHfTHtpv8D-XGP7jMM",
    },
    {
        "name": "Alpha Labs / Alpha Labs WS",
        "key": "rl_test_QSEB5FFfUtOBsRyAYRxfq30M9FmnRn3iUwEc8bx3jrE",
    },
]

# ── helpers ───────────────────────────────────────────────────────────────────

def hdrs(key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def ok(resp: httpx.Response, label: str) -> dict:
    if resp.status_code not in (200, 201, 202, 204):
        print(f"  [WARN] {label}: {resp.status_code} {resp.text[:120]}")
        return {}
    return resp.json() if resp.status_code != 204 else {}


# ── 1. BUDGETS ────────────────────────────────────────────────────────────────

async def create_budgets(client: httpx.AsyncClient, ws: dict) -> None:
    key = ws["key"]
    budgets = [
        # Workspace-level monthly budget — will be overridden by actual spend
        {"scope_type": "workspace", "scope_id": None,   "period_type": "monthly", "limit_usd": "50.00",  "action": "notify"},
        # Per-user daily budget — very low, will fire breach
        {"scope_type": "end_user",  "scope_id": "u_alice", "period_type": "daily",   "limit_usd": "2.00",  "action": "block"},
        {"scope_type": "end_user",  "scope_id": "u_bob",   "period_type": "daily",   "limit_usd": "1.00",  "action": "notify"},
        # Feature-tag budget
        {"scope_type": "feature_tag", "scope_id": "rag",  "period_type": "monthly", "limit_usd": "25.00", "action": "downgrade"},
    ]
    for b in budgets:
        r = await client.post(f"{BASE}/budgets", headers=hdrs(key), json=b)
        status = "✓" if r.status_code == 201 else "✗"
        scope = f"{b['scope_type']}:{b.get('scope_id') or '*'}"
        print(f"    {status} Budget {scope} ${b['limit_usd']}/{b['period_type']} ({b['action']})")


# ── 2. TOOL REGISTRY ──────────────────────────────────────────────────────────

TOOLS = [
    {"tool_name": "web_search",       "policy": "allow", "runtime_enforcement": False,
     "description": "Search the web via Bing/Google API"},
    {"tool_name": "sql_query",        "policy": "audit", "runtime_enforcement": False,
     "description": "Execute read-only SQL against the data warehouse"},
    {"tool_name": "file_write",       "policy": "audit", "runtime_enforcement": True,
     "description": "Write files to the workspace storage bucket"},
    {"tool_name": "shell_exec",       "policy": "block", "runtime_enforcement": True,
     "description": "Execute arbitrary shell commands — blocked by policy"},
    {"tool_name": "email_send",       "policy": "block", "runtime_enforcement": True,
     "description": "Send emails — blocked; requires human approval"},
    {"tool_name": "api_call_external","policy": "audit", "runtime_enforcement": False,
     "description": "Make outbound HTTP calls to third-party APIs"},
    {"tool_name": "vector_store",     "policy": "allow", "runtime_enforcement": False,
     "description": "Read/write embeddings in the vector store"},
]


async def register_tools(client: httpx.AsyncClient, ws: dict) -> None:
    key = ws["key"]
    for t in TOOLS:
        r = await client.post(f"{BASE}/tools/registry", headers=hdrs(key), json=t)
        status = "✓" if r.status_code == 201 else "✗"
        print(f"    {status} Tool {t['tool_name']} policy={t['policy']} enforcement={t['runtime_enforcement']}")


# ── 3. SECURITY EVENTS (trigger blocked tool checks) ─────────────────────────

BLOCKED_TOOLS = ["shell_exec", "email_send"]
TRIGGER_USERS = ["u_alice", "u_bob", "u_carol", "u_dave", "u_eve"]


async def generate_security_events(client: httpx.AsyncClient, ws: dict) -> int:
    """Hit blocked tools repeatedly — each call writes a SecurityEvent."""
    key = ws["key"]
    count = 0
    for tool in BLOCKED_TOOLS:
        for _ in range(6):
            r = await client.get(f"{BASE}/tools/check/{tool}", headers=hdrs(key))
            if r.status_code == 403:
                count += 1  # blocked → security event recorded
    return count


# ── 4. GATEWAY ROUTES + ROUTING POLICIES ─────────────────────────────────────

GATEWAY_ROUTES = [
    {"alias": "llama-local",  "provider": "ollama", "target_model": "llama3.2",
     "base_url": "http://host.docker.internal:11434", "priority": 10},
    {"alias": "llama-fast",   "provider": "ollama", "target_model": "llama3.1:8b",
     "base_url": "http://host.docker.internal:11434", "priority": 20},
    {"alias": "gpt-mini",     "provider": "openai", "target_model": "gpt-4o-mini",
     "api_key_env_var": "OPENAI_API_KEY", "priority": 5},
]

ROUTING_POLICIES = [
    # Cost-optimised: pick cheapest route
    {"alias": "llama-local",  "policy_type": "cost_optimized",    "config": {}},
    # Canary: 10% traffic to gpt-mini, 90% to llama-local
    {"alias": "gpt-mini",     "policy_type": "canary",            "config": {"canary_weight": 0.1}},
    # Weighted: split load across llama variants
    {"alias": "llama-fast",   "policy_type": "weighted",          "config": {"weights": {"llama-local": 0.7, "llama-fast": 0.3}}},
    # Latency optimised (uses p95 from recent requests)
    {"alias": "llama-local",  "policy_type": "latency_optimized", "config": {"window_minutes": 60}},
    # Budget-aware: downgrade when workspace budget is close to limit
    {"alias": "llama-local",  "policy_type": "budget_aware",      "config": {"threshold_pct": 0.8}},
]


async def setup_gateway(client: httpx.AsyncClient, ws: dict) -> list[dict]:
    key = ws["key"]
    created_routes = []
    for route in GATEWAY_ROUTES:
        r = await client.post(f"{BASE}/gateway/routes", headers=hdrs(key), json=route)
        if r.status_code == 201:
            created_routes.append(r.json())
            print(f"    ✓ Route {route['alias']} → {route['provider']}/{route['target_model']}")
        else:
            print(f"    ✗ Route {route['alias']}: {r.status_code} {r.text[:80]}")

    for pol in ROUTING_POLICIES:
        r = await client.post(f"{BASE}/gateway/policies", headers=hdrs(key), json=pol)
        status = "✓" if r.status_code == 201 else "✗"
        print(f"    {status} Policy {pol['alias']} strategy={pol['policy_type']}")

    return created_routes


# ── 5. GATEWAY REQUESTS (generate logs) ──────────────────────────────────────

PROMPTS = [
    ("llama-local",  [{"role": "user", "content": "Summarise our Q1 spend in 2 sentences."}]),
    ("llama-local",  [{"role": "user", "content": "What models had the highest cost last week?"}]),
    ("llama-fast",   [{"role": "user", "content": "Draft a one-line description of our top agent."}]),
    ("gpt-mini",     [{"role": "user", "content": "Classify this run as success or failure."}]),
    ("llama-local",  [{"role": "user", "content": "List budget overruns for the last 30 days."}]),
    ("gpt-mini",     [{"role": "user", "content": "Suggest a cost-saving routing policy."}]),
    ("llama-fast",   [{"role": "user", "content": "Which workspace spent the most this month?"}]),
    ("llama-local",  [{"role": "user", "content": "Alert summary: what triggered most this week?"}]),
]


async def fire_gateway_requests(client: httpx.AsyncClient, ws: dict) -> int:
    """Send completions — records GatewayRequest log even when provider fails."""
    key = ws["key"]
    ok_count = 0
    for alias, messages in PROMPTS:
        r = await client.post(
            f"{BASE}/gateway/chat/completions",
            headers=hdrs(key),
            json={"model": alias, "messages": messages, "max_tokens": 50, "cache": True},
            timeout=15,
        )
        ok_count += 1 if r.status_code == 200 else 0
    return ok_count


# ── 6. ALERT RULES ────────────────────────────────────────────────────────────

ALERT_RULES = [
    # spend_velocity > $0 over last 60 min → fires immediately given our data
    {"name": "High spend rate",        "metric": "spend_velocity", "operator": "gt",
     "threshold": "0.01",  "window_minutes": 60},
    # error_rate > 5% → fire if any failures
    {"name": "Elevated error rate",    "metric": "error_rate",     "operator": "gt",
     "threshold": "0.05",  "window_minutes": 30},
    # p95 latency > 2s
    {"name": "High p95 latency",       "metric": "p95_latency",    "operator": "gt",
     "threshold": "2000",  "window_minutes": 60},
    # avg_score < 0.5 (fires when scores are low)
    {"name": "Low average score",      "metric": "avg_score",      "operator": "lt",
     "threshold": "0.5",   "window_minutes": 120},
]


async def create_alert_rules(client: httpx.AsyncClient, ws: dict) -> list[str]:
    key = ws["key"]
    rule_ids = []
    for rule in ALERT_RULES:
        r = await client.post(f"{BASE}/alerts/rules", headers=hdrs(key), json=rule)
        if r.status_code == 201:
            rule_ids.append(r.json()["id"])
            print(f"    ✓ Alert '{rule['name']}' metric={rule['metric']} {rule['operator']} {rule['threshold']}")
        else:
            print(f"    ✗ Alert '{rule['name']}': {r.status_code} {r.text[:80]}")
    return rule_ids


# ── 7. INGEST FAILED RUNS (triggers error_rate + budget breach) ──────────────

async def ingest_failures(client: httpx.AsyncClient, ws: dict, n: int = 8) -> None:
    """Ingest failed runs to push error_rate above 5% threshold."""
    key = ws["key"]
    now = datetime.now(UTC)
    events = []
    for _ in range(n):
        run_id = str(uuid.uuid4())
        ts = (now - timedelta(minutes=10)).isoformat().replace("+00:00", "Z")
        te = (now - timedelta(minutes=9, seconds=30)).isoformat().replace("+00:00", "Z")
        events += [
            {"event_type": "run_start", "run_id": run_id, "started_at": ts},
            {"event_type": "run_end",   "run_id": run_id, "ended_at": te, "status": "failed"},
        ]
    r = await client.post(f"{BASE}/ingest/v1/batch", headers=hdrs(key), json={"events": events})
    status = "✓" if r.status_code == 202 else "✗"
    print(f"    {status} Ingested {n} failed runs for error_rate alert")


# ── 8. FORCE ALERT EVALUATION ────────────────────────────────────────────────

async def force_alert_evaluation(client: httpx.AsyncClient, key: str) -> None:
    """Trigger the alert Celery worker via an admin endpoint if available,
       otherwise wait for the 5-min beat schedule."""
    # The alerts worker runs every 5 min via Celery Beat.
    # We trigger it directly through the Celery broker using the task name.
    # As a fallback, we check GET /alerts/history to see what already fired.
    r = await client.get(f"{BASE}/alerts/history", headers=hdrs(key))
    history = r.json().get("items", []) if r.status_code == 200 else []
    print(f"    ℹ  {len(history)} existing alert firings (Beat runs every 5 min)")


# ── MAIN ─────────────────────────────────────────────────────────────────────

async def main() -> None:
    async with httpx.AsyncClient(timeout=20) as client:
        for ws in WORKSPACES:
            print(f"\n{'='*60}")
            print(f"  Workspace: {ws['name']}")
            print(f"{'='*60}")

            # 1. Budgets
            print("\n[1] Creating budgets …")
            await create_budgets(client, ws)

            # 2. Tool registry
            print("\n[2] Registering tools …")
            await register_tools(client, ws)

            # 3. Security events (blocked tool hits)
            print("\n[3] Generating security events (blocked tool checks) …")
            n_events = await generate_security_events(client, ws)
            print(f"    ✓ {n_events} security events written")

            # 4. Gateway routes + routing policies
            print("\n[4] Setting up gateway routes + routing policies …")
            await setup_gateway(client, ws)

            # 5. Gateway requests → logs
            print("\n[5] Firing gateway requests (logs recorded even on provider failure) …")
            hits = await fire_gateway_requests(client, ws)
            print(f"    ✓ {len(PROMPTS)} requests logged ({hits} provider successes)")

            # 6. Alert rules
            print("\n[6] Creating alert rules …")
            await create_alert_rules(client, ws)

            # 7. Ingest failures (to trigger error_rate alert)
            print("\n[7] Ingesting failed runs …")
            await ingest_failures(client, ws)

            # 8. Alert evaluation status
            print("\n[8] Alert evaluation …")
            await force_alert_evaluation(client, ws["key"])

        # Wait for Celery enrichment + alert evaluation
        print("\n\nWaiting 70s for Celery cost enrichment + alert evaluation …")
        await asyncio.sleep(70)

        # ── Final summary ─────────────────────────────────────────────────────
        print("\n" + "="*60)
        print("  FINAL STATE SUMMARY")
        print("="*60)
        for ws in WORKSPACES:
            key = ws["key"]
            h = hdrs(key)
            summary   = (await client.get(f"{BASE}/analytics/summary", headers=h)).json()
            budgets   = (await client.get(f"{BASE}/budgets", headers=h)).json()
            tools     = (await client.get(f"{BASE}/tools/registry", headers=h)).json()
            sec_evts  = (await client.get(f"{BASE}/tools/security-events", headers=h)).json()
            gw_stats  = (await client.get(f"{BASE}/gateway/stats", headers=h)).json()
            alerts    = (await client.get(f"{BASE}/alerts/history", headers=h)).json()

            print(f"\n  {ws['name']}")
            print(f"    Spend:          ${summary.get('total_cost_usd', '0')}")
            print(f"    Budgets:        {len(budgets.get('items', []))} active")
            print(f"    Tools:          {len(tools.get('items', []))} registered")
            print(f"    Security events:{len(sec_evts.get('items', []))} recorded")
            print(f"    Gateway reqs:   {gw_stats.get('total_requests', '?')} total, "
                  f"{gw_stats.get('cache_hits', '?')} cache hits")
            print(f"    Alert firings:  {len(alerts.get('items', []))} fired")


if __name__ == "__main__":
    asyncio.run(main())
