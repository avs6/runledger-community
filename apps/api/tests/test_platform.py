"""Platform, infra and auth (review stream W1-I): production validation, health 503,
sliding-window rate limits, Celery queues/limits/schedules, heartbeats, the system
status page, one-time bootstrap and the dev-only demo admin."""

from __future__ import annotations

import json
import time
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

# ── Production validation (P-14) ────────────────────────────────────────────────


def _settings(**overrides: object) -> object:
    from runledger_api.core.config import Settings

    return Settings(_env_file=None, **overrides)  # type: ignore[call-arg]


def test_production_is_the_default_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    assert _settings().environment == "production"  # type: ignore[attr-defined]


def test_production_problems_flag_insecure_defaults() -> None:
    from runledger_api.core.config import production_problems

    problems = production_problems(_settings(environment="production"))  # type: ignore[arg-type]
    text = " ".join(problems)
    assert "SECRET_KEY" in text
    assert "DATABASE_URL" in text
    assert "REDIS_URL" in text


def test_production_problems_clean_config() -> None:
    from runledger_api.core.config import production_problems

    good = _settings(
        environment="production",
        secret_key="x" * 40,
        admin_secret="y" * 24,
        database_url="postgresql+asyncpg://runledger:S3cure-pass@db:5432/runledger",
        redis_url="redis://:S3cure-pass@redis:6379/0",
        cors_origins="https://app.example.com",
    )
    assert production_problems(good) == []  # type: ignore[arg-type]


def test_development_skips_production_checks() -> None:
    from runledger_api.core.config import production_problems

    assert production_problems(_settings(environment="development")) == []  # type: ignore[arg-type]


def test_validation_refuses_to_start_unless_insecure_defaults_allowed() -> None:
    from runledger_api.core.config import _validate_production_secrets

    with pytest.raises(SystemExit):
        _validate_production_secrets(_settings(environment="production"))  # type: ignore[arg-type]
    # Escape hatch for throwaway demos: warns, doesn't exit.
    _validate_production_secrets(
        _settings(environment="production", allow_insecure_defaults=True)  # type: ignore[arg-type]
    )


# ── Sliding-window rate limiter keyed by key id (P-17) ──────────────────────────


class _FakeZRedis:
    """Just enough sorted-set behaviour for sliding_window_hit's pipeline."""

    def __init__(self) -> None:
        self.sets: dict[str, dict[str, float]] = {}

    def pipeline(self) -> _FakeZRedis._Pipe:
        return _FakeZRedis._Pipe(self)

    class _Pipe:
        def __init__(self, redis: _FakeZRedis) -> None:
            self.redis = redis
            self.ops: list[tuple[str, tuple[object, ...]]] = []

        def __getattr__(self, name: str):  # type: ignore[no-untyped-def]
            def record(*args: object, **_kw: object) -> _FakeZRedis._Pipe:
                self.ops.append((name, args))
                return self

            return record

        async def execute(self) -> list[object]:
            out: list[object] = []
            for name, args in self.ops:
                key = str(args[0])
                zset = self.redis.sets.setdefault(key, {})
                if name == "zremrangebyscore":
                    lo, hi = float(args[1]), float(args[2])  # type: ignore[arg-type]
                    for member in [m for m, s in zset.items() if lo <= s <= hi]:
                        del zset[member]
                    out.append(0)
                elif name == "zadd":
                    zset.update(args[1])  # type: ignore[arg-type]
                    out.append(1)
                elif name == "zcard":
                    out.append(len(zset))
                elif name == "zrange":
                    items = sorted(zset.items(), key=lambda kv: kv[1])[:1]
                    out.append(items)
                else:
                    out.append(True)
            return out


async def test_sliding_window_counts_only_the_last_minute() -> None:
    from runledger_api.core.ratelimit import sliding_window_hit

    redis = _FakeZRedis()
    t0 = 1_000_000.0
    for i in range(5):
        count, _ = await sliding_window_hit(redis, "k", 10, now=t0 + i)  # type: ignore[arg-type]
    assert count == 5
    # 59 s after the first hit all five still count (no epoch-minute reset)...
    count, _ = await sliding_window_hit(redis, "k", 10, now=t0 + 59)  # type: ignore[arg-type]
    assert count == 6
    # ...and once the window has slid past them they drop out.
    count, oldest = await sliding_window_hit(redis, "k", 10, now=t0 + 64.5)  # type: ignore[arg-type]
    assert count == 2
    assert oldest == t0 + 59


