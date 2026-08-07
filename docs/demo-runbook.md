# RunLedger Demo Runbook

This runbook explains how Phase 13 demo mode maps to the existing script surfaces in the repo.

## Demo Profiles

### Full Simulator

`Full Simulator` is the recommended automated path. It runs [scripts/full_simulate.py](C:/Users/Abi/Desktop/github/runledger-community/scripts/full_simulate.py) and keeps the richest existing demo story intact:

- multi-org and multi-workspace scenario seeding
- local Ollama traffic and pricing import
- Phase 13 governance and finops data
- Phase 14 guardrails
- Phase 15 intelligence and forecasting
- Phase 16 agentic operations
- richer demo entities across apps, teams, team models, tool policies, MCP permissions, approvals, email, backups, traces, intents, outcomes, and savings categories

### Quick Seed

`Quick Seed` runs [apps/api/scripts/seed_demo.py](C:/Users/Abi/Desktop/github/runledger-community/apps/api/scripts/seed_demo.py).

It is the lighter REST-only feature seed. It creates:

- synthetic enterprise organizations and workspaces
- realistic AI runs, traces, prompts, budgets, alerts, outcomes, approvals, and analytics
- gateway routes, tool registry entries, replay assets, and governance examples

### Hands-on Labs

`Hands-on Labs` is the manual path documented in [scripts/scenarios/labs/README.md](C:/Users/Abi/Desktop/github/runledger-community/scripts/scenarios/labs/README.md).

Use it when you want to walk through the product intentionally instead of auto-seeding everything.

For guided presenter-friendly stories, pair demo mode with:

- [Guided Demo Scenarios](C:/Users/Abi/Desktop/github/runledger-community/scripts/scenarios/labs/guided_demo_scenarios.md)
- [Sales Engineering Walkthrough](C:/Users/Abi/Desktop/github/runledger-community/scripts/scenarios/labs/sales_engineering_walkthrough.md)
- [Demo Visual Regression](C:/Users/Abi/Desktop/github/runledger-community/docs/demo-visual-regression.md)

## Before You Start

- Make sure the API and web app are running
- Log in as a platform admin
- Keep the current default local credentials handy:
  - `admin@runledger.local / runledger`
  - demo users created by the seeder use `demo1234`

## Seed Demo Data

1. Open the onboarding page in the dashboard.
2. In `Demo Mode`, choose `Full Simulator` or `Quick Seed`.
3. Click `Seed Demo Data`.
4. Watch the status badge until it moves from `queued` or `running` to `completed`.
5. Refresh key product pages like `Dashboard`, `Runs`, `Gateway`, `Approvals`, `Runbooks`, and `Analytics`.

`Full Simulator` is the default because it preserves the broader scenario coverage already encoded in `full_simulate.py`.
It also now seeds cross-surface demo data so `Settings`, `Tools`, `MCP`, `Approvals`, and backup/email admin flows have meaningful records immediately.
Both automated profiles are replay-safe: they reset demo data before reseeding so a presenter can get back to a known state quickly.

## Tell The Story

Use this simple before/after sequence for a coherent seeded narrative:

1. Open `Dashboard` and `Request Flow` to show where cost and latency pressure exists.
2. Open `Cost & Savings` and `Optimization Opportunities` to show what RunLedger improved or recommends next.
3. Open `Gateway` to show the control surface for routing, cache, and prompt optimization.
4. Open `Approvals`, `MCP`, and `Runbooks` to show governance, tool control, and operator workflows.

The most reusable scripted paths live in [guided_demo_scenarios.md](C:/Users/Abi/Desktop/github/runledger-community/scripts/scenarios/labs/guided_demo_scenarios.md), which covers cache optimization, routing savings, prompt compression, local summarization, budget incidents, and MCP filtering.

## Open The Labs Workbook

1. Open the onboarding page in the dashboard.
2. In `Demo Mode`, click `Open labs workbook`.
3. Follow the workbook from Module 0 onward.

## Reset Demo Data

`Reset Demo Data` runs the soft cleanup flow. It:

- truncates seeded data tables
- preserves admin access and provider pricing
- flushes Redis state

It uses the default cleanup path from [scripts/cleanup.py](C:/Users/Abi/Desktop/github/runledger-community/scripts/cleanup.py).

Use this when you want to re-seed without rebuilding the full stack.

If you want to replay the polished story exactly, the safest sequence is:

1. `Reset Demo Data`
2. `Seed Demo Data`
3. Wait for completion
4. Follow [sales_engineering_walkthrough.md](C:/Users/Abi/Desktop/github/runledger-community/scripts/scenarios/labs/sales_engineering_walkthrough.md)

## Notes

- Seed and reset both run in the background.
- Only one demo-mode task should run at a time.
- Reset is shared by both automated profiles, and both automated seed paths start from a clean slate.
- If demo seed was interrupted, run `Reset Demo Data` and then seed again.
- If you need a totally empty stack, use the hard reset CLI path from `scripts/cleanup.py --hard`.
