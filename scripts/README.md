# RunLedger scripts

Utilities for running, resetting, and populating a RunLedger stack.

## Demo modes at a glance

There are now three cohesive demo paths:

1. `Full Simulator`: [full_simulate.py](./full_simulate.py) is the primary automated demo and the default Phase 13 one-click path in the dashboard.
2. `Quick Seed`: [../apps/api/scripts/seed_demo.py](../apps/api/scripts/seed_demo.py) is the lighter REST-only seed used when you want broad feature coverage fast.
3. `Hands-on Labs`: [scenarios/labs/README.md](./scenarios/labs/README.md) is the manual workbook for guided operator-style walkthroughs.
4. `Streaming Demo`: [streaming/kafka_consumer.py](./streaming/kafka_consumer.py) consumes live Kafka events from the bundled Redpanda profile.

Supporting demo assets live alongside those entrypoints:

- [scenarios/labs/guided_demo_scenarios.md](./scenarios/labs/guided_demo_scenarios.md) for presenter-friendly before/after stories
- [scenarios/labs/sales_engineering_walkthrough.md](./scenarios/labs/sales_engineering_walkthrough.md) for the 12-20 minute sales/demo narrative
- [../docs/demo-visual-regression.md](../docs/demo-visual-regression.md) for replayable dashboard screenshot and visual review checkpoints

| Script | What it does |
|---|---|
| [`full_simulate.py`](./full_simulate.py) | Reset the cluster, then populate it with high-volume local Ollama demo data **through the REST API**. |
| [`cleanup.py`](./cleanup.py) | Reset to a blank slate - truncate data (default) or wipe every volume (`--hard`). |
| [`pricing.yaml`](./pricing.yaml) | The simulation pricing catalog - **Ollama-only** local model pricing for the demo. |
| [`scenarios/`](./scenarios) | The scenario library, organized in folders (`ollama/` by default, `hosted/` opt-in). |
| [`generate_postman.py`](./generate_postman.py) | Regenerate the Postman collection from the live OpenAPI spec. |
| [`restore.sh`](./restore.sh) | Restore stores from an S3 backup (companion to the Helm backup CronJob). |
| [`bench/`](./bench) | Optimization benchmark harness (baseline vs optimized). |
| [`localai/`](./localai) | LocalAI Agent Stack integration helpers: org bootstrap, S3 backup/restore, MCP config injection, SDK-style traffic, and OTLP trace generation. |
| [`streaming/`](./streaming) | Kafka/Redpanda local consumer helpers for the streaming export demo. |

## Local backup profile

RunLedger now includes a local MinIO-backed backup profile:

```bash
docker compose --profile backup up -d runledger-minio
```

Default local endpoints:

- S3 API: `http://localhost:9010`
- Console: `http://localhost:9011`

## Local observability profile

RunLedger also includes a dedicated local observability profile for the bundled OTel Collector:

```bash
docker compose --profile observability up -d runledger-otel-collector
```

Default local endpoints:

- OTLP/gRPC: `http://localhost:4317`
- OTLP/HTTP: `http://localhost:4318`
- Collector health: `http://localhost:13133`
- Collector self-metrics: `http://localhost:8888/metrics`
- Collector span metrics: `http://localhost:8889/metrics`

The legacy `otel` profile name is still accepted, but `observability` is the canonical profile going forward.
The shipped collector expects `Authorization: Bearer <workspace-api-key>` on inbound OTLP traffic and forwards the same workspace API key upstream to RunLedger.

## Local deployment profiles

RunLedger now has a clearer local profile split:

- `docker compose up -d` → core control plane
- `docker compose --profile aux up -d` → optimization and agentic sidecars
- `docker compose --profile backup up -d runledger-minio` → local S3-compatible target
- `docker compose --profile observability up -d runledger-otel-collector` → OTEL collector
- `docker compose --profile streaming up -d runledger-redpanda runledger-redpanda-console` → Kafka-compatible event bus demo
- `docker compose --profile tls-demo up -d runledger-caddy` → local HTTPS demo proxy
- `docker compose --profile full-demo up -d` → all optional demo services together

## What `full_simulate.py` does

One command turns an empty stack into a fully-populated demo, and it is the recommended automated profile:

```bash
uv run python scripts/full_simulate.py            # reset -> bootstrap -> import local pricing -> run Ollama scenarios x3
uv run python scripts/full_simulate.py --hard-clean  # wipe every volume first (Qdrant, memory, ...)
uv run python scripts/full_simulate.py --no-clean    # add on top of existing data
uv run python scripts/full_simulate.py --traffic-multiplier 5
uv run python scripts/full_simulate.py --scenario-set all  # intentionally include hosted examples
uv run python scripts/full_simulate.py --streaming-demo     # also seed Kafka/Redpanda exports
```

Step by step:

