# Script Normalization Working Plan

This is a local planning document intentionally kept out of git.

## Goal

Normalize the repo's script surfaces into one coherent demo/control-plane automation system:

- one master runner
- one canonical demo topology
- one place for seed logic
- one place for simulation logic
- one place for infra helpers
- one place for external local-stack integrations
- one place for manual labs

## Primary Refactor Moves

1. Create `scripts/run_demo.py`
2. Move `apps/api/scripts/seed_demo.py` to `scripts/seed/seed_quick.py`
3. Move `scripts/full_simulate.py` to `scripts/simulate/full_simulate.py`
4. Add compatibility shims at old paths
5. Create `scripts/seed/core.py`
6. Create `scripts/seed/catalog.py`
7. Create `scripts/seed/local_models.py`
8. Create `scripts/simulate/traffic/`
9. Create `scripts/simulate/features/`
10. Create `scripts/integrations/localaiagentstack/`
11. Split `scripts/scenarios/` into:
   - `manifests/`
   - `automated/`
   - `labs/`

## Canonical Topology

- Platform admin: `admin@runledger.local`
- Password: `runledger`

### Org 1

- Name: `HomeLab`
- Admin: `admin@homelab.com`
- Users:
  - `user1@homelab.com`
  - `user2@homelab.com`
- Workspace:
  - `AgentTest`

### Org 2

- Name: `LocalAIAgentStack`
- Admin: `admin@localstack.com`
- Users:
  - `user1@localstack.com`
  - `user2@localstack.com`
- Workspaces:
  - `LiteLLM Gateway`
  - `OpenWebUI`
  - `Codex`
  - `Langgraph`
  - `HermesAgent`
  - `Claude Desktop`
  - `OpenAICodes`
  - `PythonAgents`

## Phase Plan

### Phase 1

- create script runtime library under `scripts/lib`
- move quick seed
- add `run_demo.py`
- add manifest file for canonical topology

### Phase 2

- extract core identity seeding
- extract pricing import and local model discovery
- create one API key per workspace
- persist local manifest output

### Phase 3

- refactor `full_simulate` onto shared runtime
- split breadth seeding from traffic generation
- preserve all current feature breadth

### Phase 4

- add per-feature simulations:
  - gateway
  - budgets
  - approvals
  - prompts/evals
  - alerts
  - data capture
  - backup
  - kafka
  - mcp

### Phase 5

- add LocalAIAgentStack integration runners
- add HomeLab Python agent traffic runner
- add long-running continuous traffic modes

### Phase 6

- align labs to features
- ensure every major feature has:
  - manual lab
  - seed/sim script
  - infra bring-up path
  - verify script

## Non-Negotiables

- do not lose current `full_simulate` breadth
- keep demo scripts REST/API-driven rather than direct DB writes
- keep labs manual and operator-oriented
- stop adding product demo logic under `apps/api/scripts/`
- keep runtime/container startup helpers in `apps/api/scripts/` only when they are image-specific
