# Part 10 - ML Intelligence Layer

*Prerequisite: Part 1 done. A workspace with at least 7 days of ingested run data.*

RunLedger's ML Intelligence layer adds anomaly detection, cost forecasting, Top-K
analysis, pattern recognition, complexity scoring, and cost-per-outcome optimization.
All models run locally using classical ML/stats — no GPU or LLM dependency.

---

## 10.1 - Anomaly Detection

**Goal:** detect cost spikes, latency regressions, error rate spikes, and cache hit drops.

The anomaly detection worker runs hourly and uses four methods:

- **Z-score** — flags values >3σ from the rolling mean
- **EWMA** — exponentially weighted moving average, more responsive to recent shifts
- **STL (Seasonal-Trend decomposition)** — strips weekly seasonality and trend via LOESS, then flags residuals >3σ; requires ≥15 days of data
- **Isolation Forest (multivariate)** — considers all 5 dimensions (cost, latency, error_rate, tokens, cache_hit_rate) simultaneously to catch correlated anomalies that univariate methods miss

For univariate detectors (Z-score, EWMA, STL), all three run on each dimension and the most severe result wins. Then Isolation Forest runs on the full multivariate feature vector and adds any dimensions not already flagged.

**Correlated anomaly grouping:** when 2+ anomalies fire in the same detection run, they are assigned a shared `correlation_group_id` and each anomaly's context includes the list of `correlated_dimensions`.

```bash
# List detected anomalies
curl -s "http://localhost:8201/intelligence/anomalies?severity=high" \
  -H "Authorization: Bearer $KEY" | python -m json.tool

# Get anomaly summary (last 24h)
curl -s "http://localhost:8201/intelligence/anomalies/summary?hours=24" \
  -H "Authorization: Bearer $KEY" | python -m json.tool

# Acknowledge an anomaly
curl -s "http://localhost:8201/intelligence/anomalies/<anomaly_id>/acknowledge" \
  -H "Authorization: Bearer $KEY" -X POST | python -m json.tool

# Train the Isolation Forest model (needs ≥14 days of data)
curl -s "http://localhost:8201/intelligence/anomalies/train-isolation-forest" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"days": 60, "contamination": 0.05}' \
  -X POST | python -m json.tool

# List correlated anomaly groups
curl -s "http://localhost:8201/intelligence/anomalies/correlated?hours=168" \
  -H "Authorization: Bearer $KEY" | python -m json.tool
```

Severity levels: `low` (3-4σ), `medium` (3-4σ), `high` (4-5σ), `critical` (5+σ).
Flood suppression: >5 anomalies in 24h for the same dimension are auto-suppressed.

**Isolation Forest retraining** runs automatically via a weekly Celery beat task.
You can also trigger it manually via the endpoint above. The model is stored in
the ML model registry and versioned.

---

## 10.2 - Cost Forecasting

**Goal:** predict future cost and token usage with confidence intervals.

Four forecasting methods compete — the system runs all applicable methods and
auto-selects the one with the lowest in-sample MAPE:

- **Linear regression** — simple trend with prediction intervals; always runs
- **Holt-Winters** — exponential smoothing with additive weekly seasonality; needs 14+ days
- **Prophet-style decomposition** — STL decomposition (trend + weekly seasonal + residual), then extrapolates trend via linear regression and repeats the seasonal cycle forward; needs 15+ days
- **ARIMA** — automatic (p,d,q) order selection via AIC grid search over p=0..3, d=0..2, q=0..3; best for stationary or near-stationary series; needs 10+ days

```bash
# Generate a 14-day cost forecast
curl -s "http://localhost:8201/intelligence/forecasts/generate" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"forecast_type": "cost_daily", "horizon_days": 14}' \
  | python -m json.tool

# Get the latest cost forecast
curl -s "http://localhost:8201/intelligence/forecasts/cost" \
  -H "Authorization: Bearer $KEY" | python -m json.tool

# Get the latest token forecast
curl -s "http://localhost:8201/intelligence/forecasts/tokens" \
  -H "Authorization: Bearer $KEY" | python -m json.tool
```

Each forecast point includes predicted value, lower bound, and upper bound
(95% confidence interval). The response also includes accuracy metrics (MAPE, MAE,
R-squared) and the `method` field showing which method won the competition
(`linear`, `holt_winters`, `prophet_style`, or `arima`).

---

## 10.3 - Top-K Analysis

**Goal:** find the most expensive users, models, intents, and providers with
period-over-period change detection.

