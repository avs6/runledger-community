# Observability

*Use the `HomeLab / AgentTest` workspace key in `agents/.env`.*

Explore what your agents did after traffic is flowing.

Seed some traffic first:

```bash
cd scripts/labs/agents
LAB_FEATURE_TAG=support-chat LAB_RUNS=40 python traffic_gen.py
```

## Runs

- Open **Runs** in the dashboard
- Filter by `feature_tag = support-chat`
- Open a run and inspect spans, provider call details, tokens, latency, and cost

## Sessions

- Open **Sessions**
- Pick a conversation and review total cost and turn count

## Analytics

- Open **Analytics → Economics** for cost by model, feature, and day
- Open **Analytics → Users** for cost by `end_user_id`

## Monitoring & Alerts

Create a spend velocity alert, then drive more traffic:

```bash
LAB_FEATURE_TAG=support-chat LAB_RUNS=120 python traffic_gen.py
```

Confirm the alert fires in the monitoring view.

## Audit Log

Open **Governance → Audit Log** and verify that workspace creation, key minting,
budget changes, and route updates are recorded.

## Request Flow

Open **Observability → Request Flow** and inspect how traffic moves across intents,
agents, models, and tools.

## Model Usage

Open **Observability → Model Usage** and review request counts, token totals, cost,
latency, and error rate per model.

## Engineering Dashboard

Open **Observability → Engineering** and review latency, error rate, cache hit rate,
and quality-funnel coverage.

---

Next: [Quality & Evaluation](./quality-evaluation.md)
