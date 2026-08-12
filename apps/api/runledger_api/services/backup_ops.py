from __future__ import annotations

import asyncio
import hashlib
import json
import os
import subprocess
import sys
import uuid
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from runledger_api.core.config import settings
from runledger_api.models.backup_ops import BackupRun, BackupSnapshot, BackupTargetConfig
from runledger_api.services import kafka_export

log = structlog.get_logger()


def _discover_repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists() and (parent / "scripts").exists():
            return parent
    return current.parents[2]


REPO_ROOT = _discover_repo_root()
API_ROOT = REPO_ROOT / "apps" / "api" if (REPO_ROOT / "apps" / "api").exists() else REPO_ROOT


def _make_engine_and_factory() -> tuple[Any, async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    return engine, async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def _default_backup_command() -> str:
    script = REPO_ROOT / "scripts" / "localai" / "localai_s3_backup.py"
    if script.exists():
        return subprocess.list2cmdline([sys.executable, str(script), "backup"])
    return ""


def _default_backup_helper_command(action: str) -> str:
    script = REPO_ROOT / "scripts" / "localai" / "localai_s3_backup.py"
    if script.exists():
        return subprocess.list2cmdline([sys.executable, str(script), action])
    return ""


def resolve_backup_command() -> str:
    return settings.backup_command.strip() or _default_backup_command()


def resolve_backup_target(config: BackupTargetConfig | None = None) -> str | None:
    if config is not None and config.bucket.strip():
        return f"s3://{config.bucket.strip()}"
    if settings.backup_target.strip():
        return settings.backup_target.strip()
    if _default_backup_command():
        return "localai-s3://runledger-backups"
    return None


def _command_env(config: BackupTargetConfig | None) -> dict[str, str]:
    env = os.environ.copy()
    if config is None:
        return env
    env["RUNLEDGER_LOCALAI_S3_BUCKET"] = config.bucket
    if config.endpoint_url:
        env["RUNLEDGER_BACKUP_ENDPOINT_URL"] = config.endpoint_url
    if config.region:
        env["RUNLEDGER_BACKUP_REGION"] = config.region
    if config.access_key_id:
        env["RUNLEDGER_BACKUP_ACCESS_KEY_ID"] = config.access_key_id
    if config.secret_access_key:
        env["RUNLEDGER_BACKUP_SECRET_ACCESS_KEY"] = config.secret_access_key
    env["RUNLEDGER_BACKUP_FORCE_PATH_STYLE"] = "true" if config.force_path_style else "false"
    env["RUNLEDGER_BACKUP_INCLUDE_MEMORY_DB"] = "true" if config.include_memory_db else "false"
    env["RUNLEDGER_BACKUP_ENCRYPTION_MODE"] = config.encryption_mode
    return env


def _clip(text: str | None, limit: int = 4000) -> str | None:
    if not text:
        return None
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def _parse_backup_summary(stdout_text: str) -> dict[str, Any] | None:
    for line in reversed(stdout_text.splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if payload.get("kind") == "runledger_backup_summary":
            return payload
    return None


async def _run_command(command: str, *, env: dict[str, str] | None = None) -> tuple[int, str, str, bool]:
    proc = await asyncio.create_subprocess_shell(
        command,
        cwd=str(REPO_ROOT),
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    timed_out = False
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(),
            timeout=settings.backup_timeout_seconds,
        )
    except TimeoutError:
        timed_out = True
        proc.kill()
        stdout, stderr = await proc.communicate()
    return (
        proc.returncode,
        stdout.decode("utf-8", errors="replace"),
        stderr.decode("utf-8", errors="replace"),
        timed_out,
    )


async def list_backup_runs(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    limit: int = 20,
) -> tuple[list[BackupRun], int]:
    rows = (
        (
            await db.execute(
                select(BackupRun)
                .where(BackupRun.workspace_id == workspace_id)
                .order_by(BackupRun.created_at.desc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    total = int(
        (
            await db.execute(
                select(func.count(BackupRun.id)).where(BackupRun.workspace_id == workspace_id)
            )
        ).scalar_one()
        or 0
    )
    return list(rows), total


async def get_backup_config(db: AsyncSession, workspace_id: uuid.UUID) -> BackupTargetConfig | None:
    return (
        await db.execute(
            select(BackupTargetConfig).where(BackupTargetConfig.workspace_id == workspace_id)
        )
    ).scalar_one_or_none()


async def upsert_backup_config(
    db: AsyncSession, workspace_id: uuid.UUID, payload: dict[str, Any]
) -> BackupTargetConfig:
    config = await get_backup_config(db, workspace_id)
    if config is None:
        config = BackupTargetConfig(workspace_id=workspace_id, **payload)
        db.add(config)
    else:
        for key, value in payload.items():
            setattr(config, key, value)
    await db.commit()
    await db.refresh(config)
    return config


async def list_backup_snapshots(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    limit: int = 20,
) -> tuple[list[BackupSnapshot], int]:
    rows = (
        (
            await db.execute(
                select(BackupSnapshot)
                .where(BackupSnapshot.workspace_id == workspace_id)
                .order_by(BackupSnapshot.created_at.desc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    total = int(
        (
            await db.execute(
                select(func.count(BackupSnapshot.id)).where(BackupSnapshot.workspace_id == workspace_id)
            )
        ).scalar_one()
        or 0
    )
    return list(rows), total


async def queue_backup_run(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    triggered_by: str | None = None,
    *,
    trigger_mode: str = "manual",
) -> BackupRun:
    config = await get_backup_config(db, workspace_id)
    backup = BackupRun(
        workspace_id=workspace_id,
        trigger_mode=trigger_mode,
        status="queued",
        backup_scope="full",
        target=resolve_backup_target(config),
        command=resolve_backup_command() or None,
        triggered_by=triggered_by,
    )
    db.add(backup)
    await db.commit()
    await db.refresh(backup)
    asyncio.create_task(_execute_backup_run(backup.id, workspace_id))
    return backup


async def test_backup_connection(config: BackupTargetConfig | None = None) -> dict[str, Any]:
    command = _default_backup_helper_command("ensure-bucket")
    if not command:
        return {"ok": False, "message": "Local backup helper script is not available."}
    exit_code, stdout_text, stderr_text, timed_out = await _run_command(
        command, env=_command_env(config)
    )
    ok = exit_code == 0 and not timed_out
    return {
        "ok": ok,
        "message": (
            "Backup target is reachable."
            if ok
            else (
                f"Backup connectivity timed out after {settings.backup_timeout_seconds}s."
                if timed_out
                else _clip(stderr_text or stdout_text, limit=500) or "Connectivity test failed."
            )
        ),
        "details": {
            "command": command,
            "stdout_excerpt": _clip(stdout_text, limit=1000),
            "stderr_excerpt": _clip(stderr_text, limit=1000),
        },
    }


async def queue_restore_drill(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    triggered_by: str | None = None,
) -> BackupRun:
    config = await get_backup_config(db, workspace_id)
    backup = BackupRun(
        workspace_id=workspace_id,
        trigger_mode="manual",
        status="queued",
        backup_scope="restore-drill",
        target=resolve_backup_target(config),
        command=_default_backup_helper_command("list") or None,
        triggered_by=triggered_by,
    )
    db.add(backup)
    await db.commit()
    await db.refresh(backup)
    asyncio.create_task(_execute_backup_run(backup.id, workspace_id))
    return backup


async def backup_alert_status(db: AsyncSession, workspace_id: uuid.UUID) -> dict[str, Any]:
    config = await get_backup_config(db, workspace_id)
    rows = (
        (
            await db.execute(
                select(BackupRun)
                .where(BackupRun.workspace_id == workspace_id)
                .order_by(BackupRun.created_at.desc())
                .limit(10)
            )
        )
        .scalars()
        .all()
    )
    latest = rows[0] if rows else None
    failed_count = sum(1 for row in rows if row.status == "failed")
    stale = False
    if config is not None and config.schedule_enabled:
        stale = latest is None or latest.completed_at is None or (datetime.now(UTC) - latest.completed_at).total_seconds() > 60 * 60 * 36
    return {
        "latest_status": latest.status if latest else "missing",
        "latest_completed_at": latest.completed_at.isoformat() if latest and latest.completed_at else None,
        "failed_recent_runs": failed_count,
        "schedule_enabled": bool(config.schedule_enabled) if config is not None else False,
        "stale_backup": stale,
        "has_alert": latest is None or latest.status == "failed" or failed_count >= 2 or stale,
        "message": (
            "No backup runs have been recorded yet."
            if latest is None
            else "Scheduled backup is stale."
            if stale
            else "Recent backup failures need attention."
            if latest.status == "failed" or failed_count >= 2
            else "Backup posture looks healthy."
        ),
    }


async def _publish_backup_event(
    *,
    db: AsyncSession,
    workspace_id: uuid.UUID,
    backup: BackupRun,
    event_type: str,
) -> None:
    payload = {
        "backup_run_id": str(backup.id),
        "run_id": str(backup.id),
        "target": backup.target,
        "status": backup.status,
        "size_bytes": backup.size_bytes,
        "checksum": backup.checksum,
        "trigger_mode": backup.trigger_mode,
        "started_at": backup.started_at.isoformat() if backup.started_at else None,
        "completed_at": backup.completed_at.isoformat() if backup.completed_at else None,
        "idempotency_key": f"{workspace_id}:{event_type}:{backup.id}",
        "source": "runledger.backup",
    }
    await kafka_export.publish_event(
        db,
        workspace_id=workspace_id,
        event_type=event_type,
        payload=payload,
    )
    await db.commit()


async def _execute_backup_run(backup_id: uuid.UUID, workspace_id: uuid.UUID) -> None:
    engine, factory = _make_engine_and_factory()
    try:
        command_env: dict[str, str] | None = None
        async with factory() as db:
            backup = await db.get(BackupRun, backup_id)
            if backup is None:
                return
            config = await get_backup_config(db, workspace_id)
            command = backup.command or resolve_backup_command()
            backup.command = command or None
            backup.target = backup.target or resolve_backup_target(config)
            backup.status = "running"
            backup.started_at = datetime.now(UTC)
            command_env = _command_env(config)
            await db.commit()

        if not command:
            async with factory() as db:
                backup = await db.get(BackupRun, backup_id)
                if backup is None:
                    return
                backup.status = "failed"
                backup.completed_at = datetime.now(UTC)
                backup.error_detail = (
                    "No backup command configured. Set BACKUP_COMMAND or use the LocalAI helper script."
                )
                await _publish_backup_event(
                    db=db,
                    workspace_id=workspace_id,
                    backup=backup,
                    event_type="backup.failed",
                )
            return

        exit_code, stdout_text, stderr_text, timed_out = await _run_command(command, env=command_env)
        error_text = stderr_text or stdout_text
        summary = _parse_backup_summary(stdout_text)

        async with factory() as db:
            backup = await db.get(BackupRun, backup_id)
            if backup is None:
                return
            backup.completed_at = datetime.now(UTC)
            backup.output_excerpt = _clip(stdout_text or stderr_text)
            backup.details = {
                "exit_code": exit_code,
                "timed_out": timed_out,
                "stderr_excerpt": _clip(stderr_text),
            }
            if summary:
                backup.size_bytes = int(summary.get("total_size_bytes") or 0) or None
                backup.checksum = str(summary.get("checksum") or "") or None
                backup.details["artifacts"] = summary.get("artifacts")
                backup.details["bucket"] = summary.get("bucket")
                backup.details["manifest_key"] = summary.get("manifest_key")
            elif stdout_text:
                backup.size_bytes = len(stdout_text.encode("utf-8"))
                backup.checksum = hashlib.sha256(stdout_text.encode("utf-8")).hexdigest()
            if exit_code == 0 and not timed_out:
                backup.status = "success"
                if summary and summary.get("bucket"):
                    snapshot = BackupSnapshot(
                        workspace_id=workspace_id,
                        backup_run_id=backup.id,
                        snapshot_type=backup.backup_scope,
                        bucket=str(summary.get("bucket")),
                        prefix="control-plane",
                        manifest_key=summary.get("manifest_key"),
                        checksum=backup.checksum,
                        total_size_bytes=backup.size_bytes,
                        artifact_count=len(summary.get("artifacts") or []),
                        artifacts={"items": summary.get("artifacts") or []},
                        integrity_status="verified" if backup.checksum else "pending",
                        verified_at=datetime.now(UTC) if backup.checksum else None,
                    )
                    db.add(snapshot)
                await _publish_backup_event(
                    db=db,
                    workspace_id=workspace_id,
                    backup=backup,
                    event_type="backup.completed",
                )
                log.info("backup.run.success", backup_run_id=str(backup.id))
            else:
                backup.status = "failed"
                backup.error_detail = (
                    f"Backup timed out after {settings.backup_timeout_seconds}s"
                    if timed_out
                    else _clip(error_text, limit=2000)
                )
                await _publish_backup_event(
                    db=db,
                    workspace_id=workspace_id,
                    backup=backup,
                    event_type="backup.failed",
                )
                log.warning(
                    "backup.run.failed",
                    backup_run_id=str(backup.id),
                    exit_code=exit_code,
                    timed_out=timed_out,
                )
    finally:
        await engine.dispose()


async def run_scheduled_backups() -> int:
    engine, factory = _make_engine_and_factory()
    queued = 0
    try:
        now = datetime.now(UTC)
        today = date.today()
        async with factory() as db:
            configs = (
                (
                    await db.execute(
                        select(BackupTargetConfig).where(BackupTargetConfig.schedule_enabled.is_(True))
                    )
                )
                .scalars()
                .all()
            )
            for config in configs:
                if config.run_hour_utc != now.hour:
                    continue
                existing = (
                    await db.execute(
                        select(BackupRun)
                        .where(
                            BackupRun.workspace_id == config.workspace_id,
                            BackupRun.trigger_mode == "scheduled",
                            func.date(BackupRun.created_at) == today,
                        )
                        .limit(1)
                    )
                ).scalar_one_or_none()
                if existing is not None:
                    continue
                await queue_backup_run(
                    db,
                    config.workspace_id,
                    triggered_by="system",
                    trigger_mode="scheduled",
                )
                queued += 1
        return queued
    finally:
        await engine.dispose()
