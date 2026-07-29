# Part 8 · Integrating an existing stack

*This is the real-world adoption path: a customer already runs an AI stack of open-source
tools and wants RunLedger's cost/governance layer on top — **without** merging RunLedger into
their stack.* We use a concrete example stack, but the pattern generalises to any setup.

## The golden rule: reach across, don't embed

RunLedger runs as **its own** stack. You never add its services to your compose. The two stacks
talk over the Docker host bridge — every container that sets
`extra_hosts: ["host.docker.internal:host-gateway"]` (yours already do) can reach RunLedger at:

| RunLedger surface | From your containers |
|---|---|
| API + **Gateway** (OpenAI-compatible) | `http://host.docker.internal:8201` (`/gateway`) |
| **OTLP** collector (HTTP / gRPC) | `http://host.docker.internal:4318` / `:4317` |

Start order doesn't matter. Out-of-band capture (Tier 1) simply no-ops if RunLedger is down.

## Find the choke point — instrument the hub, not every tool

Most stacks funnel LLM calls through **one OpenAI-compatible proxy**. Instrument that and you
capture everything at once.

> **Worked example — `LocalAIAgentStack`:** Open WebUI, OpenHands, LangGraph, and AnythingLLM
> are all configured to call **LiteLLM** (`http://litellm:4000/v1`), which fans out to Ollama.
> LiteLLM is the choke point. (It also already ships traces to **Langfuse** — see below.)

If your stack has no single hub, apply the same tiers per app (each app's OpenAI base URL).

## RunLedger vs. your existing tracer (e.g. Langfuse)

If you already run Langfuse/Phoenix/etc., RunLedger is **not** a replacement — it's the
**FinOps + governance** layer: cost attribution across tools, budgets that *block*, gateway
routing + semantic cache, outcomes/ROI, and tool policies. Tracing tool and RunLedger coexist;
point both at the hub.

> Cost only appears once you upload a pricing catalog — local models are $0 until priced.
> Import [`samples/pricing.sample.yaml`](./pricing.sample.yaml) (Provider Profiles → Import) so
> your Ollama traffic accrues trackable spend.

---

## Tier 1 — Capture everything, out-of-band (start here)

Mirror every call the hub proxies into RunLedger. Lowest risk, whole-stack coverage, request
path unchanged.

**Step A — give the RunLedger collector a key (required, one-time).** The collector forwards to
RunLedger authenticated as a workspace. It's inert until you set it (that's why a fresh
collector shows *unhealthy*). On the **RunLedger** stack:

```bash
# mint a workspace key in the dashboard (Settings → API Keys), then:
RUNLEDGER_API_KEY=rl_... docker compose up -d runledger-otel-collector
```

All stack traffic lands in that one workspace — e.g. make a workspace called *"Local AI Stack"*.

**Step B — turn on OTEL export in the hub.** In `config/litellm/config.yaml`:

```yaml
litellm_settings:
  callbacks: ["otel"]
```

and on the `litellm` service in your compose, add the standard OTEL env pointing at RunLedger's
collector:

```yaml
    environment:
      OTEL_EXPORTER_OTLP_ENDPOINT: "http://host.docker.internal:4318"
      OTEL_EXPORTER_OTLP_PROTOCOL: "http/protobuf"
```

> Exact var names vary by LiteLLM version — confirm against yours. The collector accepts both
> gRPC (4317) and HTTP (4318); RunLedger's ingest reads OTel **GenAI** (`gen_ai.*`) and
> OpenInference conventions, which LiteLLM emits.

**Step C — verify.** Restart LiteLLM, then make a call through the stack (chat in Open WebUI,
or `curl` LiteLLM). Within ~5s it appears on RunLedger's **Runs** page with model, tokens, and
(once pricing is uploaded) cost. Nothing in your stack changed except a mirror.

🔎 You now see cost/usage for **every tool** — Open WebUI, OpenHands, LangGraph, AnythingLLM —
in one place, sliced by model.

---

## Tier 2 — Inline via the RunLedger Gateway (budgets bite, caching, routing)

Tier 1 observes; to *enforce* (block on budget, semantic-cache, route by complexity), put
RunLedger **in the path** for chosen models. Because the Gateway is OpenAI-compatible, add a
RunLedger-backed model to the hub instead of repointing tools.

**In RunLedger:** create a route (Gateway page) — alias `stack-chat`, provider `ollama`,
target `qwen2.5-coder:7b`, base URL `http://host.docker.internal:11434/v1`, **semantic cache
ON**; add a workspace **budget** (Budgets page) with action = block.

**In `config/litellm/config.yaml`:** add a model that points at the Gateway:

```yaml
  - model_name: qwen-runledger
    litellm_params:
      model: openai/stack-chat                       # the RunLedger alias
      api_base: http://host.docker.internal:8201/gateway
      api_key: rl_...                                 # a RunLedger workspace key
```

Now any tool that selects `qwen-runledger` runs **through RunLedger** — cache hits, spend caps,
per-user limits, intelligent routing all apply. Migrate models one at a time; everything else
keeps going straight to Ollama.

🔎 Pick one high-volume model to promote first (e.g. Open WebUI's default) and watch a daily
budget actually stop traffic — enforcement your tracer can't do.

---

## Tier 3 — SDK, for the code you own

Black-box images (Open WebUI, AnythingLLM) can't take the SDK, but code you build can, for the
richest data (run context, per-step cost, scores, outcomes).

> In the example stack that's `vendors/langgraph-starter/agent/graph.py` — add
> `runledger-sdk`, wrap the graph in `rl.context(...)`, and call `rl.score()` / `rl.outcome()`.
> See Part 1, Lab 01. **n8n:** add an HTTP Request node hitting RunLedger at the end of a
> workflow. **Dify:** add the RunLedger Gateway as an OpenAI-compatible model provider (Tier 2).

---

## Per-component scenarios (example stack)

| Component | Tier | Scenario |
|---|---|---|
| **LiteLLM** (hub) | 1 → 2 | Mirror all traffic; then promote one model to the Gateway to enforce a stack-wide budget |
| **Open WebUI** | via hub | Per-model chat cost; cap daily spend |
| **OpenHands** | via hub | Watch a coding agent's token burn; semantic-cache repeated context |
| **LangGraph starter** | 3 (SDK) | Instrument the graph — run context, per-node cost, quality scores |
| **AnythingLLM** (RAG) | via hub | Split embedding vs generation cost; route cheap vs frontier |
| **n8n** | 3 (HTTP node) | Emit an outcome/score when a workflow completes |
| **Dify** | 2 (provider) | Add the Gateway as a provider; govern tool calls |

---

## What NOT to do

- ❌ Don't copy RunLedger services into your compose — run it as its own stack and reach it via
  `host.docker.internal`.
- ❌ Don't point tools at RunLedger directly *and* bypass your hub — keep the hub as the single
  path so one config change covers everything.
- ⚠️ Watch for host-port clashes between the two stacks (RunLedger uses `8201/3201/8202/4317/
  4318/5432/6379`; the example stack uses the `30xx` range + internal-only infra — no clash).

✅ **End of Part 8.** This is the adoption blueprint: run RunLedger beside an existing stack,
instrument the hub for whole-stack cost visibility (Tier 1), enforce policy on chosen models
(Tier 2), and go deep on code you own (Tier 3) — no changes to the stack's compose.
