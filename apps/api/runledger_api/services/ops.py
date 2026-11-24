from __future__ import annotations

from typing import Any

# The queues celery_app.py actually declares and the workers consume (review P-12).
# The old list named "priority" and "low" queues that nothing consumed.
QUEUE_DESCRIPTIONS: dict[str, dict[str, str]] = {
    "celery": {
        "role": "default",
        "description": "Enrichment, rollups, alerts, gateway health checks and the Kafka outbox.",
    },
    "ingest": {
        "role": "ingest",
        "description": "Event ingest (pipeline.process_events), consumed by the ingest worker.",
    },
    "maintenance": {
        "role": "maintenance",
        "description": "Backups, retention and purges, ML retraining, replay and batch evals.",
    },
}


async def get_queue_depths(redis: Any) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for queue, meta in QUEUE_DESCRIPTIONS.items():
        try:
            depth = int(await redis.llen(queue))
        except Exception:
            depth = 0
        items.append(
            {
                "queue": queue,
                "depth": depth,
                "role": meta["role"],
                "description": meta["description"],
                "status": "busy" if depth > 25 else ("active" if depth > 0 else "idle"),
            }
        )
    return items
