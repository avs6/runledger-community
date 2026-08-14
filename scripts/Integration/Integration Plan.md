# Integration Plan

## Goal

Integrate the separate `C:\Users\Abi\Desktop\LocalAIAgentStack` repo with RunLedger so RunLedger becomes the single AI FinOps, observability, optimization, and control plane for the local agent ecosystem.

The repos stay separate:

- `C:\Users\Abi\Desktop\github\runledger-community` remains the RunLedger product/control-plane repo.
- `C:\Users\Abi\Desktop\LocalAIAgentStack` remains the local agent stack repo.
- Integration happens through stable network endpoints, environment variables, API keys, OTLP, OpenAI-compatible gateway routes, and optional SDK/MCP adapters.

The intended demo should feel like real usage: one RunLedger organization, multiple workspaces, scoped API keys, multiple agent systems, inline and out-of-band telemetry, Gateway optimization, budgets, experiments, and product-polish feedback from actual daily agent workflows.

---

## Target Architecture

```text
LocalAIAgentStack
  Open WebUI
  OpenHands
  LangGraph
  Hermes Agent
  Dify
  n8n / AnythingLLM
  LiteLLM
  local Ollama models
  desktop dev agents
    Claude Desktop
    OpenAI Codex
    Windsurf
    Devin
    Cursor

          inline SDK / OpenAI-compatible Gateway / OTLP / MCP
                              |
                              v
RunLedger
  Single Org: Local AI Lab
  Workspaces:
    Gateway Hub
    Open WebUI
    OpenHands
    LangGraph
    Hermes Agent
    Dify + n8n
    Desktop Agents
    Experiments Lab
  Control Plane:
    API Keys
    Gateway routes
    Provider Profiles
    Budgets
    Alert Rules
    Data Capture
    OTLP
    MCP
  Outcomes:
    cost per task
    cost per agent
    success/failure
    eval scores
    productivity/quality signals
```

---

## Integration Modes

Use all three modes because they prove different parts of the product.

| Mode | Purpose | Best For |
|---|---|---|
| Gateway inline path | RunLedger sits in the request path and can enforce routing, cache, compiler, budget, PII redaction, and rate limits | LiteLLM, Open WebUI, OpenHands, LangGraph, Dify, agents using OpenAI-compatible APIs |
| SDK inline instrumentation | Rich agent/run/span/outcome data emitted directly from code | LangGraph custom graph, Hermes adapter, custom wrappers, task runners |
| OTLP out-of-band | Services keep their existing request path but export spans/metrics to RunLedger | LiteLLM telemetry, Dify OTEL, LangGraph/OpenTelemetry, OpenHands if instrumented |
| MCP/dev-agent overlay | Dev tools can call RunLedger tools for context, memory, analytics, budget checks, and optimization helpers | Claude Desktop, Codex, Cursor, Windsurf, Devin-style workflows |

The integration should not force everything through one path. The demo is stronger if some systems are governed inline and others are observed out-of-band.

---

## RunLedger Setup

### Organization

Create one organization:

- Org name: `Local AI Lab`
- Platform admin remains the local operator/admin.
- Org admin owns all workspaces and Gateway/Provider/Profile setup.

### Workspaces

Create these workspaces first:

| Workspace | Purpose | Primary Key Use |
|---|---|---|
| `Gateway Hub` | Shared LiteLLM and central Gateway routes | Gateway proxy traffic, shared route tests |
| `Open WebUI` | Chat UI traffic | Open WebUI key |
| `OpenHands` | Coding/autonomous dev agent traffic | OpenHands key |
| `LangGraph` | Graph/runtime experiments | SDK + Gateway + OTLP key |
| `Hermes Agent` | Hermes agent tasks | Gateway + OTLP key |
| `Dify + n8n` | Workflow/app builder traffic | Gateway + OTLP key |
| `Desktop Agents` | Claude Desktop, Codex, Cursor, Windsurf, Devin | MCP + wrapper keys |
| `Experiments Lab` | Prompt/eval/model experiments | evaluation + replay workflows |

Optional later split:

- `Claude Desktop`
- `OpenAI Codex`
- `Cursor`
- `Windsurf`
- `Devin`

Start with `Desktop Agents` as one workspace. Split when attribution needs to be sharper.

### API Keys

Create one workspace key per workspace from **Control Plane -> API Keys**.

Store them in the LocalAIAgentStack `.env` as references, not inside committed compose files:

