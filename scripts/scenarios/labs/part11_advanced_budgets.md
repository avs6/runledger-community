# Part 11 — Advanced Budget & Rate Limit Engine

This lab walks through the advanced budget features added in Phase 19:
budget tiers, model-specific budgets, temporary overrides with auto-expiry,
throttle/fallback enforcement modes, rate limit headers, and billable
request metering.

## Prerequisites

- RunLedger API running (`docker compose up -d`)
- A workspace API key (from `POST /settings/api-keys`)
- At least one budget created (from Part 5 or the simulator)

## 1 — Budget tiers

Budget tiers are named profiles (Free, Starter, Pro, Enterprise) that set
RPM, TPM, spend, and model-access limits. Assign a tier to an API key to
enforce its limits on every request through that key.

### Create tiers

```bash
curl -s -X POST http://localhost:8000/budget-tiers \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Free",
    "max_spend_usd": 5,
    "period_type": "monthly",
    "rpm_limit": 10,
    "tpm_limit": 10000,
    "allowed_models": ["llama3.2"]
  }' | jq .
```

### List tiers

```bash
curl -s http://localhost:8000/budget-tiers \
  -H "Authorization: Bearer $KEY" | jq .
```

### Assign a tier to a key

```bash
curl -s -X PUT "http://localhost:8000/budget-tiers/assign/$KEY_ID?tier_id=$TIER_ID" \
  -H "Authorization: Bearer $KEY" | jq .
```

## 2 — Model-specific budgets

Set per-model spend and rate limits on individual API keys. Model patterns
support trailing `*` wildcards (e.g., `deepseek-r1:*` matches any
deepseek-r1 variant).

### Create a model budget

```bash
curl -s -X POST http://localhost:8000/api-keys/$KEY_ID/model-budgets \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model_pattern": "deepseek-r1:*",
    "max_spend_usd": 25,
    "period_type": "monthly",
    "rpm_limit": 20,
    "action": "throttle"
  }' | jq .
```

### List model budgets

```bash
curl -s http://localhost:8000/api-keys/$KEY_ID/model-budgets \
  -H "Authorization: Bearer $KEY" | jq .
```

## 3 — Throttle and fallback enforcement

Phase 19 adds two new enforcement modes beyond the original
notify/block/downgrade:

- **throttle** — allows the request but signals `throttled: true` so the
  caller can slow down voluntarily.
- **fallback** — blocks the request and suggests a cheaper fallback model
  via `fallback_model` in the response.

Create budgets with these actions:

```bash
curl -s -X POST http://localhost:8000/budgets \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "scope_type": "workspace",
    "period_type": "monthly",
    "limit_usd": 50,
    "action": "throttle"
  }' | jq .
```

## 4 — Temporary budget overrides

Temporarily increase a budget limit for a time window (e.g., a product
launch). Overrides auto-expire via a Celery beat task every 5 minutes.

### Create an override

```bash
curl -s -X POST http://localhost:8000/budgets/$BUDGET_ID/override \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "override_limit_usd": 200,
    "starts_at": "2025-01-15T00:00:00Z",
    "expires_at": "2025-01-16T00:00:00Z",
    "reason": "Product launch traffic spike"
  }' | jq .
```

### List overrides

```bash
curl -s http://localhost:8000/budgets/$BUDGET_ID/overrides \
  -H "Authorization: Bearer $KEY" | jq .
```

### Revoke an override early

```bash
curl -s -X POST http://localhost:8000/budgets/$BUDGET_ID/override/$OVERRIDE_ID/revoke \
  -H "Authorization: Bearer $KEY" | jq .
```

## 5 — Rate limit headers

Every API response now includes standard rate limit headers when a rate
limit applies:

```
X-RateLimit-Limit-Requests: 60
X-RateLimit-Remaining-Requests: 42
X-RateLimit-Reset: 1705334400
```

These are injected by middleware and reflect the current key's RPM counter.

## 6 — Billing summary

Get a per-period breakdown of billable vs non-billable costs:

```bash
curl -s "http://localhost:8000/budgets/billing-summary?months=3" \
  -H "Authorization: Bearer $KEY" | jq .
```

The response shows `total_cost_usd`, `billable_cost_usd`,
`non_billable_cost_usd`, `total_calls`, and `billable_calls` for each
period.

## 7 — Run the simulation

```bash
uv run python scripts/full_simulate.py
```

Scenario `07_advanced_budgets` creates a "BudgetLabs / Advanced Budgets"
workspace with 4 budget tiers, feature-tag scoped budgets using
throttle/fallback, and billing summary data.

## What's next

- Budget heatmap UI visualization
- Approval workflow UI for overrides
- Model budget utilization dashboard
- Metering invoice export (CSV/JSON)
