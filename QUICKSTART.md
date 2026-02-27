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
docker compose up -d          # starts Postgres + Redis + API

# 2. Run migrations
docker compose exec api uv run alembic upgrade head

# 3. Seed a dev workspace and API key
docker compose exec api uv run python scripts/seed.py
```

The seed script prints your API key — save it, it won't be shown again:

```
Tenant:    default  (a1b2c3...)
Workspace: default  (d4e5f6...)
API Key:   rl_test_xxxxxxxxxxxxxxxxxxxx
```

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

## What's next

- **Phase 7** — Budget guardrails (`block` / `throttle` / `downgrade` actions)
- **Phase 8** — Chargeback engine + signed billing statements
- **Phase 9** — Unit economics graph + deployment version change-impact diffs
- **Phase 10** — End-user cohort analytics + replay harness
