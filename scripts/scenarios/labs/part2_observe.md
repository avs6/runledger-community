# Part 2 - Observe and Investigate

*Prerequisite: you finished Part 1 and have the `HomeLab / AgentTest` key ready in `agents/.env`.*

This part is about reading what your agents did after the runtime path is working.

Seed a little traffic first:

```bash
cd scripts/scenarios/labs/agents
LAB_FEATURE_TAG=support-chat LAB_RUNS=40 python traffic_gen.py
```

## 2.1 - Runs

- Open **Runs**
- Filter by `feature_tag = support-chat`
- Open a run and inspect spans, provider call details, tokens, latency, and cost

## 2.2 - Sessions

- Open **Sessions**
- Pick a conversation and review total cost and turn count

## 2.3 - Analytics

- Open **Analytics -> Economics** for cost by model, feature, and day
- Open **Analytics -> Users** for cost by `end_user_id`

## 2.4 - Monitoring and alerts

Create a simple spend velocity alert, then drive more traffic:

```bash
LAB_FEATURE_TAG=support-chat LAB_RUNS=120 python traffic_gen.py
```

Confirm the alert fires in the monitoring view.

## 2.5 - Audit log

Open **Governance -> Audit Log** and verify that workspace creation, key minting,
budget changes, and route updates are recorded.

## 2.6 - Request flow

Open **Observability -> Request Flow** and inspect how traffic moves across intents,
agents, models, and tools.

## 2.7 - Model usage

Open **Observability -> Model Usage** and review request counts, token totals, cost,
latency, and error rate per model.

## 2.8 - Engineering dashboard

Open **Observability -> Engineering** and review latency, error rate, cache hit rate,
and quality-funnel coverage.

## 2.9 - Onboarding wizard

Open **Observability -> Onboarding** and confirm the guided integration steps are
available for workspace-based onboarding flows.

Next: [Part 3 - Quality and Experiments](./part3_quality.md)
