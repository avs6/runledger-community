"""Celery application: queues, per-task limits and the beat schedule.

Queues (review P-12):
  * ``ingest``       — pipeline.process_events only; runledger-worker-ingest consumes it,
                       so event processing never waits behind slow jobs (review I-27).
  * ``celery``       — default: enrichment, rollups, alerts, gateway health, outbox.
  * ``maintenance``  — long, deferrable jobs: backups, retention and purges, ML
                       retraining, consolidation, flywheel, replay, batch evaluation.

Every task has a soft and a hard time limit (CELERY_TASK_SOFT_TIME_LIMIT /
CELERY_TASK_TIME_LIMIT); the maintenance jobs that legitimately run long get their own
limits below. The Redis broker's visibility_timeout is longer than the longest hard
limit, so an unacked task is redelivered only after its worker is surely gone.

Beat (review P-20, cd:S-06): daily and weekly jobs use crontab schedules aligned to
the wall clock, so a beat restart doesn't push them later each time the way
86400-second intervals drifted. Beat stores its schedule file wherever ``-s`` points:
a named volume in compose, an emptyDir in Helm.
"""

from celery import Celery
from celery.schedules import crontab
from kombu import Queue

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
        "runledger_api.workers.backups",
        "runledger_api.workers.kafka",
        # Replay experiments were queued but no worker loaded the task (review B-06).
        "runledger_api.workers.replay",
        # Worker/beat heartbeats for /health and the system status page.
        "runledger_api.workers.platform",
    ],
)

QUEUE_INGEST = "ingest"
QUEUE_DEFAULT = "celery"
QUEUE_MAINTENANCE = "maintenance"
ALL_QUEUES = (QUEUE_DEFAULT, QUEUE_INGEST, QUEUE_MAINTENANCE)

# Long-running jobs: routed to the maintenance queue, with their own time limits
# (soft, hard) in seconds.
_LONG_TASK_LIMITS: dict[str, tuple[int, int]] = {
    "backups.run_scheduled": (
        settings.backup_timeout_seconds,
        settings.backup_timeout_seconds + 120,
    ),
    "retention.apply_policies": (1800, 1900),
    "ingest.purge_raw_telemetry": (1800, 1900),
    "auth.purge_session_keys": (300, 360),
    "cognitive.consolidate": (1800, 1900),
    "flywheel.analyze": (1800, 1900),
    "ml.anomaly_detection": (900, 960),
    "ml.forecast_retraining": (1800, 1900),
    "ml.complexity_retraining": (1800, 1900),
    "ml.isolation_forest_training": (1800, 1900),
    "replay.run_experiment": (1800, 1900),
    "evaluators.batch_evaluate": (1800, 1900),
    "metering.replay_backfill": (1800, 1900),
}

_task_routes: dict[str, dict[str, str]] = {"pipeline.process_events": {"queue": QUEUE_INGEST}}
_task_routes.update({name: {"queue": QUEUE_MAINTENANCE} for name in _LONG_TASK_LIMITS})
# Heartbeats: one per queue so every worker pool proves it is consuming.
_task_routes["platform.heartbeat"] = {"queue": QUEUE_DEFAULT}