1. **Reset** - truncates all data by default (preserves admin + provider pricing), or `--hard-clean` wipes every volume.
2. **Bootstrap** - creates / promotes the platform admin (`admin@runledger.local` / `runledger`).
3. **Import pricing** - uploads [`pricing.yaml`](./pricing.yaml) to the provider-pricing catalog, so cost is tracked - including for local Ollama models.
4. **Run local scenarios** - discovers the [`scenarios/ollama`](./scenarios/ollama) scenarios by default and runs them with a 3x traffic multiplier. Each scenario creates its own org via `/org/tenants`, logs in as the seeded org admin for management actions, mints a workspace API key from `/settings/api-keys`, and fills the workspace via the API: gateway routes, runs (`/ingest/v1/batch`), budgets, outcomes, scores, alerts, approval requests, chargeback rules, auto-approval policies, runbooks, and guardrails.
5. **Seed governance & finops** - triggers a governance audit pack export across all workspaces.
6. **Seed guardrails** - activates baseline content filters (code injection, data exfiltration, toxicity, violence, self-harm, child safety) across all workspaces.
7. **Expand demo breadth** - seeds richer control-plane and operator data across applications, teams, team-model mappings, agent workflows, tool policies, MCP permissions, approval decisions, email settings/history, backup settings/history, OTLP traces, intents, outcomes, and savings categories.
8. **Summary** - prints each workspace, its API key, and run count.

When `--streaming-demo` is enabled, the simulator also seeds a single-topic Kafka export config per workspace aimed at `runledger-redpanda:9092` so the `streaming` and `full-demo` Compose profiles can show live event fanout immediately.

Everything goes through the **public REST API** exactly as a real client would - no direct database writes - so it exercises the real ingest / metering / budgets / outcomes paths. Cost enrichment and rollups run on Celery, so give analytics ~60s to populate.

## Demo accounts and passwords

These are local/demo credentials used by the simulator. They are intentionally documented here so a fresh demo stack is easy to operate.

| Account | Password | Purpose |
|---|---|---|
| `admin@runledger.local` | `runledger` | Default platform admin created by `full_simulate.py`. |
| `admin@<scenario-slug>.example.com` | `Sim-Passw0rd!` | Org admin created for each scenario org. Example: `admin@helpdesk-local.example.com`. |
| `admin@localai-agent-stack.example.com` | `LocalAIStack123!` | Org admin created by `scripts/localai/bootstrap_runledger_org.py`. |

If your local database already has a different platform admin, pass it explicitly:

```powershell
python scripts\full_simulate.py --admin-email admin@homelab.com --admin-password Dell1234
python scripts\localai\bootstrap_runledger_org.py --platform-email admin@homelab.com --platform-password Dell1234
```

The workspace API keys generated by the LocalAI bootstrap are **not** committed. They are written to ignored local files:

```text
scripts/.localai-runledger.json
C:\Users\Abi\Desktop\LocalAIAgentStack\config\runledger\runledger.env
```

## Pricing local models

By default RunLedger can price local models at `$0` (see `config/pricing.yml`). For the simulator,
[`scripts/pricing.yaml`](./pricing.yaml) assigns a **small per-1M-token cost to Ollama models**
(representing GPU / electricity / infra spend), so local inference accrues real, trackable spend.
The file intentionally contains no OpenAI, Anthropic, Gemini, or other hosted-provider rows. It is the
single source of truth: `full_simulate` imports it into Provider Profiles **and** uses it to compute each
ingested run's cost. Tune the numbers to your hardware.

## LocalAI Agent Stack integration

Use this when you want RunLedger to act as the control plane for the separate
`C:\Users\Abi\Desktop\LocalAIAgentStack` repo.

### 1. Create the RunLedger org and workspace keys

```powershell
python scripts\localai\bootstrap_runledger_org.py
```

This creates one org named `LocalAI Agent Stack` with these workspaces:

| Workspace | Intended use |
|---|---|
| `LiteLLM Gateway` | Inline gateway traffic from LiteLLM/OpenAI-compatible clients. |
| `Open WebUI` | Chat UI telemetry and SDK/OTLP traffic. |
| `OpenHands` | Coding-agent runs, commands, and task outcomes. |
| `LangGraph` | Graph/node spans, tool calls, and workflow outcomes. |
| `Hermes Agent` | Hermes task traffic and tool-use telemetry. |
| `Claude Desktop` | MCP/out-of-band logging for Claude Desktop. |
| `OpenAI Codex` | MCP/out-of-band logging for Codex. |
| `Python Console` | Ad-hoc Python experiments and traffic generation. |
| `Backup Restore Lab` | S3 backup/restore and disaster-recovery drills. |

The script also writes a private env file into the LocalAIStack repo:

```text
C:\Users\Abi\Desktop\LocalAIAgentStack\config\runledger\runledger.env
```

### 2. Configure Claude Desktop and Codex MCP

```powershell
python scripts\localai\inject_mcp_configs.py
```

This backs up and updates:

```text
C:\Users\Abi\AppData\Roaming\Claude\claude_desktop_config.json
C:\Users\Abi\.codex\config.toml
```

It adds a `runledger` MCP server that launches:

```text
scripts/runledger/mcp_stdio_bridge.py
```

The bridge forwards stdio MCP JSON-RPC to the RunLedger HTTP MCP endpoint and injects the correct workspace API key.

Restart Claude Desktop and Codex after running the injection script.

After the API image has been rebuilt/restarted, validate the canonical RunLedger MCP control-plane endpoint:

```powershell
$env:RUNLEDGER_API_KEY = "<workspace-api-key>"
python scripts\runledger\validate_mcp_connection.py
```

This checks `http://localhost:8201/mcp` and confirms the Phase 1A `runledger.*` tools are visible.
The separate `http://localhost:8206/mcp` service is the optimization/cognitive MCP gateway for context,
memory, knowledge graph, skill registry, and flywheel tools.

### 3. Use LocalAIStack MinIO as S3 backup storage

LocalAIStack already exposes Langfuse MinIO:

```text
S3 endpoint: http://localhost:3021
Console: http://localhost:3022
Username: minio
Password: langfuse-minio-local
Bucket used by RunLedger: runledger-backups
```

Prepare the bucket and take a local backup:

```powershell
cd C:\Users\Abi\Desktop\LocalAIAgentStack
docker compose up -d langfuse-minio

cd C:\Users\Abi\Desktop\github\runledger-community
python scripts\localai\localai_s3_backup.py ensure-bucket
python scripts\localai\localai_s3_backup.py backup
python scripts\localai\localai_s3_backup.py list
```

Restore is intentionally guarded because it rewrites local databases:

```powershell
python scripts\localai\localai_s3_backup.py restore --confirm-restore
```

After restore, restart RunLedger API/worker/beat so every process sees the restored state.

### 4. Generate LocalAI traffic continuously

Use this to keep dashboards, Request Flow, Model Usage, Runs, Outcomes, and FinOps views moving:

```powershell
python scripts\localai\generate_agent_traffic.py --workspace "Python Console" --source python-console --batches 20 --batch-size 25 --sleep 2
python scripts\localai\generate_agent_traffic.py --workspace "LiteLLM Gateway" --source litellm-localai --batches 20 --batch-size 25 --sleep 2
python scripts\localai\generate_agent_traffic.py --workspace "OpenHands" --source openhands --batches 20 --batch-size 20 --sleep 3
```

Use this to populate the OTLP page and validate out-of-band OpenTelemetry ingestion:

```powershell
python scripts\localai\generate_otlp_traffic.py --workspace "Open WebUI" --source open-webui-otel --batches 3 --traces 40 --sleep 1
python scripts\localai\generate_otlp_traffic.py --workspace "LiteLLM Gateway" --source litellm-otel --batches 3 --traces 40 --sleep 1
```

This posts OTLP/HTTP JSON to `/v1/traces` and creates raw trace batches, spans, and canonical RunLedger events for the selected workspace.

### Inline vs out-of-band for Claude and Codex

Inline RunLedger control is possible when a tool can point its model calls at an OpenAI-compatible base URL, for example:

```text
http://localhost:8201/gateway
```

That works well for Python clients, LiteLLM, Open WebUI, OpenHands, LangGraph, and any SDK/client where you control `base_url`.

Claude Desktop and Codex are different: their native hosted model calls are not generally routed through a user-configurable OpenAI-compatible base URL. That means RunLedger cannot intercept every token inline for those built-in model calls. The practical integration is:

| Path | Works for Claude/Codex? | What RunLedger gets |
|---|---:|---|
| MCP | Yes | Budget checks, analytics lookup, policy/tool filtering, optimization helpers. |
| SDK/wrapper scripts | Yes | Task lifecycle, command spans, outcomes, repo metadata. |
| OTLP/out-of-band | Yes | Trace spans emitted by local tools/processes. |
| Gateway inline | Only for subprocesses/tools that support custom `base_url` | True request-path routing, budgets, caching, and model controls. |

To showcase true inline interception for a demo, run a Python/OpenAI-compatible client through:

```text
RUNLEDGER_GATEWAY_BASE_URL=http://localhost:8201/gateway
```

## Adding scenarios

Scenarios live in folders under [`scenarios/`](./scenarios) - see [`scenarios/README.md`](./scenarios/README.md).
Create a folder (with an `__init__.py`), drop in a module exposing `NAME` + `run(sim)`, and it's picked up
automatically:

```python
# scripts/scenarios/ollama/05_my_scenario.py
from scenarios._base import Sim

NAME = "my-scenario"
DESCRIPTION = "One line describing it."

def run(sim: Sim) -> None:
    ws = sim.workspace("My Org", "My Workspace")
    ws.add_route("chat", "llama3.1:8b", base_url="http://host.docker.internal:11434/v1")
    runs = ws.ingest_runs(100, models=["llama3.1:8b"], features=["chat"], users=["u_1"])
    for r in runs:
        ws.record_outcome(r, "resolved", value_usd=6.0)
        ws.score(r, "quality", 0.9)
```
