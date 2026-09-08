# Scripts

`scripts/` has one entry point — `run_demo.py` — and seven purpose-named directories.

## Directory layout

```text
scripts/
├── run_demo.py            # master entry point (14 subcommands)
├── core/                  # implementation (not called directly)
│   ├── demo_scenario.py   # canonical scenario definition
│   ├── seed_demo.py       # REST-only quick seed (~30s)
│   ├── full_simulate.py   # broad cluster simulator
│   ├── cleanup.py         # stack reset (truncate or hard wipe)
│   └── scenarios/         # simulation scenario modules
│       ├── ollama/        # local Ollama scenarios (01–07)
│       ├── _base.py       # Sim helper API
│       └── __init__.py    # auto-discovery registry
├── labs/                  # manual lab documentation + hands-on exercises
│   ├── README.md          # workbook index
│   ├── kafka_consumer.py  # Kafka/Redpanda consumer
│   ├── agents/            # lab agent scripts
│   └── samples/           # sample config files
├── configs/               # helper config files
│   ├── pricing.yaml       # Ollama model pricing catalog
│   ├── pricing.sample.yaml
│   └── restore.sh
├── mcp/                   # MCP stdio bridge and validation
│   ├── mcp_stdio_bridge.py
│   ├── mcp_bridge.bat
│   └── validate_mcp_connection.py
├── localai/               # LocalAI Agent Stack integration
│   ├── bootstrap_runledger_org.py
│   ├── inject_mcp_configs.py
│   ├── generate_agent_traffic.py
│   ├── generate_otlp_traffic.py
│   └── localai_s3_backup.py
├── integrations/          # integration guides (Devin, Windsurf, Cursor, Claude, Codex)
└── bench/                 # gateway benchmarking
    ├── run_benchmark.py
    └── report.py
```

## Canonical scenario

All manual labs and the normalized quick seed share one foundation:

- Platform admin: `admin@runledger.local` / `runledger`
- Org 1: `HomeLab`
  - Admin: `admin@homelab.com`
  - Users: `user1@homelab.com`, `user2@homelab.com`
  - Workspace: `AgentTest`
- Org 2: `LocalAIAgentStack`
  - Admin: `admin@localstack.com`
  - Users: `user1@localstack.com`, `user2@localstack.com`
  - Workspaces: `LiteLLM Gateway`, `OpenWebUI`, `Codex`, `Langgraph`, `HermesAgent`, `Claude Desktop`, `OpenAICodes`, `PythonAgents`

Every local account in this scenario uses password `runledger`.

## Master entry point — `run_demo.py`

All operations go through a single script with 14 subcommands:

### Setup & Seed

```bash
python scripts/run_demo.py scenario          # print canonical scenario
python scripts/run_demo.py cleanup            # truncate data (preserves admin + pricing)
python scripts/run_demo.py cleanup --hard     # wipe ALL volumes
python scripts/run_demo.py seed-demo          # REST demo seed (quick, ~30s)
python scripts/run_demo.py full-simulate      # full cluster simulation
python scripts/run_demo.py all                # cleanup → seed-demo
python scripts/run_demo.py all --full         # cleanup → full-simulate
python scripts/run_demo.py labs               # print labs workbook path
```

### Traffic & Agents

```bash
python scripts/run_demo.py traffic                     # generate agent traffic (batch mode)
python scripts/run_demo.py traffic --continuous         # continuous traffic loop (Ctrl+C to stop)
python scripts/run_demo.py traffic --workspace "LiteLLM Gateway" --source litellm-localai
python scripts/run_demo.py otlp-traffic                # generate OTLP trace traffic
python scripts/run_demo.py otlp-traffic --workspace "Open WebUI" --source open-webui-otel
```

### Gateway & Bench

```bash
python scripts/run_demo.py bench --api-key rl_... --alias chat-balanced
python scripts/run_demo.py bench-report --api-key rl_...
```

### Integrations

