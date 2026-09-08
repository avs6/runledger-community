"""
Scenario: ML intelligence layer demo.

Demonstrates anomaly detection, cost forecasting, Top-K analysis,
pattern recognition, complexity scoring, and cost-per-outcome
optimization through the ML intelligence API.
"""

from __future__ import annotations

from scenarios._base import Sim

NAME = "ollama-intelligence"
DESCRIPTION = "ML intelligence — anomaly detection, forecasting, top-K, patterns, complexity scoring."


def run(sim: Sim) -> None:
    ws = sim.workspace("IntelliOps", "ML Intelligence")

    # ── 1. Ingest runs to build feature history ─────────────────────────
    runs = ws.ingest_runs(
        200,
        models=["qwen2.5-coder:14b", "deepseek-r1:14b", "llama3.2"],
        features=["coding", "chat", "reasoning"],
        users=["u_alice", "u_bob", "u_carol", "u_dave"],
        days=30,
        success_rate=0.92,
        sessions=20,
    )

    # ── 2. Record outcomes and scores for cost-per-outcome analysis ────
    for r in ws.sample(runs, 50):
        ws.record_outcome(r, "resolved", value_usd=5.0)
        ws.score(r, "quality", 0.85)

    for r in ws.sample(runs, 30):
        ws.record_outcome(r, "escalated", value_usd=2.0)
        ws.score(r, "quality", 0.55)

    # ── 3. List anomalies (populated by worker, may be empty in demo) ──
    ws.list_anomalies()

    # ── 4. Get anomaly summary ─────────────────────────────────────────
    ws.get_anomaly_summary(hours=24)

    # ── 5. Generate cost forecast ──────────────────────────────────────
    ws.generate_forecast(forecast_type="cost_daily", horizon_days=14)

    # ── 6. Generate token forecast ─────────────────────────────────────
    ws.generate_forecast(forecast_type="tokens_daily", horizon_days=14)

    # ── 7. Get cost forecast ───────────────────────────────────────────
    ws.get_cost_forecast()

    # ── 8. Top-K analysis — most expensive models ──────────────────────
    ws.get_top_k(dimension="model", metric="cost", k=5)

    # ── 9. Top-K — most active users ───────────────────────────────────
    ws.get_top_k(dimension="user", metric="call_count", k=5)

    # ── 10. List usage patterns ────────────────────────────────────────
    ws.list_patterns()

    # ── 11. Cost-per-outcome analysis ──────────────────────────────────
    ws.get_cost_per_outcome()

    # ── 12. Complexity scoring ─────────────────────────────────────────
    ws.retrain_complexity()
    ws.get_complexity_scores(hours=24)
    ws.get_feature_importances()

    # ── 13. Adaptive alert suggestions ─────────────────────────────────
    ws.get_adaptive_suggestions()

    # ── 14. Train Isolation Forest for multivariate anomaly detection ─
    ws.train_isolation_forest(days=30)

    # ── 15. ML dashboard ───────────────────────────────────────────────
    ws.get_ml_dashboard()
