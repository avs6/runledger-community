from celery import Celery

from runledger_api.core.config import settings

celery_app = Celery(
    "runledger",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["runledger_api.workers.pipeline"],
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
)
