"""Worker and beat heartbeats.

Beat schedules ``platform.heartbeat`` once a minute on every queue, passing its own
version and build sha as arguments. Whichever worker consumes the message records:

  * ``rl:heartbeat:beat``            — beat is alive and which build it runs
  * ``rl:heartbeat:worker:<host>``   — this worker is consuming ``queue`` and its build

``/health`` turns a stale beat heartbeat into ``degraded`` (review P-19), and the
system status page lists workers, queues and versions so skew between api, workers
and beat is visible (cd:S-06).
"""

from __future__ import annotations

import json
import os
import socket
import time
from typing import Any

import structlog

from runledger_api.core.celery_app import celery_app
from runledger_api.core.config import settings

log = structlog.get_logger()

HEARTBEAT_TTL_SECONDS = 300
BEAT_KEY = "rl:heartbeat:beat"
WORKER_KEY_PREFIX = "rl:heartbeat:worker:"


def _worker_name(task: Any) -> str:
    hostname = getattr(getattr(task, "request", None), "hostname", None)
    return str(hostname or socket.gethostname())


def record_heartbeat(
    redis: Any,
    *,
    worker: str,
    queue: str,
    beat_version: str,
    beat_build_sha: str,
    now: float | None = None,
) -> None:
    """Write the beat and worker heartbeat keys (sync Redis client)."""
    ts = time.time() if now is None else now
    redis.set(
        BEAT_KEY,
        json.dumps({"version": beat_version, "build_sha": beat_build_sha, "ts": ts}),
        ex=HEARTBEAT_TTL_SECONDS,
    )
    key = f"{WORKER_KEY_PREFIX}{worker}"
    previous_raw = redis.get(key)
    queues: set[str] = {queue}
    if previous_raw:
        try:
            previous = json.loads(previous_raw)
            # Keep queues seen in the last TTL, so a worker on several queues lists all.
            queues |= set(previous.get("queues", []))
        except (ValueError, TypeError):
            pass
    redis.set(
        key,
        json.dumps(
            {
                "worker": worker,
                "queues": sorted(queues),
                "version": settings.runledger_version,
                "build_sha": settings.runledger_build_sha,
                "pid": os.getpid(),
                "ts": ts,
            }
        ),
        ex=HEARTBEAT_TTL_SECONDS,
    )


@celery_app.task(name="platform.heartbeat", bind=True, ignore_result=True)  # type: ignore[untyped-decorator]
def heartbeat(self: Any, queue: str, beat_version: str = "", beat_build_sha: str = "") -> None:
    import redis as redis_sync  # noqa: PLC0415

    client = redis_sync.Redis.from_url(settings.redis_url, socket_timeout=5)
    try:
        record_heartbeat(
            client,
            worker=_worker_name(self),
            queue=queue,
            beat_version=beat_version,
            beat_build_sha=beat_build_sha,
        )
    finally:
        client.close()
