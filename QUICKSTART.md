# RunLedger — Quickstart Guide

Get billing-grade cost tracking on your AI agents in under 5 minutes.

---

## What RunLedger captures automatically

| Data point | How |
|------------|-----|
| `model` | From the API response |
| `input_tokens` / `output_tokens` | From the API response |
| `cached_input_tokens` | From OpenAI Prompt Caching header |
| `latency_ms` | Measured wall-clock around the API call |
| `cost_usd` | Computed server-side from the pricing engine |
| `end_user_id` | Set by you in `rl.context()` |
| `session_id` | Set by you in `rl.context()` |
| `feature_tag` | Set by you in `rl.context()` |
| `run_id` | Auto-generated UUID (or set by you) |
| Span DAG | Full parent-child tree via LangChain/LangGraph callbacks |

No prompts or completions are sent unless you opt in to `PrivacyMode.FULL`.

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Python 3.13+ | SDK requirement |
| OpenAI API key | For the examples — swap for any provider |
| RunLedger API key | See "Getting an API key" below |
| Docker (optional) | To run the full RunLedger stack locally |

---

## 1. Install the SDK

```bash
# Minimum (OpenAI only)
pip install "runledger-sdk[openai]"

# LangChain support
pip install "runledger-sdk[langchain]"

# LangGraph support
pip install "runledger-sdk[langgraph]"

# Everything + CLI
pip install "runledger-sdk[all]"
```

---

## 2. Get an API key

### Option A — Local stack (recommended for development)

```bash
# 1. Clone the repo and start the stack
git clone https://github.com/yourorg/runledger
cd runledger
docker compose -f infra/docker-compose.yml up -d --build

# 2. Run migrations
docker exec infra-api-1 uv run alembic upgrade head

# 3. Bootstrap the platform admin (one-time setup)
curl -s -X POST http://localhost:8000/admin/bootstrap \
  -H "X-Admin-Secret: runledger-admin" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@runledger.io",
    "password": "Admin123!",
    "full_name": "Platform Admin",
    "org_name": "RunLedger"
  }'
```

The bootstrap call returns your API key and org details:

```json
{
  "user_id": "...",
  "tenant_id": "...",
  "workspace_id": "...",
  "api_key": "rl_test_xxxxxxxxxxxxxxxxxxxx",
  "message": "Platform admin 'admin@runledger.io' ready."
}
```

4. Update `examples/.env` with the returned `api_key`, then:
   - Open **http://localhost:3000**
   - Login with `admin@runledger.io` / `Admin123!`
   - You'll see a **Platform Admin** section in the sidebar

> **Roles**: Platform admin can create new organizations via **Admin → Tenants**. Each org gets its own admin user and workspace. Org admins manage their own users, workspaces, and settings without needing the platform admin secret.

### Option B — Local mode (zero setup, events logged to console)

Skip the API entirely during early development. Pass `local=True` or omit
`api_key` and RunLedger prints structured JSON to stdout instead of sending
to the API.

```python
rl = RunLedger(local=True)  # no API key needed
```

### Option C — RunLedger cloud (coming soon)

