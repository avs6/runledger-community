from celery import Celery

from runledger_api.core.config import settings

celery_app = Celery(
    "runledger",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "runledger_api.workers.pipeline",
        "runledger_api.workers.metering",
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
    },
)
