# Part 2 · Observe & Investigate

*Prerequisite: you finished Part 1 (stack up, teams created, pricing uploaded, keys minted).*

This part is about **reading** what your agents did. You'll generate traffic once with the
reusable agent, then explore it entirely in the GUI. Put the **AI Support Team** key in
`agents/.env` and seed some data:

```bash
cd scripts/scenarios/labs/agents
LAB_FEATURE_TAG=support-chat LAB_RUNS=40 python traffic_gen.py
```

Give Celery ~60s to enrich cost, then work through the modules.

---

## 2.1 · Runs

**Goal:** trace a single agent execution end to end.

- Open **Runs**. Filter by `feature_tag = support-chat`.
- Click any run → see its spans, the `provider_call` (model, tokens, latency, cost), and
  any score/outcome attached.

🔎 Every run is attributed to an `end_user_id` and a `feature_tag` — that attribution is
what makes all the analytics below possible.

---

## 2.2 · Sessions

**Goal:** group multi-turn conversations.

The agent stamps a `session_id` on related runs. Open **Sessions** → pick one → see the
ordered runs, total cost, and turn count for that conversation.

🔎 Sessions answer "what did one whole conversation cost?", not just one call.

---

## 2.3 · Analytics

**Goal:** see cost and usage roll up.

- **Analytics → Economics** — cost by model / feature / day. Confirm your **priced Ollama
  models show real (small) spend**, not $0 (that's the pricing upload from Part 1 working).
- **Analytics → Users** — cost per `end_user_id`. Click a user to see their runs. Who is
  your most expensive customer?

🔎 This is the FinOps view: where the money goes, sliced the way you tagged it.

---

## 2.4 · Monitoring & Alerts

**Goal:** get told when something goes wrong, instead of finding out later.

1. Open **Monitoring** → create an **alert rule** (GUI):
   - Metric: `spend_velocity`  ·  Operator: `gt`  ·  Threshold: `5`
   - (Other metrics: `error_rate`, `p95_latency`, `avg_score`.)
2. Drive a burst to trip it:
   ```bash
   LAB_FEATURE_TAG=support-chat LAB_RUNS=120 python traffic_gen.py
   ```
3. Back on **Monitoring**, watch the rule's **firing history**.

🔎 Alerts are the always-on version of the analytics you just read by hand.

---

## 2.5 · Audit Logs

**Goal:** see the record of *administrative* actions (not agent traffic).

Open **Audit**. Every setup step you did in the GUI — creating workspaces, minting API
keys, changing budgets, editing routes — is recorded with who/what/when.

🔎 Runs = what your *agents* did. Audit = what *people* did to the configuration. Both
matter for governance and incident review.

---

✅ **End of Part 2.** You can now find any run, cost, or conversation, get alerted on
regressions, and prove who changed what. Next: **[Part 3 · Quality & Experiments](./part3_quality.md)**.
