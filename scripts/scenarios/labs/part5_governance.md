# Part 5 · Governance & Control

*Prerequisite: Part 1 done.*

Optimization makes agents **cheaper**; governance keeps them **safe and accountable**. Three
controls: gateway guardrails, a tool policy, and human approvals.

---

## 5.1 · Model Gateway guardrails

Beyond routing, a Gateway route enforces **operational limits**. From
[`samples/routing_policies.md`](./samples/routing_policies.md), apply these on a route and then
drive traffic through the alias:

- **Policy 1 — Fallback / priority**: two routes on one alias; kill the primary model in
  Ollama and watch the fallback take over (`decision_reason` shows the failover).
- **Policy 5 — Per-route cost cap**: a daily `$0.05` ceiling; calls are refused at the gateway
  once crossed — independent of workspace budgets.
- **Policy 6 — Per-user RPM + PII redaction**: throttle a single `end_user_id`; scrub emails /
  phone numbers before they reach the provider.

```bash
LAB_GATEWAY_ALIAS=chat LAB_RUNS=40 LAB_FEATURE_TAG=guardrails python traffic_gen.py
```

🔎 The gateway is your policy enforcement point: routing, caching, limits, and redaction all
sit in one place your agents already call.

---

## 5.2 · Tool Registry

**Goal:** decide which tools agents may call — allow, audit, or block.

Register the tools from [`samples/tools_and_policies.md`](./samples/tools_and_policies.md) on the
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
or releasing a blocked tool call.

1. Open **Approvals** → **New request**. Type: `budget_increase`, with a reason
   ("Black Friday traffic — raise AI Support Team daily cap to $50").
2. As the approver (org admin), open the pending request → **Approve** or **Deny** with a note.
3. Watch the status move `pending → approved/denied`; the **summary** counts update.

🔎 Tool Registry is *automated* enforcement; Approvals is the *human* gate. Together they cover
"block it outright" and "block it unless a person signs off."

---

✅ **End of Part 5.** Your agents now have failover, spend/rate/PII guardrails, a tool policy,
and a human approval path. Next: **[Part 6 · Operations](./part6_operations.md)**.