```bash
# Top 10 most expensive models
curl -s "http://localhost:8201/intelligence/top-k?dimension=model&metric=cost&k=10" \
  -H "Authorization: Bearer $KEY" | python -m json.tool

# Top 5 most active users
curl -s "http://localhost:8201/intelligence/top-k?dimension=user&metric=call_count&k=5" \
  -H "Authorization: Bearer $KEY" | python -m json.tool

# Top 5 highest latency providers
curl -s "http://localhost:8201/intelligence/top-k?dimension=provider&metric=latency_p95&k=5" \
  -H "Authorization: Bearer $KEY" | python -m json.tool
```

Dimensions: `model`, `user`, `intent`, `feature_tag`, `provider`.
Metrics: `cost`, `tokens`, `call_count`, `latency_p95`, `error_rate`.

The response includes `significant_changes` — items that entered/exited the
top-K, or changed by more than 50%.

---

## 10.4 - Pattern Recognition

**Goal:** classify usage patterns to improve forecast method selection.

```bash
# List all detected patterns
curl -s "http://localhost:8201/intelligence/patterns" \
  -H "Authorization: Bearer $KEY" | python -m json.tool

# Patterns for a specific dimension
curl -s "http://localhost:8201/intelligence/patterns/cost" \
  -H "Authorization: Bearer $KEY" | python -m json.tool
```

Pattern types:

| Pattern | Description |
|---|---|
| steady | Consistent daily usage, low variance |
| growing | Week-over-week increase (significant positive slope) |
| declining | Week-over-week decrease (significant negative slope) |
| spiky | High variance, irregular usage (CV > 0.5) |
| seasonal | Predictable weekly cycle (autocorrelation at lag 7) |
| one_shot | >80% of total concentrated in <10% of days |

---

## 10.5 - Complexity Scoring

**Goal:** score request complexity using gradient boosting on observable features.

```bash
# Retrain the complexity model
curl -s "http://localhost:8201/intelligence/complexity/retrain" \
  -H "Authorization: Bearer $KEY" -X POST | python -m json.tool

# Get recent complexity scores
curl -s "http://localhost:8201/intelligence/complexity/scores?hours=24" \
  -H "Authorization: Bearer $KEY" | python -m json.tool

# Get feature importances
curl -s "http://localhost:8201/intelligence/complexity/importances" \
  -H "Authorization: Bearer $KEY" | python -m json.tool
```

The model trains on: input_tokens, output_tokens, total_tokens, tool_call_count,
latency_ms. Complexity tiers: `simple`, `medium`, `complex`, `reasoning`.

---

## 10.6 - Cost-Per-Outcome Analysis

**Goal:** find the cheapest model that maintains quality, with Pareto frontier.

```bash
curl -s "http://localhost:8201/intelligence/cost-per-outcome" \
  -H "Authorization: Bearer $KEY" | python -m json.tool
```

Returns cost per successful outcome by model and outcome type, plus the
Pareto frontier — models where no other model has both lower cost AND
higher quality.

---

## 10.7 - Adaptive Alert Thresholds

**Goal:** replace static alert thresholds with statistically-derived ones.

```bash
# Get adaptive threshold suggestions
curl -s "http://localhost:8201/intelligence/alerts/adaptive-suggestions" \
  -H "Authorization: Bearer $KEY" | python -m json.tool

# Enable adaptive mode on a rule
curl -s "http://localhost:8201/intelligence/alerts/<rule_id>/enable-adaptive" \
  -H "Authorization: Bearer $KEY" -X POST | python -m json.tool
```

Adaptive thresholds use EWMA on 30-day feature history to compute baselines
with confidence intervals. They reduce false positives for variable workloads
and tighten thresholds for stable ones.

---

## 10.8 - ML Dashboard

**Goal:** monitor the health of all trained ML models.

```bash
# ML observability dashboard
curl -s "http://localhost:8201/intelligence/dashboard" \
  -H "Authorization: Bearer $KEY" | python -m json.tool

# List trained models
curl -s "http://localhost:8201/intelligence/models" \
  -H "Authorization: Bearer $KEY" | python -m json.tool
```

Each model shows: type, dimension, version, training date, sample count,
staleness, accuracy metrics, and health status (healthy/stale/degraded).

---

End of Part 10. You've set up anomaly detection, cost forecasting, Top-K analysis,
pattern recognition, complexity scoring, cost-per-outcome optimization, adaptive
alert thresholds, and ML observability. Next: review **[Part 11 - Agentic Operations](./part11_agentic.md)**
for agent lifecycle management (Phase 16).