async def test_identity_is_per_key_not_per_prefix() -> None:
    from runledger_api.core.ratelimit import rate_limit_identity

    def request(token: str | None, **state: object) -> MagicMock:
        req = MagicMock()
        req.state = SimpleNamespace(**state)
        req.headers = {"Authorization": f"Bearer {token}"} if token else {}
        req.client = SimpleNamespace(host="203.0.113.7")
        return req

    a = await rate_limit_identity(request("rl_dev_AAAAAAAA_secret_one"))
    b = await rate_limit_identity(request("rl_dev_AAAAAAAA_secret_two"))
    assert a != b  # same 16-char prefix used to collide
    key_id = uuid.uuid4()
    by_id = await rate_limit_identity(request("anything", api_key=SimpleNamespace(id=key_id)))
    assert by_id == f"key:{key_id}"
    anon = await rate_limit_identity(request(None))
    assert anon == "ip:203.0.113.7"


# ── Celery queues, limits and schedules (P-12, P-20, cd:S-06) ───────────────────


def test_celery_has_limits_queues_and_visibility_timeout() -> None:
    from runledger_api.core.celery_app import ALL_QUEUES, celery_app
    from runledger_api.core.config import settings

    conf = celery_app.conf
    assert conf.task_time_limit and conf.task_soft_time_limit
    assert conf.task_soft_time_limit < conf.task_time_limit
    assert conf.broker_transport_options["visibility_timeout"] > settings.backup_timeout_seconds
    assert {q.name for q in conf.task_queues} == set(ALL_QUEUES)
    assert conf.task_routes["pipeline.process_events"]["queue"] == "ingest"
    assert conf.task_routes["backups.run_scheduled"]["queue"] == "maintenance"
    assert conf.task_annotations["backups.run_scheduled"]["time_limit"] > conf.task_time_limit
    assert conf.worker_max_tasks_per_child


def test_daily_jobs_use_wall_clock_crontab() -> None:
    from celery.schedules import crontab
    from runledger_api.core.celery_app import celery_app

    for name, entry in celery_app.conf.beat_schedule.items():
        schedule = entry["schedule"]
        if isinstance(schedule, int | float):
            # Intervals only for sub-daily jobs: a 24h interval drifts on every restart.
            assert schedule < 86400, name
        else:
            assert isinstance(schedule, crontab), name


def test_every_queue_gets_a_heartbeat_carrying_the_beat_build() -> None:
    from runledger_api.core.celery_app import ALL_QUEUES, celery_app
    from runledger_api.core.config import settings

    beats = [e for e in celery_app.conf.beat_schedule.values() if e["task"] == "platform.heartbeat"]
    assert {e["options"]["queue"] for e in beats} == set(ALL_QUEUES)
    assert all(e["args"][1] == settings.runledger_version for e in beats)


def test_record_heartbeat_writes_beat_and_worker_keys() -> None:
    from runledger_api.workers.platform import BEAT_KEY, WORKER_KEY_PREFIX, record_heartbeat

    store: dict[str, str] = {}
    redis = MagicMock()
    redis.set = lambda key, value, ex=None: store.__setitem__(key, value)
    redis.get = lambda key: store.get(key)
    record_heartbeat(
        redis, worker="w1@host", queue="celery", beat_version="1.2.3", beat_build_sha="abc"
    )
    record_heartbeat(
        redis, worker="w1@host", queue="maintenance", beat_version="1.2.3", beat_build_sha="abc"
    )
    assert json.loads(store[BEAT_KEY])["version"] == "1.2.3"
    worker = json.loads(store[f"{WORKER_KEY_PREFIX}w1@host"])
    assert worker["queues"] == ["celery", "maintenance"]


# ── /health 503 when degraded, readiness migration gate (P-19) ──────────────────


def _client_with(db: AsyncMock, redis: AsyncMock) -> AsyncClient:
    from runledger_api.core.db import get_db
    from runledger_api.core.redis import get_redis
    from runledger_api.main import app

    async def _db():  # type: ignore[no-untyped-def]
        yield db

    async def _redis() -> AsyncMock:
        return redis

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_redis] = _redis
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _db_with_revision(revision: str | None) -> AsyncMock:
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [revision] if revision else []
    db.execute = AsyncMock(return_value=result)
    return db


@pytest.fixture
def _cleanup_overrides():  # type: ignore[no-untyped-def]
    yield
    from runledger_api.main import app

    app.dependency_overrides.clear()


