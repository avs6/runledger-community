from __future__ import annotations

from typing import Any

QUEUE_DESCRIPTIONS: dict[str, dict[str, str]] = {
    "celery": {
        "role": "default",
        "description": "General background work such as pipeline jobs, exports, and rollups.",
    },
    "priority": {
        "role": "priority",
        "description": "Latency-sensitive work such as budget checks and route health actions.",
    },
    "low": {
        "role": "low",
        "description": "Deferred maintenance work that can tolerate delay.",
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
