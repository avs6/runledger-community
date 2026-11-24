"""Platform health checks and the system status snapshot.

Shared by ``GET /health`` / ``GET /health/ready`` (review P-19) and the platform-admin
``GET /system/status`` page: database and Redis reachability, migration head, beat
and worker heartbeats, queue depths, the latest backups, and the build each component
runs, so version skew between api, workers and beat shows up (cd:S-06).
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.config import production_problems, settings

log = structlog.get_logger()

STARTED_AT = datetime.now(UTC)
# A missing beat heartbeat is "starting" (not degraded) this long after the API starts.
BEAT_STARTUP_GRACE_SECONDS = 300
# A heartbeat older than this is stale. Beat sends one every 60 s.
HEARTBEAT_STALE_SECONDS = 180

CheckState = Literal["ok", "error", "degraded", "behind", "stale", "starting", "unknown"]


def uptime_seconds() -> float:
    return max(0.0, (datetime.now(UTC) - STARTED_AT).total_seconds())


@lru_cache(maxsize=1)
def alembic_heads() -> tuple[str, ...]:
    """Head revision(s) of the migration scripts shipped with this build."""
    try:
        from alembic.script import ScriptDirectory  # noqa: PLC0415

        import runledger_api  # noqa: PLC0415

        script_dir = Path(runledger_api.__file__).resolve().parent.parent / "alembic"
        if not script_dir.is_dir():
            return ()
        return tuple(sorted(ScriptDirectory(str(script_dir)).get_heads()))
    except Exception as exc:  # pragma: no cover - depends on packaging
        log.warning("alembic_heads_unavailable", error=str(exc))
        return ()


async def check_db(db: AsyncSession) -> CheckState:
    try:
        await db.execute(text("SELECT 1"))
        return "ok"
    except Exception as exc:
        log.warning("db_health_check_failed", error=str(exc))
        return "error"


async def check_redis(redis: Any) -> CheckState:
    try:
        await redis.ping()
        return "ok"
    except Exception as exc:
        log.warning("redis_health_check_failed", error=str(exc))
        return "error"


async def migration_state(db: AsyncSession) -> dict[str, Any]:
    """``ok`` at head, ``behind`` when the database lags this build, else ``unknown``."""
    heads = list(alembic_heads())
    current: list[str] = []
    try:
        result = await db.execute(text("SELECT version_num FROM alembic_version"))
        rows = result.scalars().all() if result is not None else []
        current = sorted(str(r) for r in rows if isinstance(r, str))
    except Exception as exc:
        log.warning("migration_state_failed", error=str(exc))
    state: CheckState
    if not heads or not current:
        state = "unknown"
    elif set(current) == set(heads):
        state = "ok"
    else:
        state = "behind"
    return {"status": state, "current": current, "head": heads}


def _parse_heartbeat(raw: Any) -> dict[str, Any] | None:
    if isinstance(raw, bytes):
        raw = raw.decode()
    if not isinstance(raw, str):
        return None
    try:
        payload = json.loads(raw)
    except ValueError:
        return None
    return payload if isinstance(payload, dict) else None


def _age(payload: dict[str, Any], now: float) -> float | None:
    ts = payload.get("ts")
    return max(0.0, now - float(ts)) if isinstance(ts, int | float) else None


async def beat_state(redis: Any) -> dict[str, Any]:
    from runledger_api.workers.platform import BEAT_KEY  # noqa: PLC0415

    now = time.time()
    payload: dict[str, Any] | None = None
    try:
        payload = _parse_heartbeat(await redis.get(BEAT_KEY))
    except Exception as exc:
        log.warning("beat_heartbeat_read_failed", error=str(exc))
    state: CheckState
    if payload is None:
        state = "starting" if uptime_seconds() < BEAT_STARTUP_GRACE_SECONDS else "stale"
        return {"status": state, "version": None, "build_sha": None, "age_seconds": None}
    age = _age(payload, now)
    state = "ok" if age is not None and age <= HEARTBEAT_STALE_SECONDS else "stale"
    return {
        "status": state,
        "version": payload.get("version"),
        "build_sha": payload.get("build_sha"),
        "age_seconds": round(age, 1) if age is not None else None,
    }


async def worker_states(redis: Any) -> list[dict[str, Any]]:
    from runledger_api.workers.platform import WORKER_KEY_PREFIX  # noqa: PLC0415

    now = time.time()
    items: list[dict[str, Any]] = []
    try:
        keys = [k async for k in redis.scan_iter(match=f"{WORKER_KEY_PREFIX}*", count=100)]
    except Exception as exc:
        log.warning("worker_heartbeat_scan_failed", error=str(exc))
        return items
    for key in keys[:200]:
        try:
            payload = _parse_heartbeat(await redis.get(key))
        except Exception:
            payload = None
        if payload is None:
            continue
        age = _age(payload, now)
        items.append(
            {
                "worker": payload.get("worker"),
                "queues": payload.get("queues", []),
                "version": payload.get("version"),
                "build_sha": payload.get("build_sha"),
                "pid": payload.get("pid"),
                "age_seconds": round(age, 1) if age is not None else None,
                "status": "ok" if age is not None and age <= HEARTBEAT_STALE_SECONDS else "stale",
            }
        )
    items.sort(key=lambda item: str(item.get("worker")))
    return items


async def health_snapshot(db: AsyncSession, redis: Any) -> tuple[bool, dict[str, Any]]:
    """``(healthy, body)`` for /health: degraded when a dependency is down, the database
    is behind this build's migrations, or beat stopped sending heartbeats."""
    db_state = await check_db(db)
    redis_state = await check_redis(redis)
    migrations = await migration_state(db) if db_state == "ok" else {"status": "unknown"}
    beat = (
        await beat_state(redis)
        if redis_state == "ok" and settings.health_require_beat
        else {"status": "unknown"}
    )
    degraded = (
        db_state != "ok"
        or redis_state != "ok"
        or migrations["status"] == "behind"
        or beat["status"] == "stale"
    )
    body = {
        "status": "degraded" if degraded else "ok",
        "db": db_state,
        "redis": redis_state,
        "migrations": migrations["status"],
        "beat": beat["status"],
        "version": settings.runledger_version,
    }
    return not degraded, body