```env
RUNLEDGER_BASE_URL=http://host.docker.internal:8201
RUNLEDGER_OTLP_HTTP=http://host.docker.internal:4318/v1/traces
RUNLEDGER_GATEWAY_BASE_URL=http://host.docker.internal:8201/gateway
RUNLEDGER_MCP_URL=http://host.docker.internal:8206/mcp

RUNLEDGER_KEY_GATEWAY_HUB=rl_...
RUNLEDGER_KEY_OPEN_WEBUI=rl_...
RUNLEDGER_KEY_OPENHANDS=rl_...
RUNLEDGER_KEY_LANGGRAPH=rl_...
RUNLEDGER_KEY_HERMES=rl_...
RUNLEDGER_KEY_DIFY_N8N=rl_...
RUNLEDGER_KEY_DESKTOP_AGENTS=rl_...
RUNLEDGER_KEY_EXPERIMENTS=rl_...
```

Do not reuse the same key everywhere. The demo depends on workspace-level isolation.

---

## LocalAIAgentStack Current Fit

Observed stack files:

- `C:\Users\Abi\Desktop\LocalAIAgentStack\docker-compose.yml`
- `C:\Users\Abi\Desktop\LocalAIAgentStack\config\litellm\config.yaml`
- `C:\Users\Abi\Desktop\LocalAIAgentStack\vendors\langgraph-starter\agent\graph.py`
- `C:\Users\Abi\Desktop\LocalAIAgentStack\images\openhands-winports\`
- `C:\Users\Abi\Desktop\LocalAIAgentStack\vendors\dify\`

Already present:

- LiteLLM is the central model gateway for several services.
- Open WebUI points to `http://litellm:4000/v1`.
- OpenHands points to `http://litellm:4000/v1`.
- LangGraph starter points to LiteLLM with `ChatOpenAI`.
- LiteLLM has OTEL export placeholders:
  - `OTEL_EXPORTER=otlp_http`
  - `OTEL_ENDPOINT=http://host.docker.internal:4318/v1/traces`
- Dify supports OTEL env knobs in vendor configs.

This means the first integration should start with LiteLLM and only then move individual tools onto RunLedger Gateway.

### Current Configuration Status

LocalAIAgentStack is **not fully configured with RunLedger yet**. Treat this plan as the implementation checklist, not a record of completed integration.

Current known state:

| Component | Current State | RunLedger Work Needed |
|---|---|---|
| LiteLLM | Present and already central for several services | Add RunLedger Gateway-backed model aliases and inject RunLedger workspace keys |
| Open WebUI | Points to LiteLLM | Select RunLedger-backed LiteLLM models once aliases exist |
| OpenHands | Points to LiteLLM with `LLM_BASE_URL=http://litellm:4000/v1` | Point `LLM_MODEL` to a RunLedger-backed LiteLLM alias; add task outcome wrapper later |
| LangGraph | Starter graph uses `ChatOpenAI` through LiteLLM | Add RunLedger SDK and inline spans/outcomes |
| Hermes Agent | Service exists but API/model config needs review | Point to LiteLLM/RunLedger and add OTLP or wrapper capture |
| Dify/n8n/AnythingLLM | Present through LocalAIAgentStack/vendor config | Route provider settings to LiteLLM aliases and enable OTLP where supported |
| Desktop agents | Not wired yet | Add Claude Desktop MCP config and wrapper scripts for Codex/Cursor/Windsurf/Devin-style tasks |

Do not assume OpenHands, Hermes, or desktop agents are already logging into RunLedger. The first visible success should be one Open WebUI or LiteLLM request appearing in RunLedger Gateway logs.

---

## LocalAIAgentStack Documentation To Add

Add a RunLedger section to `C:\Users\Abi\Desktop\LocalAIAgentStack\README.md` after the service overview. Suggested text:

```md
## RunLedger Integration

RunLedger is kept in a separate repo at:

`C:\Users\Abi\Desktop\github\runledger-community`

This stack integrates with RunLedger through:

- LiteLLM model aliases that point at RunLedger Gateway
- OTLP export to RunLedger's collector
- optional inline SDK instrumentation for LangGraph/custom agents
- optional MCP connection for Claude Desktop and other dev-agent workflows

RunLedger should be running first:

```powershell
cd C:\Users\Abi\Desktop\github\runledger-community
docker compose up -d
Invoke-WebRequest -UseBasicParsing http://localhost:8201/health/ready
Invoke-WebRequest -UseBasicParsing http://localhost:3201/login
```

Create one RunLedger org named `Local AI Lab`, then create workspace-scoped API keys for:

- Gateway Hub
- Open WebUI
- OpenHands
- LangGraph
- Hermes Agent
- Dify + n8n
- Desktop Agents
- Experiments Lab

Store those keys only in `.env`; do not commit real keys.
```

Also add a small status note:

```md
### Integration Status

RunLedger integration is being rolled out incrementally. Some services may still call LiteLLM directly.

Recommended order:

1. LiteLLM -> RunLedger Gateway
2. Open WebUI through RunLedger-backed LiteLLM alias
3. OpenHands through RunLedger-backed LiteLLM alias
4. LangGraph inline SDK instrumentation
5. Hermes/Dify/n8n OTLP and Gateway routing
6. Desktop-agent MCP/wrapper capture
```