async def test_health_503_when_beat_heartbeat_is_stale(
    monkeypatch: pytest.MonkeyPatch, _cleanup_overrides: None
) -> None:
    from runledger_api.services import system_status

    monkeypatch.setattr(system_status, "alembic_heads", lambda: ("head1",))
    redis = AsyncMock()
    redis.ping = AsyncMock(return_value=True)
    redis.get = AsyncMock(return_value=json.dumps({"version": "x", "ts": time.time() - 3600}))
    async with _client_with(_db_with_revision("head1"), redis) as ac:
        resp = await ac.get("/health")
    assert resp.status_code == 503
    assert resp.json()["beat"] == "stale"


async def test_health_ok_with_fresh_heartbeat_and_migrations_at_head(
    monkeypatch: pytest.MonkeyPatch, _cleanup_overrides: None
) -> None:
    from runledger_api.services import system_status

    monkeypatch.setattr(system_status, "alembic_heads", lambda: ("head1",))
    redis = AsyncMock()
    redis.ping = AsyncMock(return_value=True)
    redis.get = AsyncMock(return_value=json.dumps({"version": "x", "ts": time.time()}))
    async with _client_with(_db_with_revision("head1"), redis) as ac:
        resp = await ac.get("/health")
    assert resp.status_code == 200
    assert resp.json() | {"version": None} == {
        "status": "ok",
        "db": "ok",
        "redis": "ok",
        "migrations": "ok",
        "beat": "ok",
        "version": None,
    }


async def test_ready_503_when_schema_is_behind(
    monkeypatch: pytest.MonkeyPatch, _cleanup_overrides: None
) -> None:
    from runledger_api.services import system_status

    monkeypatch.setattr(system_status, "alembic_heads", lambda: ("head2",))
    redis = AsyncMock()
    redis.ping = AsyncMock(return_value=True)
    async with _client_with(_db_with_revision("head1"), redis) as ac:
        resp = await ac.get("/health/ready")
    assert resp.status_code == 503
    assert resp.json()["detail"]["migrations"] == "behind"


def test_shipped_migrations_have_one_head() -> None:
    from runledger_api.services.system_status import alembic_heads

    assert len(alembic_heads()) == 1


# ── System status page (ENH) ───────────────────────────────────────────────────


async def test_system_status_requires_platform_admin(_cleanup_overrides: None) -> None:
    from fastapi import HTTPException
    from runledger_api.core.deps import require_platform_admin
    from runledger_api.main import app

    async def _deny() -> None:
        raise HTTPException(403, "Platform admin required")

    app.dependency_overrides[require_platform_admin] = _deny
    async with _client_with(_db_with_revision(None), AsyncMock()) as ac:
        resp = await ac.get("/system/status")
    assert resp.status_code == 403


