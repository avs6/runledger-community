# Integrating an Existing Stack

The real-world adoption path: you already run an AI stack and want RunLedger's
cost/governance layer on top — **without** merging RunLedger into your stack.

## The Golden Rule: Reach Across, Don't Embed

RunLedger runs as **its own** stack. The two stacks talk over the Docker host bridge:

| RunLedger Surface | From Your Containers |
|---|---|
| API + Gateway (OpenAI-compatible) | `http://host.docker.internal:8201` (`/gateway`) |
| OTLP Collector (HTTP / gRPC) | `http://host.docker.internal:4318` / `:4317` |

Start order doesn't matter. Out-of-band capture simply no-ops if RunLedger is down.

## Find the Choke Point

Most stacks funnel LLM calls through **one OpenAI-compatible proxy**. Instrument
that and you capture everything at once.

> **Example — LocalAIAgentStack:** Open WebUI, OpenHands, LangGraph, and AnythingLLM
> all call **LiteLLM** (`http://litellm:4000/v1`), which fans out to Ollama.
> LiteLLM is the choke point.

If your stack has no single hub, apply the same tiers per app.

## RunLedger vs Your Existing Tracer

If you already run Langfuse/Phoenix/etc., RunLedger is **not** a replacement — it's
the **FinOps + governance** layer: cost attribution, budgets that *block*, gateway
routing + semantic cache, outcomes/ROI, and tool policies. Both coexist.

> Cost appears once you upload a pricing catalog — local models are $0 until priced.
> Import [`samples/pricing.sample.yaml`](./pricing.sample.yaml) via Provider Profiles → Import.

---

## Tier 1 — Out-of-Band Capture (Start Here)

Mirror every call the hub proxies into RunLedger. Lowest risk, whole-stack coverage.

**A — Give the collector a key.** Mint a workspace key in the dashboard, then:

```bash
RUNLEDGER_API_KEY=rl_... docker compose --profile observability up -d runledger-otel-collector
```

**B — Turn on OTEL export in the hub.** In `config/litellm/config.yaml`:

```yaml
litellm_settings:
  callbacks: ["otel"]
```

On the `litellm` service, add:

```yaml
environment:
  OTEL_EXPORTER: "otlp_http"
  OTEL_ENDPOINT: "http://host.docker.internal:4318/v1/traces"
```

**C — Verify.** Restart LiteLLM, make a call. Within ~15s it appears on RunLedger's
**Runs** page with model and tokens. Cost shows once the model has a pricing row.

---

## Tier 2 — Inline via Gateway (Budgets, Caching, Routing)

To *enforce* (block on budget, semantic-cache, route by complexity), put RunLedger
**in the path** for chosen models.

**In RunLedger:** create a route — alias `stack-chat`, provider `ollama`, model
`qwen2.5-coder:7b`, base URL `http://host.docker.internal:11434/v1`, semantic cache ON.
Add a workspace budget with action = block.

**In `config/litellm/config.yaml`:**

```yaml
- model_name: qwen-runledger
  litellm_params:
    model: openai/stack-chat
    api_base: http://host.docker.internal:8201/gateway
    api_key: rl_...
```

Migrate models one at a time; everything else keeps going straight to Ollama.

---

## Tier 3 — SDK (Code You Own)

Black-box images can't take the SDK, but code you build can — for the richest data
(run context, per-step cost, scores, outcomes).

Example: in `vendors/langgraph-starter/agent/graph.py`, add `runledger-sdk`, wrap
the graph in `rl.context(...)`, and call `rl.score()` / `rl.outcome()`.

---

## Per-Component Scenarios

| Component | Tier | Scenario |
|---|---|---|
| **LiteLLM** (hub) | 1 → 2 | Mirror all traffic; promote one model to Gateway for budget enforcement |
| **Open WebUI** | via hub | Per-model chat cost; cap daily spend |
| **OpenHands** | via hub | Watch coding agent token burn; semantic-cache repeated context |
| **LangGraph** | 3 (SDK) | Instrument the graph — run context, per-node cost, quality scores |
| **AnythingLLM** (RAG) | via hub | Split embedding vs generation cost; route cheap vs frontier |
| **n8n** | 3 (HTTP node) | Emit outcome/score when a workflow completes |
| **Dify** | 2 (provider) | Add the Gateway as a provider; govern tool calls |

---

## What NOT to Do

- Don't copy RunLedger services into your compose — run it as its own stack.
- Don't point tools at RunLedger directly *and* bypass your hub.
- Watch for host-port clashes between the two stacks.
