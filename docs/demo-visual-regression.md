# Demo Visual Regression

This document defines the stable dashboard checkpoints we expect after replaying
 the automated demo on Friday, August 7, 2026.

Use it with the machine-readable fixture manifest at
[apps/web/test-fixtures/demo-dashboard-fixtures.json](C:/Users/Abi/Desktop/github/runledger-community/apps/web/test-fixtures/demo-dashboard-fixtures.json).

## Purpose

- give design and product a repeatable screenshot checklist
- give QA a stable set of seeded demo pages to compare after UI changes
- keep demo storytelling grounded in the same surfaces used for visual review

## How To Use

1. Run `Reset Demo Data`.
2. Run `Seed Demo Data` with `Full Simulator`.
3. Wait for background jobs and analytics to settle.
4. Capture the pages in the fixture manifest.
5. Compare headings, primary cards, chart presence, and key narrative cues.

## Core Fixture Pages

| Fixture | Route | Why it matters |
|---|---|---|
| `dashboard-overview` | `/dashboard` | Proves the top-level enterprise story and KPI density. |
| `request-flow-story` | `/request-flow` | Shows before/after request attribution and exploration depth. |
| `cost-savings-story` | `/cost-savings` | Anchors the optimization ROI narrative. |
| `optimization-opportunities` | `/optimization-opportunities` | Proves advisory and actionability surfaces exist. |
| `gateway-routing` | `/gateway` | Validates routing, cache, and request-log storytelling. |
| `approvals-governance` | `/approvals` | Captures governance and human approval flows. |
| `mcp-governance` | `/mcp` | Shows MCP onboarding and tool-governance positioning. |
| `runbooks-ops` | `/runbooks` | Keeps operator incident/runbook surfaces visually stable. |

## Acceptance Notes

- These fixtures are not pixel-perfect golden images yet.
- They are narrative fixtures: route, heading, cards, and expected seeded themes.
- If a design change intentionally alters one of these pages, update both this doc and the JSON manifest in the same PR.

## Story Expectations

The replayed demo should tell a coherent arc:

1. There is meaningful AI activity across teams and applications.
2. RunLedger identifies cost and latency pressure.
3. RunLedger shows optimization categories such as cache, routing, and compression.
4. RunLedger shows governance controls such as approvals and MCP restrictions.
5. The product can be replayed from a clean slate without live customer data.