async def test_system_status_reports_versions_workers_and_skew(
    authed_client: AsyncClient,
    mock_redis_client: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from runledger_api.core.config import settings
    from runledger_api.workers.platform import BEAT_KEY, WORKER_KEY_PREFIX

    now = time.time()
    store = {
        BEAT_KEY: json.dumps({"version": "0.0.9", "build_sha": "old", "ts": now}),
        f"{WORKER_KEY_PREFIX}default@h": json.dumps(
            {
                "worker": "default@h",
                "queues": ["celery"],
                "version": settings.runledger_version,
                "build_sha": settings.runledger_build_sha,
                "ts": now,
            }
        ),
    }

    async def _scan_iter(match: str, count: int = 100):  # type: ignore[no-untyped-def]
        for key in store:
            if key.startswith(WORKER_KEY_PREFIX):
                yield key

    mock_redis_client.get = AsyncMock(side_effect=lambda key: store.get(key))
    mock_redis_client.scan_iter = _scan_iter
    mock_redis_client.llen = AsyncMock(return_value=3)

    resp = await authed_client.get("/system/status", headers={"Authorization": "Bearer t"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["beat"]["status"] == "ok"
    assert [w["worker"] for w in body["workers"]] == ["default@h"]
    assert {q["queue"] for q in body["queues"]} == {"celery", "ingest", "maintenance"}
    # Beat on an older build than the API → skew is reported (cd:S-06).
    assert body["versions"]["skew"] is True
    assert "config_warnings" in body


# ── Bootstrap and the dev-only demo admin (P-01) ────────────────────────────────


async def test_bootstrap_status_is_public(client: AsyncClient, mock_db_session: AsyncMock) -> None:
    result = MagicMock()
    result.scalar_one.return_value = 0
    mock_db_session.execute = AsyncMock(return_value=result)
    resp = await client.get("/auth/bootstrap-status")
    assert resp.status_code == 200
    assert resp.json()["needs_bootstrap"] is True


async def test_bootstrap_refused_once_a_platform_admin_exists() -> None:
    from fastapi import HTTPException
    from runledger_api.routers.auth import BootstrapRequest, bootstrap_platform_admin

    db = AsyncMock()
    result = MagicMock()
    result.scalar_one.return_value = 1
    db.execute = AsyncMock(return_value=result)
    with pytest.raises(HTTPException) as exc:
        await bootstrap_platform_admin(
            BootstrapRequest(email="a@example.com", password="Str0ng-password!"),
            db,
        )
    assert exc.value.status_code == 409


async def test_bootstrap_enforces_password_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi import HTTPException
    from runledger_api.core.config import settings

    monkeypatch.setattr(settings, "environment", "production")
    from runledger_api.routers.auth import BootstrapRequest, bootstrap_platform_admin

    db = AsyncMock()
    result = MagicMock()
    result.scalar_one.return_value = 0
    db.execute = AsyncMock(return_value=result)
    with pytest.raises(HTTPException) as exc:
        await bootstrap_platform_admin(
            BootstrapRequest(email="a@example.com", password="short"), db
        )
    assert exc.value.status_code == 422


async def test_dev_seed_admin_login_refused_outside_development(
    client: AsyncClient,
    mock_db_session: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from runledger_api.core.config import DEV_SEED_ADMIN_EMAIL, settings
    from runledger_api.routers import login as login_router

    monkeypatch.setattr(settings, "environment", "production")
    user = SimpleNamespace(
        id=uuid.uuid4(),
        email=DEV_SEED_ADMIN_EMAIL,
        password_hash="x",
        is_active=True,
        email_verified=True,
        is_platform_admin=True,
    )
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    mock_db_session.execute = AsyncMock(return_value=result)
    monkeypatch.setattr(login_router, "verify_password", AsyncMock(return_value=True))
    monkeypatch.setattr(login_router, "assert_login_allowed", AsyncMock())
    monkeypatch.setattr(login_router, "clear_login_failures", AsyncMock())

    resp = await client.post(
        "/auth/login", json={"email": DEV_SEED_ADMIN_EMAIL, "password": "runledger"}
    )
    assert resp.status_code == 403
    assert "development" in resp.json()["detail"]


async def test_seed_does_nothing_outside_development(monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib.util
    from pathlib import Path

    from runledger_api.core.config import settings

    spec = importlib.util.spec_from_file_location(
        "seed_script", Path(__file__).resolve().parents[1] / "scripts" / "seed.py"
    )
    assert spec and spec.loader
    seed = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(seed)
    monkeypatch.setattr(settings, "environment", "production")
    session_factory = MagicMock(side_effect=AssertionError("must not open a session"))
    monkeypatch.setattr(seed, "AsyncSessionLocal", session_factory)
    await seed.seed()
    session_factory.assert_not_called()


# ── Backups: restore gate and network pg_dump (P-21, P-22) ──────────────────────


async def test_restore_drill_gated_by_backup_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi import HTTPException
    from runledger_api.routers import settings as settings_router

    monkeypatch.setattr(settings_router.app_settings, "backup_enabled", False)
    with pytest.raises(HTTPException) as exc:
        await settings_router.run_restore_drill(
            auth=(SimpleNamespace(id=uuid.uuid4()), None),  # type: ignore[arg-type]
            db=AsyncMock(),
        )
    assert exc.value.status_code == 400


def test_backups_use_network_pg_dump(monkeypatch: pytest.MonkeyPatch) -> None:
    from runledger_api.services import backup_ops, pg_backup

    assert "runledger_api.services.pg_backup" in backup_ops.resolve_backup_command()
    assert "docker" not in backup_ops.resolve_backup_command()
    assert (
        pg_backup._libpq_url("postgresql+asyncpg://u:p@db:5432/rl") == "postgresql://u:p@db:5432/rl"
    )
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@db:5432/rl")
    monkeypatch.setenv("MEMORY_DB_URL", "postgresql://l:l@mem:5432/letta")
    assert [p for p, _ in pg_backup._database_urls()] == ["control-plane", "memory-db"]


def test_restore_cli_requires_backup_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from runledger_api.services import pg_backup

    monkeypatch.setenv("BACKUP_ENABLED", "false")
    with pytest.raises(SystemExit, match="BACKUP_ENABLED"):
        pg_backup.restore("bucket", confirm=True)


# ── Feature flags removed (P-11) ───────────────────────────────────────────────


def test_feature_flags_endpoint_removed() -> None:
    from runledger_api.main import app

    paths = {getattr(r, "path", "") for r in app.routes}
    assert "/settings/ops/feature-flags" not in paths
    from runledger_api.core.config import Settings

    assert "feature_flags" not in Settings.model_fields
