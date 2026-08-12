# Part 5 - Governance and Control

*Prerequisite: Part 1 completed.*

This section covers the controls that make the runtime path safe, reviewable, and
finance-aware.

## 5.1 - Gateway guardrails

Use the gateway to enforce:

- fallback routes
- per-route cost caps
- per-user rate limits
- PII redaction

Drive traffic through the configured alias and verify the gateway request log shows
the resulting decision.

## 5.2 - Tool registry

Register a few tools and confirm the policy outcome changes:

- `search_kb` -> allow
- `lookup_order` -> audit
- `refund_customer` -> block and enforce

## 5.3 - Approvals

Create a `budget_increase` request with a reason such as:

`Black Friday traffic - raise HomeLab AgentTest daily cap to $50`

Approve or deny it and verify the status transition.

## 5.4 - Auto-approval policies

Create a low-risk auto-approval rule for small budget increases and compare how
small versus large requests behave.

## 5.5 - Chargeback and showback

Map feature tags to cost centers and verify the resulting finance view.

## 5.6 - Runbooks

Generate a runbook from an expensive or failed run and review the resulting operator
summary.

## 5.7 - Model scorecards

Compare cost, latency, and quality across active models.

## 5.8 - Policy dry run

Simulate a routing or budget policy before enforcing it.

## 5.9 - Governance audit pack

Export the audit pack and confirm policies, approvals, budgets, and tool events are
included.

Next: [Part 6 - Operations](./part6_operations.md)