---

## API Key Injection Guide

### 1. Create Keys In RunLedger

In RunLedger:

1. Log in as org admin or platform admin.
2. Open **Control Plane -> API Keys**.
3. Create one key per workspace.
4. Copy each key immediately; it is shown once.

Recommended names:

| Workspace | Key Name |
|---|---|
| Gateway Hub | `local-stack-gateway-hub` |
| Open WebUI | `local-stack-open-webui` |
| OpenHands | `local-stack-openhands` |
| LangGraph | `local-stack-langgraph` |
| Hermes Agent | `local-stack-hermes` |
| Dify + n8n | `local-stack-dify-n8n` |
| Desktop Agents | `local-stack-desktop-agents` |
| Experiments Lab | `local-stack-experiments` |

### 2. Add Keys To LocalAIAgentStack `.env`

In `C:\Users\Abi\Desktop\LocalAIAgentStack\.env`, add:

```env
# RunLedger endpoints
RUNLEDGER_BASE_URL=http://host.docker.internal:8201
RUNLEDGER_API_URL=http://host.docker.internal:8201
RUNLEDGER_GATEWAY_BASE_URL=http://host.docker.internal:8201/gateway
RUNLEDGER_OTLP_HTTP=http://host.docker.internal:4318/v1/traces
RUNLEDGER_OTLP_COLLECTOR=http://host.docker.internal:4318
RUNLEDGER_MCP_URL=http://host.docker.internal:8206/mcp

# Workspace-scoped keys
RUNLEDGER_KEY_GATEWAY_HUB=rl_replace_me
RUNLEDGER_KEY_OPEN_WEBUI=rl_replace_me
RUNLEDGER_KEY_OPENHANDS=rl_replace_me
RUNLEDGER_KEY_LANGGRAPH=rl_replace_me
RUNLEDGER_KEY_HERMES=rl_replace_me
RUNLEDGER_KEY_DIFY_N8N=rl_replace_me
RUNLEDGER_KEY_DESKTOP_AGENTS=rl_replace_me
RUNLEDGER_KEY_EXPERIMENTS=rl_replace_me
```

For host-side tools like Claude Desktop, use `http://localhost:...` URLs instead:

```env
RUNLEDGER_HOST_API_URL=http://localhost:8201
RUNLEDGER_HOST_GATEWAY_BASE_URL=http://localhost:8210/gateway
RUNLEDGER_HOST_MCP_URL=http://localhost:8206/mcp
```

Why both forms matter:

| Caller | Use |
|---|---|
| Docker container in LocalAIAgentStack | `host.docker.internal` |
| Browser or desktop app on Windows host | `localhost` |
| Container-to-container on shared Docker network, if added later | service DNS name |

### 3. Inject Keys Into `docker-compose.yml`

Update LocalAIAgentStack services with env references rather than literal keys.

LiteLLM:

```yaml
litellm:
  environment:
    LITELLM_MASTER_KEY: "local-litellm-master-key"
    RUNLEDGER_BASE_URL: "${RUNLEDGER_BASE_URL}"
    RUNLEDGER_GATEWAY_BASE_URL: "${RUNLEDGER_GATEWAY_BASE_URL}"
    RUNLEDGER_API_KEY: "${RUNLEDGER_KEY_GATEWAY_HUB}"
    OTEL_EXPORTER: "otlp_http"
    OTEL_ENDPOINT: "${RUNLEDGER_OTLP_HTTP}"
```

Open WebUI:

```yaml
open-webui:
  environment:
    OPENAI_API_BASE_URL: "http://litellm:4000/v1"
    OPENAI_API_BASE_URLS: "http://litellm:4000/v1"
    OPENAI_API_KEY: "local-litellm-master-key"
    OPENAI_API_KEYS: "local-litellm-master-key"
    RUNLEDGER_API_KEY: "${RUNLEDGER_KEY_OPEN_WEBUI}"
```

OpenHands:

```yaml
openhands:
  environment:
    LLM_MODEL: "openai/runledger-openhands-code"
    LLM_BASE_URL: "http://litellm:4000/v1"
    LLM_API_KEY: "local-litellm-master-key"
    RUNLEDGER_API_KEY: "${RUNLEDGER_KEY_OPENHANDS}"
    RUNLEDGER_BASE_URL: "${RUNLEDGER_BASE_URL}"
```

LangGraph:

```yaml
langgraph:
  environment:
    OPENAI_API_BASE_URL: "http://litellm:4000/v1"
    OPENAI_API_KEY: "local-litellm-master-key"
    RUNLEDGER_API_KEY: "${RUNLEDGER_KEY_LANGGRAPH}"
    RUNLEDGER_BASE_URL: "${RUNLEDGER_BASE_URL}"
    OTEL_EXPORTER_OTLP_ENDPOINT: "${RUNLEDGER_OTLP_COLLECTOR}"
```