```bash
python scripts/run_demo.py localai            # bootstrap LocalAI Agent Stack org
python scripts/run_demo.py localai --inject   # also inject MCP configs into Claude/Codex
python scripts/run_demo.py mcp-validate       # validate MCP endpoint connectivity
python scripts/run_demo.py kafka              # consume Kafka/Redpanda events
python scripts/run_demo.py backup             # S3 backup
python scripts/run_demo.py backup --restore --confirm   # S3 restore
python scripts/run_demo.py backup --list      # list existing backups
```

## Which path to use

| Path | Use it for |
|---|---|
| `run_demo.py all` | One-shot pipeline: cleanup → seed |
| `run_demo.py all --full` | One-shot pipeline: cleanup → full-simulate |
| `run_demo.py seed-demo` | Fast UI and admin validation against the fixed HomeLab + LocalAIAgentStack layout |
| `run_demo.py full-simulate` | Broad synthetic traffic, observability depth, and richer cross-surface demo data |
| `run_demo.py traffic --continuous` | Keep dashboards moving with indefinite agent traffic |
| `run_demo.py cleanup` | Reset the stack to a blank slate |
| [`labs/README.md`](./labs/README.md) | Manual operator training with the same org/user/workspace story |
| [`core/scenarios/README.md`](./core/scenarios/README.md) | Scenario library, simulator notes, and helper API reference |
| [`integrations/`](./integrations) | Integration guides for Devin, Windsurf, Cursor, Claude Desktop, Codex |
| [`localai/`](./localai) | LocalAI Agent Stack helpers (bootstrap, traffic, backup) |
| [`mcp/`](./mcp) | MCP stdio bridge and validation |
| [`bench/`](./bench) | Gateway benchmark and reporting |
| [`configs/`](./configs) | Pricing catalog and restore helper |

## What `full-simulate` does

One command turns an empty stack into a fully-populated demo:

```bash
python scripts/run_demo.py full-simulate
python scripts/run_demo.py full-simulate -- --hard-clean
python scripts/run_demo.py full-simulate -- --no-clean
python scripts/run_demo.py full-simulate -- --traffic-multiplier 5
python scripts/run_demo.py full-simulate -- --scenario-set all
python scripts/run_demo.py full-simulate -- --streaming-demo
```

Step by step:

1. **Reset** — truncates all data (preserves admin + provider pricing), or `--hard-clean` wipes every volume.
2. **Bootstrap** — creates / promotes the platform admin (`admin@runledger.local` / `runledger`).
3. **Import pricing** — uploads [`configs/pricing.yaml`](./configs/pricing.yaml) to the provider-pricing catalog, so cost is tracked for local Ollama models.
4. **Run local scenarios** — discovers [`core/scenarios/ollama`](./core/scenarios/ollama) by default and runs them with a 3x traffic multiplier. Each scenario creates its own org, logs in as the org admin, mints a workspace API key, and fills the workspace via the API: gateway routes, runs, budgets, outcomes, scores, alerts, approval requests, chargeback rules, auto-approval policies, runbooks, and guardrails.
5. **Seed governance & finops** — triggers a governance audit pack export across all workspaces.
6. **Seed guardrails** — activates baseline content filters across all workspaces.
7. **Expand demo breadth** — seeds richer control-plane and operator data across applications, teams, agent workflows, tool policies, MCP permissions, approval decisions, email settings, backup settings, OTLP traces, intents, outcomes, and savings categories.
8. **Summary** — prints each workspace, its API key, and run count.

When `--streaming-demo` is enabled, the simulator also seeds a single-topic Kafka export config per workspace aimed at `runledger-redpanda:9092`.

Everything goes through the **public REST API** — no direct database writes — so it exercises the real ingest / metering / budgets / outcomes paths. Cost enrichment and rollups run on Celery, so give analytics ~60s to populate.

## Pricing local models

[`configs/pricing.yaml`](./configs/pricing.yaml) assigns a **small per-1M-token cost to Ollama models**
(representing GPU / electricity / infra spend), so local inference accrues real, trackable spend.
The file contains no hosted-provider rows. The simulator imports it into Provider Profiles
**and** uses it to compute each ingested run's cost. Tune the numbers to your hardware.

