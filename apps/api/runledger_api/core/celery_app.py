from celery import Celery

from runledger_api.core.config import settings

celery_app = Celery(
    "runledger",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "runledger_api.workers.pipeline",
        "runledger_api.workers.metering",
        "runledger_api.workers.budgets",
        "runledger_api.workers.billing",
        "runledger_api.workers.ledger",
        "runledger_api.workers.alerts",
        "runledger_api.workers.evaluators",
        "runledger_api.workers.outcomes",
        "runledger_api.workers.otlp_finalize",
        "runledger_api.workers.retention",
        "runledger_api.workers.email_reports",
        "runledger_api.workers.gateway_health",
        "runledger_api.workers.consolidation",
        "runledger_api.workers.flywheel",
        "runledger_api.workers.ml_anomaly",
        "runledger_api.workers.ml_forecast",
        "runledger_api.workers.ml_complexity",
        "runledger_api.workers.budget_overrides",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    beat_schedule={
        # Cognitive consolidation: distil episodes → facts, daily
        "cognitive-consolidation-daily": {
            "task": "cognitive.consolidate",
            "schedule": 86400.0,
        },
        # Optimization flywheel: learn cheapest config per segment holding the SLA, daily
        "flywheel-analyze-daily": {
            "task": "flywheel.analyze",
            "schedule": 86400.0,
        },
        # Cost enrichment: every 60 seconds
        "cost-enrichment-60s": {
            "task": "metering.cost_enrichment",
            "schedule": 60.0,
        },
        # Hourly rollup: every 30 minutes
        "rollup-hourly-30m": {
            "task": "metering.rollup_hourly",
            "schedule": 1800.0,
        },
        # Daily rollup: every day at 00:05 UTC
        "rollup-daily-00:05": {
            "task": "metering.rollup_daily",
            "schedule": 86400.0,  # approximate — use celery beat crontab for prod
        },
        # Data quality check: every hour
        "data-quality-1h": {
            "task": "metering.data_quality",
            "schedule": 3600.0,
        },
        # Runaway protection: every 5 minutes
        "runaway-protection-5m": {
            "task": "budgets.runaway_protection",
            "schedule": 300.0,
        },
        # Budget spend sync: daily (recovery from Redis eviction)
        "budget-spend-sync-daily": {
            "task": "budgets.budget_spend_sync",
            "schedule": 86400.0,
        },
        # Nightly reconciliation: daily at 00:15 UTC
        "nightly-reconciliation": {
            "task": "billing.nightly_reconciliation",
            "schedule": 86400.0,
        },
        # Auto-create billing periods: daily at 00:01 UTC
        "auto-create-billing-periods": {
            "task": "billing.auto_create_billing_periods",
            "schedule": 86400.0,
        },
        # Ledger daily snapshots: daily at 1am UTC
        "ledger-daily-snapshots": {
            "task": "ledger.daily_snapshots",
            "schedule": 86400.0,
        },
        # Suspicious sequence detection: every 60 seconds
        "ledger-suspicious-sequences": {
            "task": "ledger.suspicious_sequences",
            "schedule": 60.0,
        },
        # Alert rule evaluation: every 5 minutes
        "alert-evaluation-5m": {
            "task": "alerts.evaluate_rules",
            "schedule": 300.0,
        },
        # Judge drift detection: every 6 hours
        "judge-drift-6h": {
            "task": "evaluators.detect_judge_drift",
            "schedule": 21600.0,
        },
        # Outcome daily rollup: every day at 00:10 UTC
        "outcome-rollup-daily": {
            "task": "outcomes.rollup_daily",
            "schedule": 86400.0,
        },
        # Outcome alert check: every 6 hours
        "outcome-alerts-6h": {
            "task": "outcomes.check_alerts",
            "schedule": 21600.0,
        },
        # OTLP stale trace finalizer: every 3 minutes
        "otlp-finalize-stale-3m": {
            "task": "otlp.finalize_stale_traces",
            "schedule": 180.0,
        },
        # Data retention policies: nightly at 00:30 UTC
        "retention-apply-policies-daily": {
            "task": "retention.apply_policies",
            "schedule": 86400.0,
        },
        # Scheduled analytics email reports: hourly check, workspace prefs decide cadence.
        "email-report-weekly": {
            "task": "email_reports.send_weekly_analytics",
            "schedule": 3600.0,
        },
        # Gateway route health monitoring: every 5 minutes
        "gateway-health-check-5m": {
            "task": "gateway.health_check",
            "schedule": 300.0,
        },
        # ML anomaly detection: hourly
        "ml-anomaly-detection-hourly": {
            "task": "ml.anomaly_detection",
            "schedule": 3600.0,
        },
        # ML forecast retraining: daily
        "ml-forecast-retraining-daily": {
            "task": "ml.forecast_retraining",
            "schedule": 86400.0,
        },
        # ML complexity scorer retraining: weekly
        "ml-complexity-retraining-weekly": {
            "task": "ml.complexity_retraining",
            "schedule": 604800.0,
        },
        # Isolation Forest retraining: weekly
        "ml-isolation-forest-weekly": {
            "task": "ml.isolation_forest_training",
            "schedule": 604800.0,
        },
        "budget-overrides-expire-5m": {
            "task": "budgets.expire_overrides",
            "schedule": 300.0,
        },
    },
)

if not (settings.email_enabled and settings.email_reports_enabled):
    celery_app.conf.beat_schedule.pop("email-report-weekly", None)