async def _latest_backups(db: AsyncSession) -> dict[str, Any]:
    from runledger_api.models.backup_ops import BackupRun  # noqa: PLC0415

    try:
        rows = (
            (await db.execute(select(BackupRun).order_by(BackupRun.created_at.desc()).limit(5)))
            .scalars()
            .all()
        )
    except Exception as exc:
        log.warning("backup_status_failed", error=str(exc))
        rows = []
    runs = [
        {
            "id": str(row.id),
            "status": row.status,
            "scope": row.backup_scope,
            "trigger_mode": row.trigger_mode,
            "target": row.target,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "completed_at": row.completed_at.isoformat() if row.completed_at else None,
            "size_bytes": row.size_bytes,
            "error": (row.error_detail or "")[:300] or None,
        }
        for row in rows
    ]
    last_success = next((r for r in runs if r["status"] == "success"), None)
    return {"enabled": settings.backup_enabled, "recent": runs, "last_success": last_success}


def _version_skew(components: list[dict[str, Any]]) -> bool:
    shas = {c["build_sha"] for c in components if c.get("build_sha")}
    versions = {c["version"] for c in components if c.get("version")}
    return len(shas) > 1 or len(versions) > 1


async def system_status(db: AsyncSession, redis: Any) -> dict[str, Any]:
    """Platform-admin snapshot for the System status page."""
    from runledger_api.services.ops import get_queue_depths  # noqa: PLC0415

    healthy, health = await health_snapshot(db, redis)
    migrations = await migration_state(db) if health["db"] == "ok" else {"status": "unknown"}
    beat = await beat_state(redis) if health["redis"] == "ok" else {"status": "unknown"}
    workers = await worker_states(redis) if health["redis"] == "ok" else []
    queues = await get_queue_depths(redis) if health["redis"] == "ok" else []

    api = {
        "component": "api",
        "version": settings.runledger_version,
        "build_sha": settings.runledger_build_sha,
        "status": "ok",
    }
    components = [api]
    if beat.get("version"):
        components.append({"component": "beat", **beat})
    components.extend(
        {"component": f"worker {w['worker']}", **w} for w in workers if w["status"] == "ok"
    )

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "healthy": healthy,
        "health": health,
        "environment": settings.environment,
        "uptime_seconds": round(uptime_seconds(), 1),
        "started_at": STARTED_AT.isoformat(),
        "versions": {
            "components": [
                {
                    "component": c["component"],
                    "version": c.get("version"),
                    "build_sha": c.get("build_sha"),
                    "status": c.get("status"),
                }
                for c in components
            ],
            "skew": _version_skew(components),
        },
        "migrations": migrations,
        "beat": beat,
        "workers": workers,
        "queues": queues,
        "backups": await _latest_backups(db) if health["db"] == "ok" else None,
        "config_warnings": production_problems(settings),
    }