Hermes Agent:

```yaml
hermes-agent:
  environment:
    RUNLEDGER_API_KEY: "${RUNLEDGER_KEY_HERMES}"
    RUNLEDGER_BASE_URL: "${RUNLEDGER_BASE_URL}"
    OPENAI_BASE_URL: "http://litellm:4000/v1"
    OPENAI_API_KEY: "local-litellm-master-key"
```

Dify/n8n style services:

```yaml
environment:
  RUNLEDGER_API_KEY: "${RUNLEDGER_KEY_DIFY_N8N}"
  RUNLEDGER_BASE_URL: "${RUNLEDGER_BASE_URL}"
  ENABLE_OTEL: "true"
  OTLP_BASE_ENDPOINT: "${RUNLEDGER_OTLP_COLLECTOR}"
```

These snippets are templates. Apply them service-by-service after confirming each container supports the specific env var names.

### 4. Add LiteLLM RunLedger Aliases

In `C:\Users\Abi\Desktop\LocalAIAgentStack\config\litellm\config.yaml`, add aliases like:

```yaml
  - model_name: runledger-openwebui-chat
    litellm_params:
      model: openai/local-chat
      api_base: http://host.docker.internal:8201/gateway
      api_key: os.environ/RUNLEDGER_KEY_OPEN_WEBUI

  - model_name: runledger-openhands-code
    litellm_params:
      model: openai/qwen-code
      api_base: http://host.docker.internal:8201/gateway
      api_key: os.environ/RUNLEDGER_KEY_OPENHANDS

  - model_name: runledger-langgraph-chat
    litellm_params:
      model: openai/langgraph-chat
      api_base: http://host.docker.internal:8201/gateway
      api_key: os.environ/RUNLEDGER_KEY_LANGGRAPH

  - model_name: runledger-desktop-agent
    litellm_params:
      model: openai/dev-agent-auto
      api_base: http://host.docker.internal:8201/gateway
      api_key: os.environ/RUNLEDGER_KEY_DESKTOP_AGENTS
```

Then create matching RunLedger Gateway route aliases:

- `local-chat`
- `qwen-code`
- `langgraph-chat`
- `dev-agent-auto`

### 5. Validate Key Injection

From LocalAIAgentStack:

```powershell
cd C:\Users\Abi\Desktop\LocalAIAgentStack
docker compose config | Select-String RUNLEDGER
docker compose up -d litellm
docker compose logs --tail 80 litellm
```

From RunLedger:

```powershell
Invoke-WebRequest -UseBasicParsing http://localhost:8201/health/ready
Invoke-WebRequest -UseBasicParsing http://localhost:13133/
```

Smoke test one Gateway call:

```powershell
$headers = @{ Authorization = "Bearer $env:RUNLEDGER_KEY_GATEWAY_HUB" }
$body = @{
  model = "local-chat"
  messages = @(@{ role = "user"; content = "Say hello from LocalAIAgentStack" })
} | ConvertTo-Json -Depth 10
Invoke-RestMethod -Method Post -Uri "http://localhost:8210/gateway/chat/completions" -Headers $headers -ContentType "application/json" -Body $body
```

Verify in RunLedger:

- **Gateway -> Requests** shows the call.
- **Runs** or **Analytics** shows the workspace traffic after processing.
- **API Keys** shows the key used for the correct workspace.

---

---

## Traffic Flow Design

### Phase 1 Flow: Observe Existing LiteLLM Traffic

```text
Open WebUI / OpenHands / LangGraph / Hermes / Dify
        -> LiteLLM
        -> Ollama / local models
        -> OTLP spans to RunLedger collector
```

Goal:

- Keep existing request path stable.
- Export spans out-of-band to RunLedger.
- Validate Runs/Sessions/Analytics light up.

### Phase 2 Flow: Put RunLedger Gateway In The Path

```text
Open WebUI / OpenHands / LangGraph / Hermes / Dify
        -> LiteLLM
        -> RunLedger Gateway
        -> Ollama / hosted providers
```

Goal:

- RunLedger enforces route budgets, semantic cache, context compiler, prompt compression, intelligent routing, PII redaction, and per-user limits.
- LiteLLM remains the compatibility hub for tools that expect LiteLLM.

### Phase 3 Flow: Direct SDK + Outcomes

```text
LangGraph / Hermes / custom wrappers
        -> runledger-sdk inline spans + scores + outcomes
        -> optional Gateway model calls
```

Goal:

- Rich application-level task spans.
- Outcomes like `task_completed`, `bug_fixed`, `research_answered`, `workflow_succeeded`.
- Score signals for evals/flywheel.

### Phase 4 Flow: Desktop Agent Overlay