## Demo accounts and passwords

| Account | Password | Purpose |
|---|---|---|
| `admin@runledger.local` | `runledger` | Default platform admin. |
| `admin@<scenario-slug>.example.com` | `Sim-Passw0rd!` | Org admin created for each scenario org. |
| `admin@localai-agent-stack.example.com` | `LocalAIStack123!` | Org admin created by `run_demo.py localai`. |

If your local database already has a different platform admin, pass it explicitly:

```powershell
python scripts\run_demo.py full-simulate -- --admin-email admin@homelab.com --admin-password Dell1234
python scripts\run_demo.py localai --base-url http://localhost:8201
```

## Local deployment profiles

```text
docker compose up -d                                    # core control plane
docker compose --profile aux up -d                      # optimization and agentic sidecars
docker compose --profile backup up -d runledger-minio   # local S3-compatible target
docker compose --profile observability up -d runledger-otel-collector  # OTEL collector
docker compose --profile streaming up -d runledger-redpanda runledger-redpanda-console  # Kafka event bus
docker compose --profile tls-demo up -d runledger-caddy # local HTTPS demo proxy
docker compose --profile full-demo up -d                # all optional services together
```

Default local endpoints:

| Service | Endpoint |
|---|---|
| MinIO S3 API | `http://localhost:9010` |
| MinIO Console | `http://localhost:9011` |
| OTLP/gRPC | `http://localhost:4317` |
| OTLP/HTTP | `http://localhost:4318` |
| Collector health | `http://localhost:13133` |

The shipped collector expects `Authorization: Bearer <workspace-api-key>` on inbound OTLP traffic and forwards the same workspace API key upstream to RunLedger.

## LocalAI Agent Stack integration

Use this when you want RunLedger to act as the control plane for the separate
`LocalAIAgentStack` repo.

### 1. Create the RunLedger org and workspace keys

```powershell
python scripts\run_demo.py localai
```

This creates one org named `LocalAI Agent Stack` with workspaces for LiteLLM Gateway,
Open WebUI, OpenHands, LangGraph, Hermes Agent, Claude Desktop, OpenAI Codex,
Python Console, and Backup Restore Lab.

### 2. Configure Claude Desktop and Codex MCP

```powershell
python scripts\run_demo.py localai --inject
```

This backs up and updates `claude_desktop_config.json` and `.codex/config.toml`,
adding a `runledger` MCP server that launches `scripts/mcp/mcp_stdio_bridge.py`.

After the API has been rebuilt/restarted, validate the MCP endpoint:

```powershell
python scripts\run_demo.py mcp-validate
```

### 3. Use LocalAIStack MinIO as S3 backup storage

```powershell
python scripts\run_demo.py backup              # take a backup
python scripts\run_demo.py backup --list       # list existing backups
python scripts\run_demo.py backup --restore --confirm  # restore (destructive)
```

### 4. Generate traffic continuously

```powershell
python scripts\run_demo.py traffic --continuous --workspace "Python Console" --source python-console
python scripts\run_demo.py traffic --continuous --workspace "LiteLLM Gateway" --source litellm-localai
python scripts\run_demo.py otlp-traffic --workspace "Open WebUI" --source open-webui-otel
```

### Inline vs out-of-band for Claude and Codex

| Path | Works for Claude/Codex? | What RunLedger gets |
|---|---:|---|
| MCP | Yes | Budget checks, analytics lookup, policy/tool filtering, optimization helpers. |
| SDK/wrapper scripts | Yes | Task lifecycle, command spans, outcomes, repo metadata. |
| OTLP/out-of-band | Yes | Trace spans emitted by local tools/processes. |
| Gateway inline | Only for subprocesses with custom `base_url` | True request-path routing, budgets, caching, and model controls. |

## Adding scenarios

Scenarios live under [`core/scenarios/`](./core/scenarios) — see [`core/scenarios/README.md`](./core/scenarios/README.md).
Create a module exposing `NAME` + `run(sim)`, and it's picked up automatically:

```python
# scripts/core/scenarios/ollama/05_my_scenario.py
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
