# Advanced Budgets & Rate Limits

Budget tiers, model-specific budgets, temporary overrides with auto-expiry,
throttle/fallback enforcement, rate limit headers, and billing metering.

## Prerequisites

- RunLedger API running (`docker compose up -d`)
- A workspace API key
- At least one budget created (from the [Governance](./governance.md) lab or the simulator)

## Budget Tiers

Named profiles (Free, Starter, Pro, Enterprise) that set RPM, TPM, spend,
and model-access limits. Assign a tier to an API key to enforce its limits.

```bash
# Create a tier
curl -s -X POST http://localhost:8201/budget-tiers \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Free",
    "max_spend_usd": 5,
    "period_type": "monthly",
    "rpm_limit": 10,
    "tpm_limit": 10000,
    "allowed_models": ["llama3.2"]
  }' | python -m json.tool

# List tiers
curl -s http://localhost:8201/budget-tiers \
  -H "Authorization: Bearer $KEY" | python -m json.tool

# Assign a tier to a key
curl -s -X PUT "http://localhost:8201/budget-tiers/assign/$KEY_ID?tier_id=$TIER_ID" \
  -H "Authorization: Bearer $KEY" | python -m json.tool
```

## Model-Specific Budgets

Per-model spend and rate limits on individual API keys. Model patterns support
trailing `*` wildcards (e.g., `deepseek-r1:*`).

```bash
# Create a model budget
curl -s -X POST http://localhost:8201/api-keys/$KEY_ID/model-budgets \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model_pattern": "deepseek-r1:*",
    "max_spend_usd": 25,
    "period_type": "monthly",
    "rpm_limit": 20,
    "action": "throttle"
  }' | python -m json.tool

# List model budgets
curl -s http://localhost:8201/api-keys/$KEY_ID/model-budgets \
  -H "Authorization: Bearer $KEY" | python -m json.tool
```

## Throttle & Fallback Enforcement

Two enforcement modes beyond notify/block/downgrade:

- **throttle** — allows the request but signals `throttled: true`
- **fallback** — blocks the request and suggests a cheaper fallback model

```bash
curl -s -X POST http://localhost:8201/budgets \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "scope_type": "workspace",
    "period_type": "monthly",
    "limit_usd": 50,
    "action": "throttle"
  }' | python -m json.tool
```

## Temporary Overrides

Temporarily increase a budget limit for a time window (e.g., a product launch).
Overrides auto-expire via a Celery beat task.

```bash
# Create an override
curl -s -X POST http://localhost:8201/budgets/$BUDGET_ID/override \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "override_limit_usd": 200,
    "starts_at": "2025-01-15T00:00:00Z",
    "expires_at": "2025-01-16T00:00:00Z",
    "reason": "Product launch traffic spike"
  }' | python -m json.tool

# List overrides
curl -s http://localhost:8201/budgets/$BUDGET_ID/overrides \
  -H "Authorization: Bearer $KEY" | python -m json.tool

# Revoke early
curl -s -X POST http://localhost:8201/budgets/$BUDGET_ID/override/$OVERRIDE_ID/revoke \
  -H "Authorization: Bearer $KEY" | python -m json.tool
```

## Rate Limit Headers

Every API response includes standard rate limit headers when applicable:

```
X-RateLimit-Limit-Requests: 60
X-RateLimit-Remaining-Requests: 42
X-RateLimit-Reset: 1705334400
```

## Billing Summary

Per-period breakdown of billable vs non-billable costs:

```bash
curl -s "http://localhost:8201/budgets/billing-summary?months=3" \
  -H "Authorization: Bearer $KEY" | python -m json.tool
```

## Run the Simulation

```bash
python scripts/run_demo.py full-simulate
```

The `07_advanced_budgets` scenario creates a workspace with 4 budget tiers,
feature-tag scoped budgets using throttle/fallback, and billing summary data.
