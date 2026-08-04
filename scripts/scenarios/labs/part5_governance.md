# Part 5 · Governance & Control

*Prerequisite: Part 1 done.*

Optimization makes agents **cheaper**; governance keeps them **safe and accountable**. This
part covers gateway guardrails, tool policies, human approvals (including auto-approval
policies), chargeback & showback, runbooks, model scorecards, policy dry run, and the
governance audit pack.

---

## 5.1 · Model Gateway guardrails

As an org admin, configure Gateway routes to enforce **operational limits**. From
[`samples/routing_policies.md`](./samples/routing_policies.md), apply these on a route and then
drive traffic through the alias:

- **Policy 1 — Fallback / priority**: two routes on one alias; kill the primary model in
  Ollama and watch the fallback take over (`decision_reason` shows the failover).
- **Policy 8 - Per-route cost cap**: a daily `$0.05` ceiling; calls are refused at the gateway
  once crossed — independent of workspace budgets.
- **Policy 9 - Per-user RPM + PII redaction**: throttle a single `end_user_id`; scrub emails /
  phone numbers before they reach the provider.

```bash
LAB_GATEWAY_ALIAS=chat LAB_RUNS=40 LAB_FEATURE_TAG=guardrails python traffic_gen.py
```

🔎 The gateway is your policy enforcement point: routing, caching, limits, and redaction all
sit in one place your agents already call.

---

## 5.2 · Tool Registry

**Goal:** decide which tools agents may call — allow, audit, or block.

As an org admin, register the tools from [`samples/tools_and_policies.md`](./samples/tools_and_policies.md) on the
**Tool Registry** page (`search_kb`=allow, `lookup_order`=audit, `refund_customer`=block+enforce,
`delete_account`=block+enforce). Then resolve a policy directly:

```bash
curl -s -H "Authorization: Bearer $RUNLEDGER_API_KEY" \
  http://localhost:8201/tools/check/refund_customer      # → 403, security event written
curl -s -H "Authorization: Bearer $RUNLEDGER_API_KEY" \
  http://localhost:8201/tools/check/search_kb            # → allowed: true
```

🔎 Blocked attempts appear under **security events** on the Tool Registry page. In a real
agent with `tool_enforcement=True`, that 403 becomes a `ToolBlockedError` raised *before* the
tool runs — the risky action never happens.

---

## 5.3 · Approvals (human-in-the-loop)

**Goal:** route a sensitive change to a person to approve or deny.

Approvals are a workflow for actions that shouldn't be automatic — e.g. **raising a budget**,
or releasing a blocked tool call. RunLedger supports **10 request types**:

| Request type | When to use |
|---|---|
| `budget_increase` | Raise a workspace or feature budget cap |
| `budget_override` | Override a blocked budget enforcement |
| `model_access` | Grant access to a restricted model |
| `data_export` | Export sensitive data (runs, traces, prompts) |
| `config_change` | Change a gateway route or policy |
| `premium_model_use` | Use a frontier/expensive model for a period |
| `external_mcp_tool` | Connect an external MCP tool to the workspace |
| `long_agent_session` | Allow an agent session exceeding the time/cost cap |
| `sensitive_export` | Export PII-containing or compliance-scoped data |
| `route_policy_change` | Change a routing policy (fallback, cache, limits) |