celery_app.conf.update(
    task_queues=[Queue(name) for name in ALL_QUEUES],
    task_default_queue=QUEUE_DEFAULT,
    task_routes=_task_routes,
    task_annotations={
        name: {"soft_time_limit": soft, "time_limit": hard}
        for name, (soft, hard) in _LONG_TASK_LIMITS.items()
    },
    task_soft_time_limit=settings.celery_task_soft_time_limit,
    task_time_limit=settings.celery_task_time_limit,
    broker_transport_options={"visibility_timeout": settings.celery_visibility_timeout},
    result_backend_transport_options={"visibility_timeout": settings.celery_visibility_timeout},
    result_expires=86400,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=settings.celery_worker_max_tasks_per_child,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    beat_schedule={
        # ── Heartbeats (beat → each queue). The beat process passes its own version,
        #    so the receiving worker records both (cd:S-06 version skew).
        "platform-heartbeat-default-60s": {
            "task": "platform.heartbeat",
            "schedule": 60.0,
            "args": (QUEUE_DEFAULT, settings.runledger_version, settings.runledger_build_sha),
            "options": {"queue": QUEUE_DEFAULT, "expires": 120},
        },
        "platform-heartbeat-ingest-60s": {
            "task": "platform.heartbeat",
            "schedule": 60.0,
            "args": (QUEUE_INGEST, settings.runledger_version, settings.runledger_build_sha),
            "options": {"queue": QUEUE_INGEST, "expires": 120},
        },
        "platform-heartbeat-maintenance-60s": {
            "task": "platform.heartbeat",
            "schedule": 60.0,
            "args": (
                QUEUE_MAINTENANCE,
                settings.runledger_version,
                settings.runledger_build_sha,
            ),
            "options": {"queue": QUEUE_MAINTENANCE, "expires": 120},
        },
        # Cognitive consolidation: distil episodes → facts, daily 03:00 UTC
        "cognitive-consolidation-daily": {
            "task": "cognitive.consolidate",
            "schedule": crontab(hour=3, minute=0),
        },
        # Optimization flywheel: cheapest config per segment holding the SLA, 03:30 UTC
        "flywheel-analyze-daily": {
            "task": "flywheel.analyze",
            "schedule": crontab(hour=3, minute=30),
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
        # Daily rollup: 00:05 UTC
        "rollup-daily-00:05": {
            "task": "metering.rollup_daily",
            "schedule": crontab(hour=0, minute=5),
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
        # Budget spend sync (recovery from Redis eviction): 00:20 UTC
        "budget-spend-sync-daily": {
            "task": "budgets.budget_spend_sync",
            "schedule": crontab(hour=0, minute=20),
        },
        # Nightly reconciliation: 00:15 UTC
        "nightly-reconciliation": {
            "task": "billing.nightly_reconciliation",
            "schedule": crontab(hour=0, minute=15),
        },
        # Auto-create billing periods: 00:01 UTC
        "auto-create-billing-periods": {
            "task": "billing.auto_create_billing_periods",
            "schedule": crontab(hour=0, minute=1),
        },
        # Ledger daily snapshots: 01:00 UTC
        "ledger-daily-snapshots": {
            "task": "ledger.daily_snapshots",
            "schedule": crontab(hour=1, minute=0),
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
            "schedule": crontab(hour="*/6", minute=40),
        },
        # Outcome daily rollup: 00:10 UTC
        "outcome-rollup-daily": {
            "task": "outcomes.rollup_daily",
            "schedule": crontab(hour=0, minute=10),
        },
        # Outcome alert check: every 6 hours
        "outcome-alerts-6h": {
            "task": "outcomes.check_alerts",
            "schedule": crontab(hour="*/6", minute=50),
        },
        # OTLP stale trace finalizer: every 3 minutes
        "otlp-finalize-stale-3m": {
            "task": "otlp.finalize_stale_traces",
            "schedule": 180.0,
        },
        # Data retention policies: 00:30 UTC
        "retention-apply-policies-daily": {
            "task": "retention.apply_policies",
            "schedule": crontab(hour=0, minute=30),
        },
        # Raw OTLP data, finished Kafka deliveries, resolved dead letters: 00:45 UTC
        "ingest-purge-raw-telemetry-daily": {
            "task": "ingest.purge_raw_telemetry",
            "schedule": crontab(hour=0, minute=45),
        },
        # Expired / revoked dashboard session keys (7-day grace): 01:15 UTC
        "auth-purge-session-keys-daily": {
            "task": "auth.purge_session_keys",
            "schedule": crontab(hour=1, minute=15),
        },
        # Scheduled analytics email reports: hourly check, workspace prefs decide cadence.
        "email-report-weekly": {
            "task": "email_reports.send_weekly_analytics",
            "schedule": crontab(minute=5),
        },
        # Gateway route health monitoring: every 5 minutes
        "gateway-health-check-5m": {
            "task": "gateway.health_check",
            "schedule": 300.0,
        },
        # ML anomaly detection: hourly
        "ml-anomaly-detection-hourly": {
            "task": "ml.anomaly_detection",
            "schedule": crontab(minute=20),
        },
        # ML forecast retraining: 02:00 UTC
        "ml-forecast-retraining-daily": {
            "task": "ml.forecast_retraining",
            "schedule": crontab(hour=2, minute=0),
        },
        # ML complexity scorer retraining: Sundays 04:00 UTC
        "ml-complexity-retraining-weekly": {
            "task": "ml.complexity_retraining",
            "schedule": crontab(day_of_week=0, hour=4, minute=0),
        },
        # Isolation Forest retraining: Sundays 04:30 UTC
        "ml-isolation-forest-weekly": {
            "task": "ml.isolation_forest_training",
            "schedule": crontab(day_of_week=0, hour=4, minute=30),
        },
        "budget-overrides-expire-5m": {
            "task": "budgets.expire_overrides",
            "schedule": 300.0,
        },
        "backups-scheduled-1h": {
            "task": "backups.run_scheduled",
            "schedule": crontab(minute=0),
        },
        # Kafka outbox: deliver pending rows and due retries.
        "kafka-outbox-10s": {
            "task": "kafka.retry_pending_deliveries",
            "schedule": 10.0,
        },
    },
)

if not (settings.email_enabled and settings.email_reports_enabled):
    celery_app.conf.beat_schedule.pop("email-report-weekly", None)
