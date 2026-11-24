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

Org admins and users in this scenario use password `runledger-demo-1` (the API password policy requires at least 12 characters with a letter and a digit). The platform admin is seeded directly and keeps `runledger`.

## Master entry point — `run_demo.py`

All operations go through a single script with 14 subcommands:

### Setup & Seed

```bash
python scripts/run_demo.py scenario          # print canonical scenario
python scripts/run_demo.py cleanup            # truncate data (preserves admin + pricing)
python scripts/run_demo.py cleanup --hard     # wipe ALL volumes
python scripts/run_demo.py seed-demo          # REST demo seed (quick, ~30s)
python scripts/run_demo.py verify-org-access  # assert org/invite/session/lockout controls
python scripts/run_demo.py verify-budgets     # assert scoped budget counting + enforcement
python scripts/run_demo.py verify-ingestion   # assert ingest limits, dead letters, OTLP, signing, SSRF
python scripts/run_demo.py verify-api-health  # every dashboard read endpoint returns without a 5xx
python scripts/run_demo.py verify-billing     # periods, close/reopen, chargeback rules, shared costs, signing
python scripts/run_demo.py verify-security    # critical security fixes (guardrail logic sandbox, …)
python scripts/run_demo.py verify-gateway-runtime --bench  # in-process gateway checks + p50/p99 (needs DATABASE_URL, REDIS_URL)
python scripts/run_demo.py verify-gateway-admin  # role matrix, route/policy invariants, tiers, audit
python scripts/run_demo.py verify-workflows   # workflow attribution, page data, agent envelope, archive
python scripts/run_demo.py verify-observe     # runs, explorer, flow, sessions, outcomes, live stream
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
| `run_demo.py verify-org-access` | Asserts Org & Access controls end to end: temporary passwords, password policy, pending invitations, cross-org identity guard, session revocation, audit events, viewer/editor write enforcement, API key scopes, platform-only backups and pricing import, cross-org ingest isolation, closed unauthenticated surfaces, sign-in throttling (creates and deletes two throwaway orgs) |
| `run_demo.py verify-budgets` | Asserts scoped budgets end to end: priced ingest calls counted exactly once against feature-tag, end-user and API-key budgets, retries not double counted, one breach recorded, `/budgets/check` blocks the exhausted workflow. With `--gateway-url` and `--alias`, also expects the gateway to return 429. Needs the pipeline worker running |
| `run_demo.py verify-security` | Asserts the critical security fixes: guardrail logic runs in RunLedger's own interpreter (escapes refused on save, valid block/modify rules and the PII template work). Grows as fixes land |
| `run_demo.py verify-gateway-runtime` | In process, against a throwaway Postgres + Redis (no Docker stack): preflight decision trace and `X-RunLedger-Decision`, prompt refs, `run_id`/`api_key_id`/`workflow` attribution on requests and guardrail events, the single cache profile and its counters, pass-through governance and no redirects. `--bench` adds SQL-per-request and p50/p99 thresholds (CI job `gateway-bench`) |
| `run_demo.py verify-gateway-admin` | Asserts gateway administration: the role matrix (workload keys can't change routes), alias/group invariants (400/409), merge-mode route edits keep unsent config keys, preview-change saves nothing, the test-request dry run picks the route, policies can't name another alias's route, unknown policy types are refused, budget tier limits clear with null and delete is a soft delete, and every change is in the audit log. `--gateway-url` also asserts a tier's allowed_models is enforced (403) |
| `run_demo.py verify-workflows` | Asserts the workflow spine (28 checks, 31 with `--gateway-url` and `--alias`): existing tagged runs link when a workflow is created; duplicate tags (409) and unknown aliases (422) are refused; runs are attributed by header, explicit id, feature tag and OTLP attribute, never by a foreign id; cost by step rolls up from model calls; the health card, list stats and related drawer agree; agent stats come from attributed runs; the agent preflight refuses a spent envelope, an alias outside the allow-list (unknown aliases refused on save) and a paused agent, and gateway-rs returns the same 429/403 with `X-Agent-Policy-Reason`; archive stops matching and restore re-links |
| `run_demo.py verify-observe` | Ingests three runs for a unique workflow and asserts Runs (cursor, 422 on bad status, stats, export filters, facets), Request Explorer status/workflow filters, Sessions, Outcomes (SDK outcomes visible, cost counted once per run), Request Flow (recorded savings only), the API success rate, payload redaction for read-only keys, compare, saved views, the SSE stream and a monitoring feed |
| `run_demo.py verify-billing` | Creates a throwaway org with two admins and priced usage for three workflows, then asserts billing end to end: period overlap/date validation, cost-center tree and cycle guard, chargeback rules (weights ≤ 1, one dimension, direct = weight 1), separation of duties on approval-gated rules, one billable-cost definition (failed-but-charged calls count), the cost-center report, shared-cost apply/replace, CSV formula escaping and the end-user export filter, adjustment actor, locked close with frozen lines (late usage doesn't change a closed bill; reconciliation flags it), signed-export verification (online, offline, tampered, other workspace), reopen + re-close, and signing-key rotation. Deletes the org unless `-- --keep` |
| `run_demo.py verify-api-health` | Signs in as the platform admin and sends GET to every route in the OpenAPI spec without path or required query parameters (analytics views, settings, lists) plus `GET /context`; fails on any 5xx. Catches stale column names, missing tables and response-schema mismatches. `-- --prefix /analytics` narrows it |
| `run_demo.py verify-ingestion` | Asserts Ingestion & Integrations end to end: batch and body limits, one bad event dead-lettered without dropping its batch (replay, discard), idempotent tool calls, status normalization, OTLP gating (dropped vs runs), protobuf, gzip-bomb refusal, raw payload not stored, signed ingest (nonce replay, bad signature), SSRF refusals, `POST /mcp` without redirect. Needs both Celery workers |
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

When `--streaming-demo` is enabled, the simulator also seeds a single-topic Kafka export config per workspace aimed at `runledger-redpanda:9092`; start the broker first with `docker compose --profile streaming up -d`.

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
docker compose up -d                       # full stack (control plane, sidecars, MinIO, collector, Caddy)
docker compose --profile streaming up -d   # plus Redpanda + console for Kafka export
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