```text
Claude Desktop / Codex / Cursor / Windsurf / Devin
        -> MCP / wrapper scripts / shell hooks
        -> RunLedger Desktop Agents workspace
        -> optional Gateway for model calls
```

Goal:

- Track spawned task agents and dev workflows.
- Attribute cost and outcomes by tool, repo, task type, and user.
- Use RunLedger MCP tools for memory, budgets, analytics, and optimization suggestions.

---

## LiteLLM Integration

### Step 1: Add RunLedger As A Provider Target

In `LocalAIAgentStack/config/litellm/config.yaml`, add aliases that point to RunLedger Gateway:

```yaml
model_list:
  - model_name: runledger-qwen-coder
    litellm_params:
      model: openai/qwen-code
      api_base: http://host.docker.internal:8201/gateway
      api_key: ${RUNLEDGER_KEY_GATEWAY_HUB}

  - model_name: runledger-local-chat
    litellm_params:
      model: openai/local-chat
      api_base: http://host.docker.internal:8201/gateway
      api_key: ${RUNLEDGER_KEY_GATEWAY_HUB}

  - model_name: runledger-auto
    litellm_params:
      model: openai/auto-chat
      api_base: http://host.docker.internal:8201/gateway
      api_key: ${RUNLEDGER_KEY_GATEWAY_HUB}
```

RunLedger Gateway routes to create:

| Alias | Target | Optimization |
|---|---|---|
| `qwen-code` | Ollama `qwen2.5-coder-64k:latest` | compiler + tool filtering |
| `local-chat` | Ollama `qwen2.5-coder:7b` or `qwen3:4b` | semantic cache |
| `auto-chat` | tiered aliases | intelligent routing |
| `dev-heavy` | stronger local or hosted reasoning model | compression + budget guardrails |

### Step 2: Keep OTLP Export On

Set LiteLLM OTLP to RunLedger collector:

```env
OTEL_EXPORTER=otlp_http
OTEL_ENDPOINT=http://host.docker.internal:4318/v1/traces
RUNLEDGER_API_KEY=${RUNLEDGER_KEY_GATEWAY_HUB}
```

If LiteLLM cannot attach the RunLedger key as a Bearer header for OTLP, route OTLP through a small collector config that injects the header, or use direct RunLedger SDK wrappers for the first demo.

### Step 3: Demo Validation

Run a prompt from Open WebUI through a `runledger-*` model. Verify:

- RunLedger **Gateway** request appears.
- **Runs** and **Analytics** show tokens/cost.
- Semantic cache hit appears after repeated questions.
- Budget caps block when configured low.

---

## Open WebUI Integration

Initial path:

```text
Open WebUI -> LiteLLM -> RunLedger Gateway -> Ollama
```

Configuration:

- Keep Open WebUI pointed at LiteLLM:
  - `OPENAI_API_BASE_URL=http://litellm:4000/v1`
  - `OPENAI_API_KEY=local-litellm-master-key`
- Add RunLedger-backed models in LiteLLM and expose them in Open WebUI.

RunLedger workspace:

- `Open WebUI`

Tracking plan:

- Use a dedicated RunLedger key if Open WebUI can route per-model or per-header.
- Otherwise start with `Gateway Hub` and use metadata tags or model aliases to identify Open WebUI traffic.

Demo:

- Chat with `runledger-local-chat`.
- Ask the same support-style question twice to show semantic cache.
- Ask a long context question to show compiler savings.
- Show RunLedger Analytics by feature/model/user.

---

## OpenHands Integration

Initial path:

```text
OpenHands -> LiteLLM -> RunLedger Gateway -> Ollama/local models
```

Current stack already points OpenHands to LiteLLM:

- `LLM_MODEL=openai/qwen2.5-coder-64k`
- `LLM_BASE_URL=http://litellm:4000/v1`
- `LLM_API_KEY=local-litellm-master-key`

Plan:

1. Add a LiteLLM model alias `runledger-openhands-code`.
2. Point OpenHands `LLM_MODEL` to that alias.
3. Create RunLedger Gateway route:
   - alias: `openhands-code`
   - target: `qwen2.5-coder-64k:latest`
   - compiler: on
   - tool filtering: on
   - budget: daily cap
   - PII redaction: on
4. Add task-level outcome logging if OpenHands exposes task hooks or logs:
   - `task_completed`
   - `patch_created`
   - `tests_passed`
   - `human_intervention_required`

Demo:

- Ask OpenHands to make a small repo change.
- Show RunLedger spans by task.
- Show cost by task and tool-use profile.
- Show budget guardrail for runaway loops.

---

## LangGraph Integration

Use both inline and gateway modes. LangGraph is ideal for product polish because it can emit clean spans, scores, and outcomes.

Current file:

- `LocalAIAgentStack/vendors/langgraph-starter/agent/graph.py`

Plan:

1. Keep `ChatOpenAI` compatible path through LiteLLM.
2. Add RunLedger SDK to `requirements.txt`.
3. Wrap graph execution with RunLedger:
   - run start/end
   - node spans
   - LLM call spans
   - tool spans
   - score events
   - outcome events
4. Add environment:
   ```env
   RUNLEDGER_BASE_URL=http://host.docker.internal:8201
   RUNLEDGER_API_KEY=${RUNLEDGER_KEY_LANGGRAPH}
   OPENAI_API_BASE_URL=http://litellm:4000/v1
   OPENAI_API_KEY=local-litellm-master-key
   ```

Recommended tags:

- `feature_tag=langgraph-local-agent`
- `task_class=research`
- `agent_framework=langgraph`
- `repo=LocalAIAgentStack`

Outcomes:

- `answer_accepted`
- `tool_success`
- `workflow_completed`
- `workflow_failed`

Experiments:

- Compare `qwen2.5-coder-64k` vs `qwen2.5-coder:7b`.
- Compare compiler on/off.
- Compare semantic cache threshold.
- Track eval score vs cost.

---

## Hermes Agent Integration

Initial path:

```text
Hermes Agent -> LiteLLM or RunLedger Gateway -> model
```

Plan:

1. Identify Hermes Agent model configuration in `data/hermes/.env`.
2. Point it to LiteLLM `runledger-hermes` alias first.
3. If Hermes supports OpenTelemetry, export to:
   - `http://host.docker.internal:4318/v1/traces`
4. If not, add a thin sidecar/wrapper:
   - starts a RunLedger run
   - invokes Hermes task
   - tails Hermes logs
   - records task outcome and cost association

Workspace:

- `Hermes Agent`

Demo:

- Run an autonomous task.
- Show out-of-band spans if available.
- Show cost attribution through Gateway even if app-level spans are minimal.

---

## Dify + n8n Integration

Initial path:

```text
Dify / n8n -> LiteLLM -> RunLedger Gateway -> model
```

Plan:

1. Configure Dify OpenAI-compatible provider:
   - base URL: `http://litellm:4000/v1`
   - key: `local-litellm-master-key`
   - model: RunLedger-backed LiteLLM alias
2. Enable Dify OTEL if stable:
   - `ENABLE_OTEL=true`
   - `OTLP_BASE_ENDPOINT=http://host.docker.internal:4318`
   - add RunLedger API key header if supported
3. Configure n8n HTTP/OpenAI calls through LiteLLM or direct RunLedger Gateway.
4. Use workspace `Dify + n8n`.

Demo:

- Build a Dify workflow.
- Trigger it from n8n.
- Show cost per workflow run.
- Attach outcome `workflow_succeeded` with value.

---

## Desktop Agent Integration

Target tools:

- Claude Desktop
- OpenAI Codex
- Cursor
- Windsurf
- Devin

### Integration Principle

Desktop tools are harder to instrument internally, so use layered capture:

1. MCP overlay for tools that support MCP.
2. Shell/task wrapper for commands they spawn.
3. Gateway proxy when the tool allows OpenAI-compatible model configuration.
4. OTLP sidecar only where the tool or wrapper can emit spans.

### Claude Desktop

Use RunLedger MCP:

```json
{
  "mcpServers": {
    "runledger": {
      "url": "http://localhost:8206/mcp",
      "env": {
        "RUNLEDGER_API_KEY": "<RUNLEDGER_KEY_DESKTOP_AGENTS>"
      }
    }
  }
}
```

Use cases:

- query RunLedger analytics
- memory/knowledge graph
- compile context
- select tools
- flywheel analysis
- budget checks before starting expensive work

### OpenAI Codex / Cursor / Windsurf / Devin

Create a local wrapper strategy:

```text
dev-agent-wrapper
  start RunLedger run
  record repo/task/tool metadata
  launch agent command
  capture stdout/stderr summary
  record outcome
  record score if tests pass/fail
```

Suggested metadata:

- `tool=codex|cursor|windsurf|devin`
- `repo=runledger-community|LocalAIAgentStack|other`
- `task_type=bugfix|refactor|docs|integration|test`
- `branch`
- `commit_sha`
- `workspace`
- `estimated_value_usd`

Possible outcomes:

- `task_completed`
- `tests_passed`
- `pr_opened`
- `commit_created`
- `manual_rework_required`
- `abandoned`

Later, if any tool supports configurable model provider/base URL, point it at:

- `http://localhost:8210/gateway`
- API key: `RUNLEDGER_KEY_DESKTOP_AGENTS`
- model alias: `dev-agent-auto`

---

## RunLedger Gateway Route Plan

Create these routes in RunLedger Gateway:

| Alias | Workspace | Target | Controls |
|---|---|---|---|
| `local-chat` | Gateway Hub | Ollama `qwen3:4b` or `qwen2.5-coder:7b` | semantic cache |
| `qwen-code` | OpenHands / Gateway Hub | Ollama `qwen2.5-coder-64k:latest` | compiler + tool filtering |
| `langgraph-chat` | LangGraph | Ollama `qwen2.5-coder:7b` | compiler on |
| `hermes-chat` | Hermes Agent | local model | semantic cache + budget |
| `workflow-chat` | Dify + n8n | local model | per-user RPM + PII redaction |
| `dev-agent-auto` | Desktop Agents | tiered local/provider models | intelligent routing |
| `experiment-a` | Experiments Lab | baseline model | no optimization |
| `experiment-b` | Experiments Lab | same model | compiler/cache/compression |

Route controls to exercise:

- semantic cache
- context compiler
- prompt compression
- tool filtering
- skill injection
- intelligent routing
- daily/monthly route cost cap
- per-user RPM
- PII redaction
- health auto-disable/fallback

---

## Provider Profiles

Import or maintain provider pricing for:

- `qwen2.5-coder-64k:latest`
- `qwen2.5-coder:7b`
- `qwen2.5-coder:3b`
- `phi4-mini:latest`
- `qwen3:4b`
- `nomic-embed-text:latest`
- any hosted providers used later

Local models should have non-zero infra pricing so budgets, cost per task, and ROI demos are meaningful.

---

## Budgets

Start with intentionally small budgets so the demo shows enforcement:

| Workspace | Budget | Action |
|---|---|---|
| Gateway Hub | daily `$2` | notify |
| OpenHands | daily `$1` | block |
| LangGraph | monthly `$20` | notify |
| Hermes Agent | daily `$1` | notify |
| Dify + n8n | daily `$1` | block |
| Desktop Agents | daily `$3` | notify |
| Experiments Lab | monthly `$10` | notify |

Add per-route hard caps for runaway-agent demos.

---

## Experiments And Evaluation

Use RunLedger experiments to compare:

- LiteLLM direct to Ollama vs LiteLLM to RunLedger Gateway.
- Cache off vs semantic cache on.
- Compiler off vs compiler on.
- Compression off vs compression on.
- Tool filtering off vs on.
- Local small model vs local coder model.
- Desktop agent task costs across Codex/Cursor/Windsurf/Claude.

Core metrics:

- cost per successful task
- total tokens per task
- latency
- cache hit rate
- compiler token savings
- quality score
- tests passed
- human rework needed
- task completion rate

Outcomes:

- `task_completed`
- `tests_passed`
- `workflow_succeeded`
- `answer_accepted`
- `bug_resolved`
- `pr_ready`

---

## Demo Narrative

The cool demo should tell this story:

1. Open LocalAIAgentStack.
2. Show Open WebUI, OpenHands, LangGraph, Hermes, and LiteLLM running separately.
3. Show RunLedger as a separate control-plane product.
4. Create/select `Local AI Lab` org.
5. Show workspace-scoped keys.
6. Run a chat in Open WebUI.
7. Run a coding task in OpenHands.
8. Run a LangGraph workflow with inline scores/outcomes.
9. Run a Dify/n8n workflow.
10. Run a desktop-agent task through Claude/Codex/Cursor wrapper.
11. Show RunLedger Runs/Sessions/Analytics across all systems.
12. Show budget enforcement.
13. Show Gateway optimization:
    - semantic cache hit
    - compiler saved tokens
    - tool filtering dropped tools
    - intelligent routing selected a cheaper tier
14. Show Experiments comparing cost/quality.
15. Show Outcomes & ROI.
16. Show MCP memory/knowledge/tool filtering from Claude Desktop.

This becomes both a real daily setup and a product-polish lab.

---

## Implementation Phases

### Phase 0 - Baseline Inventory

Tasks:

- Confirm RunLedger stack is healthy.
- Confirm LocalAIAgentStack stack is healthy.
- List current model aliases in LiteLLM.
- Create RunLedger org/workspaces/API keys.
- Import local model pricing.

Exit criteria:

- Both stacks run independently.
- RunLedger has the `Local AI Lab` org and workspaces.
- Keys exist and are stored in LocalAIAgentStack `.env`.

### Phase 1 - LiteLLM Out-Of-Band Telemetry

Tasks:

- Configure LiteLLM OTLP export to RunLedger collector.
- Ensure RunLedger API key/header works for collector path.
- Run traffic from Open WebUI and OpenHands.
- Confirm spans/runs show in RunLedger.

Exit criteria:

- Existing LocalAIAgentStack behavior unchanged.
- RunLedger sees LiteLLM-originated activity.

### Phase 2 - LiteLLM Through RunLedger Gateway

Tasks:

- Add RunLedger-backed LiteLLM aliases.
- Create RunLedger Gateway routes.
- Move Open WebUI model selection to RunLedger-backed alias.
- Move OpenHands to RunLedger-backed alias.