Sign up at [runledger.io](https://runledger.io) → Settings → API Keys → New Key.

---

## 3. Verify your API key

```bash
export RUNLEDGER_API_KEY=rl_test_...

runledger validate         # sends a synthetic test event
runledger status           # checks API + DB + Redis health
runledger runs --limit 5   # lists your most recent agent runs
```

---

## 4. Instrument OpenAI (2 lines)

```python
from runledger_sdk import RunLedger
import openai

rl = RunLedger(api_key="rl_test_...")  # or reads RUNLEDGER_API_KEY
rl.instrument()                         # wraps openai.OpenAI + AsyncOpenAI

client = openai.OpenAI()

with rl.context(end_user_id="u_123", feature_tag="support-chat") as run_id:
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Hello!"}],
    )
    print(resp.choices[0].message.content)

rl.shutdown()  # flush before process exits
```

That's it. Every `create()` call inside the `with` block is now tracked.

### What `rl.context()` does

`rl.context()` is a context manager (supports both `with` and `async with`).
It sets thread-local / async-local metadata that is attached to every event
fired inside the block.

```python
with rl.context(
    end_user_id="u_123",       # who triggered this run
    session_id="sess_abc",     # groups multiple runs into a session
    feature_tag="support-bot", # which feature/product area
    deployment_version="v2.1", # your app's deployment version
) as run_id:
    # run_id is a UUID you can log, return to the client, etc.
    ...
```

Contexts nest — inner blocks inherit outer values and can selectively override:

```python
with rl.context(end_user_id="u_123"):
    # all calls here tagged to u_123

    with rl.context(feature_tag="checkout"):
        # tagged to u_123 + checkout
        ...

    with rl.context(feature_tag="search"):
        # tagged to u_123 + search
        ...
```

---

## 5. LangChain

```python
from runledger_sdk import RunLedger
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

rl = RunLedger(api_key="rl_test_...")

llm = ChatOpenAI(model="gpt-4o-mini")
prompt = ChatPromptTemplate.from_template("Explain {topic} in one sentence.")
chain = prompt | llm | StrOutputParser()

# One handler instance per RunLedger client
handler = rl.callback_handler()

with rl.context(end_user_id="u_456", feature_tag="explainer") as run_id:
    result = chain.invoke(
        {"topic": "gradient descent"},
        config={"callbacks": [handler]},   # <── attach here
    )
    print(result)

rl.shutdown()
```

The callback handler fires:
- `run_start` / `run_end` at the outermost chain boundary
- `span_start` / `span_end` for each chain, LLM, and tool invocation
- `provider_call` with token counts at `on_llm_end`

> **Avoid double-counting:** if you also call `rl.instrument()` (OpenAI patch),
> pass `track_llm_cost=False` to the handler to prevent duplicate provider_call
> events:
> ```python
> handler = rl.callback_handler(track_llm_cost=False)
> ```

---

## 6. LangGraph

```python
from runledger_sdk import RunLedger
from runledger_sdk.langgraph import instrument_graph
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from typing import TypedDict

rl = RunLedger(api_key="rl_test_...")

class State(TypedDict):
    question: str
    answer: str

llm = ChatOpenAI(model="gpt-4o-mini")

def answer_node(state: State) -> State:
    resp = llm.invoke(state["question"])
    return {**state, "answer": resp.content}

builder = StateGraph(State)
builder.add_node("answer", answer_node)
builder.set_entry_point("answer")
builder.add_edge("answer", END)
graph = builder.compile()

# Instrument once after compile()
graph = instrument_graph(graph, rl._get_sync_transport())

with rl.context(end_user_id="u_789", feature_tag="qa-graph") as run_id:
    result = graph.invoke({"question": "What is 2+2?", "answer": ""})
    print(result["answer"])

rl.shutdown()
```

`instrument_graph()` uses LangGraph's `with_config()` to inject a
`RunLedgerCallbackHandler` into every node execution. The original graph
object is unchanged — a new configured view is returned.

---

## 7. Async usage

All context managers support `async with`:

```python
import asyncio
import openai
from runledger_sdk import RunLedger

rl = RunLedger(api_key="rl_test_...")
rl.instrument()

client = openai.AsyncOpenAI()

async def main():
    async with rl.context(end_user_id="u_async") as run_id:
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello async!"}],
        )
        print(resp.choices[0].message.content)

    await rl.aflush()

asyncio.run(main())
```

---

## 8. FastAPI middleware pattern

For web services, set the context in a middleware or dependency so every
request is attributed automatically:

```python
from fastapi import FastAPI, Header
from runledger_sdk import RunLedger

app = FastAPI()
rl = RunLedger(api_key="rl_test_...")
rl.instrument()

@app.post("/chat")
async def chat(
    body: ChatRequest,
    x_user_id: str | None = Header(default=None),
):
    async with rl.context(
        end_user_id=x_user_id or "anonymous",
        feature_tag="chat-api",
    ) as run_id:
        # all LLM calls here are attributed to x_user_id
        ...
    return {"run_id": run_id, ...}

@app.on_event("shutdown")
async def shutdown():
    await rl.aflush()
```

---

## 9. Cross-service propagation

Preserve run context when calling downstream services:

**Service A (caller)**
```python
with rl.context(end_user_id="u_123", feature_tag="pipeline"):
    headers = rl.propagation_headers()
    # {'X-RunLedger-Run-Id': '...', 'X-RunLedger-End-User-Id': 'u_123', ...}

    response = httpx.post("http://service-b/process", headers=headers, ...)
```

**Service B (receiver)**
```python
@app.post("/process")
async def process(request: Request):
    ctx = RunLedger.from_headers(dict(request.headers))
    async with ctx as run_id:
        # run_id, end_user_id, feature_tag are all restored
        ...
```

All spans from both services share the same `run_id` and appear together
in the Run Explorer.

---

## 10. Analytics API

Once events are flowing, query your spend data:

```bash
BASE=http://localhost:8000
KEY=rl_test_...

# Total cost + tokens for the last 7 days (includes period-over-period delta)
curl "$BASE/analytics/summary" -H "Authorization: Bearer $KEY"
# → { total_cost_usd, prev_cost_usd, cost_delta_pct, run_count, call_count, ... }

# Daily spend time-series
curl "$BASE/analytics/spend-over-time?granularity=daily" \
     -H "Authorization: Bearer $KEY"

# Cost breakdown by model
curl "$BASE/analytics/spend-by-model" -H "Authorization: Bearer $KEY"

# Top 10 spenders (includes avg_cost_per_run and last_active)
curl "$BASE/analytics/spend-by-user?limit=10" \
     -H "Authorization: Bearer $KEY"

# Cost by feature tag
curl "$BASE/analytics/spend-by-feature" -H "Authorization: Bearer $KEY"

# Full spend profile for a single end-user
curl "$BASE/analytics/users/user-alice" -H "Authorization: Bearer $KEY"
# → { cost_usd, run_count, avg_cost_per_run, last_active,
#     spend_over_time[], models_used[], features_used[] }
```

All endpoints accept `from` and `to` query params (ISO-8601 datetimes):

```bash
curl "$BASE/analytics/summary?from=2026-01-01T00:00:00Z&to=2026-01-31T23:59:59Z" \
     -H "Authorization: Bearer $KEY"
```

The analytics dashboard at `http://localhost:3000/analytics` visualises all of the above with Recharts — summary cards, spend-over-time line chart, spend-by-model bar chart, spend-by-feature donut, and a top-spenders table with clickable user profiles. Use the 24h / 7d / 30d preset buttons to change the time window.

### Runs API + CSV export

```bash
# List runs — filter by model, cost range, status, time window
curl "$BASE/runs?model=gpt-4o&min_cost=0.01&status=succeeded&from=2026-01-01T00:00:00Z" \
     -H "Authorization: Bearer $KEY"

# Download filtered runs as CSV (up to 5 000 rows)
curl "$BASE/runs/export?model=gpt-4o&from=2026-03-01T00:00:00Z" \
     -H "Authorization: Bearer $KEY" \
     -o runs.csv
```

The dashboard Run Explorer at `http://localhost:3000/runs` exposes the same filters via the UI — including model substring search, cost range, and a custom datetime picker with second-level granularity. The **Export CSV** button downloads the currently filtered view.

---

## 11. Run the example agents

```bash
cd runledger

# Set environment variables
export OPENAI_API_KEY=sk-...
export RUNLEDGER_API_KEY=rl_test_...   # or skip — examples use local=True

# Example 1: Basic OpenAI call
uv run python examples/01_openai_basic.py

# Example 2: Multi-turn conversation with session tracking
uv run python examples/02_openai_multi_turn.py

# Example 3: LangChain chain
pip install langchain-openai
uv run python examples/03_langchain_chain.py

# Example 4: LangGraph ReAct agent with tools
pip install langchain-openai langgraph
uv run python examples/04_langgraph_agent.py

# Example 5: FastAPI service
pip install fastapi uvicorn
uv run uvicorn examples.05_fastapi_service:app --reload
curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -H "X-User-Id: user-alice" \
     -d '{"message": "What is Python?"}'

# Example 6: Local Ollama (OpenAI-compatible endpoint, no cloud needed)
# Requires: ollama pull llama3.2 && ollama serve
uv run python examples/06_ollama_local.py --local   # stdout only
uv run python examples/06_ollama_local.py           # sends to RunLedger API

# Example 7: Analytics API query (requires a running RunLedger stack with data)
export RUNLEDGER_API_KEY=rl_test_...
uv run python examples/07_analytics_query.py

# Example 19: Unified policy decision checks
uv run python examples/19_policy_check.py
```

---

## Troubleshooting

### Events not appearing in the API

1. Check your API key: `runledger validate`
2. Check service health: `runledger status`
3. Confirm `rl.shutdown()` (sync) or `await rl.aflush()` (async) is called
   before the process exits — unflushed events in the buffer are lost.

### "No pricing row" in logs

The cost enrichment worker needs pricing data. Run the seed script:
```bash
cd apps/api && uv run python scripts/seed.py
```

### Duplicate provider_call events

If you use both `rl.instrument()` and `rl.callback_handler()`, pass
`track_llm_cost=False` to the handler:
```python
handler = rl.callback_handler(track_llm_cost=False)
```

### Events are captured but cost_usd is NULL

Cost enrichment runs every 60 seconds via Celery Beat. Start the worker:
```bash
celery -A runledger_api.core.celery_app worker --loglevel=info --pool=solo
celery -A runledger_api.core.celery_app beat --loglevel=info
```

### Ollama / local provider shows $0 cost

That's correct — Ollama and other self-hosted providers have no API cost, so RunLedger stores `cost_usd = 0.00`. Runs will appear in the analytics with zero cost, which is accurate. If you want to assign an internal transfer price to Ollama usage, add a pricing row via **Settings → Provider Profiles** (or `POST /providers/pricing`) for `provider = ollama`.

---

## Reference

### RunLedger client

```python
rl = RunLedger(
    api_key="rl_live_...",          # reads RUNLEDGER_API_KEY if omitted
    base_url="https://...",          # default: https://api.runledger.io
    privacy_mode=PrivacyMode.METADATA_ONLY,  # default
    local=False,                     # True → log to stdout, no HTTP
)
```

### Context manager

```python
with rl.context(
    run_id=None,                 # auto-generated UUID if omitted
    end_user_id=None,
    session_id=None,
    feature_tag=None,
    deployment_version=None,
) as run_id: ...
```

### Transport flush

```python
rl.flush()          # sync — blocks until all events are sent
await rl.aflush()   # async variant
rl.shutdown()       # flush + stop background thread
```

### Supported providers

| Provider | Models tracked |
|----------|----------------|
| OpenAI | gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo, o1, o3-mini |
| Anthropic | claude-opus-4-6, claude-sonnet-4-6, claude-haiku-4-5 |
| Google | gemini-1.5-pro, gemini-1.5-flash |

Add a new model by inserting a row into `provider_pricing` — no code change
required.

---

## 12. Quality scores

Attach quality scores to runs from anywhere — human raters, rule-based checks, or post-processing pipelines:

```python
from runledger_sdk import RunLedger

rl = RunLedger(api_key="rl_test_...")

with rl.context(end_user_id="u_123", feature_tag="support-chat") as run_id:
    # ... your agent logic ...

    # Rate the response after the run completes
    rl.score("helpfulness", 0.9, label="good", source="human")
    rl.score("relevance", 0.75, run_id=str(run_id), confidence=0.9)

rl.shutdown()
```

`rl.score()` is synchronous and fails silently — it will never raise or interrupt your agent.

When `run_id` is omitted, it is picked up from the current `rl.context()` automatically.

**Query score analytics via the API:**

```bash
KEY=rl_test_...
BASE=http://localhost:8000

# Average score per score name + period-over-period delta
curl "$BASE/analytics/scores/summary" -H "Authorization: Bearer $KEY"
# → { "items": [{ "name": "helpfulness", "avg_value": "0.88", "change_pct": "+5.2", ... }] }

# Score names where avg dropped >20% vs prior week
curl "$BASE/analytics/scores/regressions" -H "Authorization: Bearer $KEY"
# → [] if no regressions
```

The **/evaluations** dashboard page (`http://localhost:3000/evaluations`) provides:
- A submit-score form (no code needed for human ratings)
- Per-score-name summary cards with ↑/↓ delta badges
- A recent scores table with run-ID links

---

---

## 13. Prompt management

Version-controlled prompt templates with `{{variable}}` substitution and environment promotion:

```python
from runledger_sdk import RunLedger

rl = RunLedger(api_key="rl_test_...")

# Fetch latest production version (60s in-memory cache)
rendered = rl.get_prompt(
    "support-agent",
    environment="production",
    variables={"user_name": "Alice", "company": "Acme"},
)
# rendered["content"]  → "Welcome Alice! How can I assist you at Acme today?"
# rendered["version"]  → 3

# Link runs to prompt versions for per-version metrics:
with rl.context(
    end_user_id="u_123",
    deployment_version=f"support-agent:{rendered['version']}",
) as run_id:
    # ... your agent logic ...
    pass

rl.shutdown()
```

**Manage prompts via the API:**

```bash
KEY=rl_test_...
BASE=http://localhost:8000

# Create a prompt
curl -X POST "$BASE/prompts" -H "Authorization: Bearer $KEY" \
     -H "Content-Type: application/json" \
     -d '{"name":"support-agent","default_environment":"production"}'

# Commit a staging version
curl -X POST "$BASE/prompts/support-agent/versions" -H "Authorization: Bearer $KEY" \
     -H "Content-Type: application/json" \
     -d '{"content":"Hello {{user_name}}!","environment":"staging","commit_message":"v1 draft"}'

# Promote to production
curl -X POST "$BASE/prompts/support-agent/promote" -H "Authorization: Bearer $KEY" \
     -H "Content-Type: application/json" \
     -d '{"source_environment":"staging","target_environment":"production"}'

# Per-version metrics (run count, avg cost, avg score)
curl "$BASE/prompts/support-agent/metrics" -H "Authorization: Bearer $KEY"
```

The **/prompts** dashboard page (`http://localhost:3000/prompts`) provides:
- A prompt list with create/delete controls
- Per-prompt detail: version history with env badges, commit messages, metrics cards
- Commit form with `{{variable}}` syntax hint
- Side-by-side line-level diff viewer between any two versions
- One-click "Promote staging → production" button

---

## 14. Sessions & payload viewer

Group multi-turn conversations and inspect captured prompts/completions:

```python
import uuid
from runledger_sdk import RunLedger

rl = RunLedger(api_key="rl_test_...")
rl.instrument()

# Assign a stable session_id across turns to group them
session_id = str(uuid.uuid4())

for turn, message in enumerate(["Hello!", "What's the weather?", "Thanks, bye."]):
    with rl.context(
        end_user_id="u_123",
        session_id=session_id,
        feature_tag="support-chat",
    ):
        # ... call your LLM here ...
        pass

rl.shutdown()
```

**Query sessions via the API:**

```bash
KEY=rl_test_...
BASE=http://localhost:8000

# List sessions (grouped by session_id, ordered by most recent)
curl "$BASE/sessions" -H "Authorization: Bearer $KEY"
# → { "items": [{ "session_id": "...", "run_count": 3, "total_cost_usd": "0.0042", ... }] }

# Session detail with turn-ordered run list
curl "$BASE/sessions/{session_id}" -H "Authorization: Bearer $KEY"

# Per-turn and cumulative cost (for chart rendering)
curl "$BASE/sessions/{session_id}/cost-over-turns" -H "Authorization: Bearer $KEY"
# → { "turns": [{ "turn_number": 1, "cost_usd": "0.001", "cumulative_cost_usd": "0.001" }, ...] }
```

To see captured payloads inline in the run detail, enable SAMPLED capture first:

```bash
curl -X PUT "$BASE/privacy/capture-policy" -H "Authorization: Bearer $KEY" \
     -H "Content-Type: application/json" \
     -d '{"privacy_mode": "SAMPLED", "sampled_rate": "1.0"}'
```

The **/sessions** dashboard page (`http://localhost:3000/sessions`) provides:
- A filterable session list with user, turn count, total cost, and duration
- Session detail with a cumulative cost line chart and per-turn run timeline
- The run detail page (`/runs/[id]`) shows an inline **Payload Viewer** with colour-coded message roles when payloads are captured

---

## 15. Alert rules

Set up threshold-based alerts that fire every 5 minutes via Celery Beat:

```bash
KEY=rl_test_...
BASE=http://localhost:8000

# Alert when error rate exceeds 5% in a 1-hour window
curl -X POST "$BASE/alerts/rules" -H "Authorization: Bearer $KEY" \
     -H "Content-Type: application/json" \
     -d '{"name":"High error rate","metric":"error_rate","operator":"gt","threshold":0.05,"window_minutes":60}'

# Alert when p95 latency exceeds 5 000 ms in a 30-minute window
curl -X POST "$BASE/alerts/rules" -H "Authorization: Bearer $KEY" \
     -H "Content-Type: application/json" \
     -d '{"name":"Slow responses","metric":"p95_latency","operator":"gt","threshold":5000,"window_minutes":30}'

# Alert when average quality score drops below 0.6
curl -X POST "$BASE/alerts/rules" -H "Authorization: Bearer $KEY" \
     -H "Content-Type: application/json" \
     -d '{"name":"Low quality","metric":"avg_score","operator":"lt","threshold":0.6,"window_minutes":60}'

# Alert when hourly spend exceeds $5
curl -X POST "$BASE/alerts/rules" -H "Authorization: Bearer $KEY" \
     -H "Content-Type: application/json" \
     -d '{"name":"Spend spike","metric":"spend_velocity","operator":"gt","threshold":5.0,"window_minutes":60}'

# List all rules
curl "$BASE/alerts/rules" -H "Authorization: Bearer $KEY"

# Toggle a rule on/off
curl -X PUT "$BASE/alerts/rules/{rule_id}" -H "Authorization: Bearer $KEY" \
     -H "Content-Type: application/json" \
     -d '{"is_active": false}'

# Recent firings
curl "$BASE/alerts/history?limit=20" -H "Authorization: Bearer $KEY"
```

Supported metrics:

| Metric | Description |
|--------|-------------|
| `error_rate` | Fraction of failed runs in the window (0–1) |
| `p95_latency` | 95th-percentile run duration in milliseconds |
| `avg_score` | Average value from `/evaluations/scores` in the window |
| `spend_velocity` | Total `cost_usd` across all runs in the window |

The **Settings → Alert Rules** section in the dashboard provides a full UI for managing rules and viewing recent firings.

---

## 16. Model gateway

Point any OpenAI client at RunLedger's proxy to get prompt caching, provider fallback, and automatic request logging — with zero code changes:

**Configure a route** (Settings → Model Gateway or via API):

```bash
KEY=rl_test_...
BASE=http://localhost:8000

curl -X POST "$BASE/gateway/routes" -H "Authorization: Bearer $KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "alias": "gpt-4o-mini",
       "provider": "openai",
       "target_model": "gpt-4o-mini",
       "api_key_env_var": "OPENAI_API_KEY",
       "priority": 10
     }'
```

**Use it** — change only `base_url`, keep your existing code:

```python
import openai

client = openai.OpenAI(
    api_key="rl_test_...",                     # RunLedger API key
    base_url="http://localhost:8000/gateway",  # RunLedger gateway
)

resp = client.chat.completions.create(
    model="gpt-4o-mini",   # alias from the route above
    messages=[{"role": "user", "content": "What is 2+2?"}],
)
# First call: forwarded to OpenAI, response stored in cache.
# Identical second call: returned from cache in <5ms.
```

**Fallback routing** — add a second route with higher `priority` number:

```bash
# priority 20 = lower priority than 10; tried only if priority-10 route fails
curl -X POST "$BASE/gateway/routes" -H "Authorization: Bearer $KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "alias": "gpt-4o-mini",
       "provider": "groq",
       "target_model": "llama-3.3-70b-versatile",
       "base_url": "https://api.groq.com/openai/v1",
       "api_key_env_var": "GROQ_API_KEY",
       "priority": 20
     }'
```

If OpenAI returns 429 or 5xx, the gateway automatically retries via Groq.

**Check stats:**

```bash
curl "$BASE/gateway/stats" -H "Authorization: Bearer $KEY"
# → { "total_requests": 42, "cache_hits": 18, "cache_hit_rate": "0.4286",
#     "avg_latency_ms": "312.50", "routes": [...] }
```

---

## 17. Unified policy checks

Use one endpoint to evaluate budgets, tool policies, gateway route readiness, and optional score gates before allowing an action.

```bash
KEY=rl_test_...
BASE=http://localhost:8000

# Simple admission check
curl -X POST "$BASE/policies/check" -H "Authorization: Bearer $KEY" \
     -H "Content-Type: application/json" \
     -d '{}'

# Tool + gateway checks
curl -X POST "$BASE/policies/check" -H "Authorization: Bearer $KEY" \
     -H "Content-Type: application/json" \
     -d '{"tool_name":"search","model_alias":"gpt-4o-mini","end_user_id":"user-alice"}'

# Add a score gate for release checks
curl -X POST "$BASE/policies/check" -H "Authorization: Bearer $KEY" \
     -H "Content-Type: application/json" \
     -d '{"score_gate":{"name":"helpfulness","min_value":80,"source":"human"}}'
```

---

## What's next

- **Phase 20** — TypeScript / Node.js SDK (`@runledger/sdk`, OpenAI Node, Vercel AI SDK)
- **Phase 22** — SaaS Foundation — self-service signup, Stripe subscriptions, usage quota enforcement
