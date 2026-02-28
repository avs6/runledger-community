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
    },
)