Exit criteria:

- Gateway request logs show Open WebUI/OpenHands traffic.
- Semantic cache and compiler can be demonstrated.

### Phase 3 - LangGraph Inline SDK

Tasks:

- Add RunLedger SDK to LangGraph starter.
- Instrument graph runs/nodes/tools/LLM calls.
- Record outcomes and scores.
- Add experiment comparing two models/routes.

Exit criteria:

- LangGraph runs appear with rich spans.
- Outcomes and eval scores appear in RunLedger.

### Phase 4 - Hermes, Dify, n8n

Tasks:

- Route each through LiteLLM RunLedger-backed aliases.
- Add OTLP where supported.
- Add wrapper-based outcome logging where direct instrumentation is not easy.

Exit criteria:

- Each tool has identifiable traffic in its workspace.
- Cost and success/failure are visible.

### Phase 5 - Desktop Agent Capture

Tasks:

- Connect Claude Desktop to RunLedger MCP.
- Create wrapper scripts for Codex/Cursor/Windsurf/Devin-style tasks.
- Record task metadata, repo, command, result, and outcome.
- Optionally route configurable agents through RunLedger Gateway.

Exit criteria:

- Desktop agent tasks appear under `Desktop Agents`.
- At least one spawned task records outcome and cost.

Detailed desktop agent docs:

- [Desktop Agent Integration Overview](Desktop%20Agent%20Integration%20Overview.md)
- [Devin Integration](Devin%20Integration.md)
- [Windsurf IDE Integration](Windsurf%20IDE%20Integration.md)
- [Cursor IDE Integration](Cursor%20IDE%20Integration.md)
- [Claude Desktop Integration](Claude%20Desktop%20Integration.md)
- [OpenAI Codex IDE Integration](OpenAI%20Codex%20IDE%20Integration.md)

### Phase 6 - Demo Polish

Tasks:

- Create seeded demo workflows.
- Create dashboards/screenshots.
- Create a single runbook.
- Add troubleshooting notes.
- Add cleanup/reset steps.

Exit criteria:

- Demo can be run end-to-end in 15-20 minutes.
- It shows observability, FinOps, optimization, governance, and experiments.

---

## Files To Add Later

In RunLedger repo:

```text
scripts/Integration/
  Integration Plan.md
  runledger-local-ai-env.example
  lite-llm-runledger-snippets.yaml
  desktop-agent-wrapper.ps1
  desktop-agent-wrapper.py
  langgraph-inline-example.py
  demo-runbook.md
```

In LocalAIAgentStack repo:

```text
config/runledger/
  .env.runledger.example
  litellm-runledger-models.yaml
  otel-collector-runledger.yaml
scripts/runledger/
  desktop-agent-wrapper.ps1
  validate-runledger.ps1
  smoke-openwebui-to-runledger.ps1
```

Keep the repos separate, but allow copy/paste snippets from RunLedger into LocalAIAgentStack.

---

## Risks And Decisions

| Risk | Mitigation |
|---|---|
| Tool-specific agents do not expose hooks | Capture through Gateway and wrapper-level outcomes first |
| OTLP headers differ by service | Use collector config or SDK where native OTLP cannot add auth |
| Too many workspaces too early | Start with 8 workspaces, split desktop agents later |
| Local model cost shows `$0` | Maintain Provider Profiles with non-zero local infra pricing |
| Gateway path changes model behavior | Keep direct LiteLLM aliases for fallback and A/B experiments |
| Secrets leak into compose files | Put RunLedger keys in `.env`, keep examples redacted |
| Demo becomes too broad | Build one happy path per tool, then expand |

---

## First Concrete Next Steps

1. Create `Local AI Lab` org in RunLedger.
2. Create workspaces and API keys listed above.
3. Add RunLedger key variables to `LocalAIAgentStack\.env`.
4. Add one LiteLLM alias that points to RunLedger Gateway.
5. Create one RunLedger route `local-chat`.
6. Run Open WebUI through that alias.
7. Confirm RunLedger Gateway request appears.
8. Add one LangGraph inline SDK run with outcome.
9. Add Claude Desktop MCP connection.
10. Turn the process into `scripts/Integration/demo-runbook.md`.

---

## Success Definition

This integration is successful when:

- LocalAIAgentStack remains a separate repo and still runs independently.
- RunLedger has a single org with multiple workspaces and scoped keys.
- Open WebUI, OpenHands, LangGraph, Hermes, Dify/n8n, and desktop agents are visible in RunLedger.
- Some traffic is inline through RunLedger Gateway.
- Some telemetry is out-of-band through OTLP.
- At least one framework has rich inline SDK spans/outcomes.
- Experiments compare model/optimization choices.
- Budgets and route caps can block runaway usage.
- The demo clearly shows RunLedger as a real, useful AI control plane rather than a synthetic dashboard.