1. As a workspace admin, open **Governance → Approvals** and create a new request. Type:
   `budget_increase`, with a reason ("Black Friday traffic — raise AI Support Team daily cap
   to $50").
2. As a workspace admin or org admin for that workspace, open the pending request and
   **Approve** or **Deny** with a note.
3. Watch the status move `pending → approved/denied`; the **summary strip** counts update.

🔎 Use the summary filter cards at the top to quickly find pending, approved, or denied
requests.

---

## 5.4 · Auto-Approval Policies

**Goal:** let low-risk requests bypass the human gate automatically.

1. On the **Approvals** page, scroll to **Auto-Approval Policies**.
2. Create a policy:
   - **Request type:** `budget_increase`
   - **Max amount:** `10.00` (auto-approve budget increases up to $10)
   - **Conditions:** `{"scope": "workspace", "period_type": "daily"}`
3. Submit a `budget_increase` request with a `requested_limit` of $8 — it should be
   auto-approved immediately.
4. Submit one with $15 — it stays `pending` for human review.

🔎 Auto-approval policies are the middle ground between "block everything" and "approve
everything." Set them for well-understood, bounded requests.

---

## 5.5 · Chargeback & Showback

**Goal:** attribute AI spend to the business units that caused it.

1. Open **FinOps → Chargeback**. Create chargeback rules that map traffic to cost centers:

   | Rule name | Match field | Match value | Cost center | Split % |
   |---|---|---|---|---|
   | Support chat | `feature_tag` | `support-chat` | SUPPORT-OPS | 100 |
   | Billing queries | `feature_tag` | `billing-help` | BILLING-OPS | 80 |
   | Fraud checks | `feature_tag` | `fraud-check` | TRUST-SAFETY | 100 |

2. Generate traffic so the rules have data to match:
   ```bash
   LAB_FEATURE_TAG=support-chat LAB_RUNS=40 python traffic_gen.py
   LAB_FEATURE_TAG=billing-help LAB_RUNS=20 python traffic_gen.py
   ```
3. View the **Chargeback Report** — monthly cost breakdowns by cost center, with month-over-month
   variance.

🔎 Chargeback rules turn raw spend into finance-ready reports. Each rule maps a traffic
attribute (feature, model, user, team) to a cost center and optionally splits the cost.

---

## 5.6 · Agent Runbooks

**Goal:** generate incident-style summaries for individual runs.

1. Open **Observability → Runs** and find an expensive or failed run.
2. Click the run detail, then **Generate Runbook**.
3. The runbook includes: what happened, which model/tool was used, cost breakdown, error
   details (if any), and recommended next steps.
4. Open **Observability → Runbooks** to see all generated runbooks, filterable by status.

🔎 Runbooks turn raw run data into actionable incident summaries — useful for post-mortems
and on-call handoffs.

---

## 5.7 · Model Scorecards

**Goal:** compare model quality, cost, and performance side by side.

1. Open **Observability → Model Scorecards**. Each model with enough traffic gets a scorecard
   showing:
   - Request count, total tokens, total cost
   - Average latency, error rate
   - Quality score trends (from evaluation scores)
   - Cost-per-quality ratio
2. Use the time-range filter to compare models over different periods.

🔎 Scorecards answer "which model gives the best value?" — quality per dollar, not just raw
performance. Use them to justify model switches.

---

## 5.8 · Policy Dry Run

**Goal:** test a policy change before enforcing it.

1. Open **Governance → Policy Dry Run**.
2. Select a policy type (budget, routing, tool) and the proposed change.
3. Run the simulation — it shows what *would have happened* over recent traffic:
   - How many requests would have been blocked/rerouted
   - Cost impact (savings or increase)
   - Quality impact (if routing changes)
4. Decide whether to apply the policy based on evidence, not guesswork.

🔎 Dry run is the safety net for policy changes. Never enforce a new budget or routing rule
blind — dry-run it first.

---

## 5.9 · Governance Audit Pack

**Goal:** export a compliance evidence bundle.

1. Open **Governance → Governance Audit Pack**.
2. Select the time range and click **Export**.
3. The pack includes:
   - Active policies and their enforcement history
   - Approval request log (all decisions)
   - Budget utilization and breach events
   - Tool registry and security events
   - Data capture and retention configuration
4. Download as CSV for auditors or compliance review.

🔎 The audit pack is your compliance evidence — everything an auditor would ask for, in one
export. Schedule it monthly for SOC 2 or ISO 27001 evidence collection.

---

✅ **End of Part 5.** Your agents now have failover, spend/rate/PII guardrails, a tool policy,
a human approval path with auto-approval for low-risk requests, chargeback attribution,
runbooks, model scorecards, dry-run testing, and exportable compliance evidence. Next:
**[Part 6 · Operations](./part6_operations.md)**.
