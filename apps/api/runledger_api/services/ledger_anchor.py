"""
Off-box anchoring of sealed ledger snapshots (review cd:M-02).

The signing key lives (encrypted) in the database the ledger attests, so a database
admin who also holds the app secret could re-sign history. Anchoring copies each
sealed snapshot's hash, chain link and manifest digest to the workspace's backup
bucket (S3 or S3-compatible), with S3 Object Lock in COMPLIANCE mode when the bucket
has Object Lock enabled. Verification compares the database copy with the anchor: a
re-signed or re-chained snapshot no longer matches what was written off-box.

Without a backup target the snapshot stays unanchored; ``retry_unanchored`` anchors
it once a target is configured. Without Object Lock the anchor is still useful (it is
outside the database), but a bucket admin could overwrite it; ``anchor_locked``
records which one you have.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.backup_ops import BackupTargetConfig
from runledger_api.models.ledger import LedgerSnapshot

log = structlog.get_logger()

# How long an anchor is write-protected under Object Lock.
ANCHOR_RETENTION_DAYS = 400
_FIELDS = ("hash", "prev_hash", "entries_root", "entry_count")


def anchor_payload(snap: LedgerSnapshot) -> dict[str, Any]:
    return {
        "workspace_id": str(snap.workspace_id),
        "snapshot_date": str(snap.snapshot_date),
        "hash": snap.hash,
        "prev_hash": snap.prev_hash,
        "entries_root": snap.entries_root,
        "entry_count": snap.entry_count,
        "key_id": str(snap.key_id),
        "sealed_at": snap.sealed_at.isoformat() if snap.sealed_at else None,
    }


def _object_key(config: BackupTargetConfig, snap: LedgerSnapshot) -> str:
    prefix = (config.prefix or "").strip("/")
    path = f"ledger-anchors/{snap.workspace_id}/{snap.snapshot_date}.json"
    return f"{prefix}/{path}" if prefix else path


def _client(config: BackupTargetConfig) -> Any:
    import boto3  # noqa: PLC0415
    from botocore.config import Config  # noqa: PLC0415

    from runledger_api.services.kafka_export import resolve_secret_value  # noqa: PLC0415

    return boto3.client(
        "s3",
        endpoint_url=config.endpoint_url or None,
        region_name=config.region or None,
        aws_access_key_id=config.access_key_id or None,
        aws_secret_access_key=resolve_secret_value(config.secret_access_key) or None,
        config=Config(
            s3={"addressing_style": "path" if config.force_path_style else "auto"},
            connect_timeout=5,
            read_timeout=15,
            retries={"max_attempts": 2},
        ),
    )


async def _target(db: AsyncSession, workspace_id: Any) -> BackupTargetConfig | None:
    config = (
        await db.execute(
            select(BackupTargetConfig).where(BackupTargetConfig.workspace_id == workspace_id)
        )
    ).scalar_one_or_none()
    if config is None or not (config.bucket or "").strip():
        return None
    return config


def _put(config: BackupTargetConfig, key: str, body: bytes) -> tuple[bool, str | None]:
    """Write the anchor; returns (Object Lock protects it, version id).

    With Object Lock the bucket is versioned: the locked version can't be deleted or
    changed, but a newer version could be uploaded under the same key, so the anchor
    records and later reads that exact version.
    """
    client = _client(config)
    bucket = config.bucket.strip()
    try:
        resp = client.put_object(
            Bucket=bucket,
            Key=key,
            Body=body,
            ContentType="application/json",
            ObjectLockMode="COMPLIANCE",
            ObjectLockRetainUntilDate=datetime.now(UTC) + timedelta(days=ANCHOR_RETENTION_DAYS),
        )
        return True, resp.get("VersionId")
    except Exception as exc:  # bucket without Object Lock rejects the lock headers
        code = getattr(exc, "response", {}).get("Error", {}).get("Code", "")
        if code not in {"InvalidRequest", "InvalidArgument", "NotImplemented", "AccessDenied"}:
            raise
    resp = client.put_object(Bucket=bucket, Key=key, Body=body, ContentType="application/json")
    return False, resp.get("VersionId")


def _get(config: BackupTargetConfig, key: str, version_id: str | None = None) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"Bucket": config.bucket.strip(), "Key": key}
    if version_id:
        kwargs["VersionId"] = version_id
    obj = _client(config).get_object(**kwargs)
    return json.loads(obj["Body"].read())


def _parse_uri(uri: str) -> tuple[str, str | None]:
    """``s3://bucket/key[?versionId=v]`` → (key, version id)."""
    rest = uri[len("s3://") :] if uri.startswith("s3://") else uri
    path, _, query = rest.partition("?versionId=")
    _, _, key = path.partition("/")
    return key, (query or None)


async def anchor_snapshot(db: AsyncSession, snap: LedgerSnapshot) -> str:
    """Anchor one sealed snapshot. Returns ``anchored``, ``already_anchored``,
    ``no_target``, ``unsealed`` or ``failed: <reason>``. Does not commit."""
    if getattr(snap, "entries_root", None) is None:
        return "unsealed"
    if getattr(snap, "anchor_uri", None):
        return "already_anchored"
    config = await _target(db, snap.workspace_id)
    if config is None:
        return "no_target"
    key = _object_key(config, snap)
    body = json.dumps(anchor_payload(snap), sort_keys=True).encode()
    try:
        locked, version_id = await asyncio.to_thread(_put, config, key, body)
    except Exception as exc:
        log.warning(
            "ledger_anchor_failed", workspace_id=str(snap.workspace_id), error=str(exc)[:200]
        )
        return f"failed: {str(exc)[:200]}"
    snap.anchor_uri = f"s3://{config.bucket.strip()}/{key}" + (
        f"?versionId={version_id}" if version_id else ""
    )
    snap.anchored_at = datetime.now(UTC)
    snap.anchor_locked = locked
    await db.flush()
    log.info(
        "ledger_snapshot_anchored",
        workspace_id=str(snap.workspace_id),
        snapshot_date=str(snap.snapshot_date),
        locked=locked,
    )
    return "anchored"


async def check_anchor(db: AsyncSession, snap: LedgerSnapshot) -> tuple[bool | None, str | None]:
    """Compare a snapshot with its off-box anchor.

    ``(None, reason)`` when it can't be checked (not anchored, no target, bucket
    unreachable); ``(True, None)`` when it matches; ``(False, detail)`` when the
    database copy differs from what was anchored.
    """
    uri = getattr(snap, "anchor_uri", None)
    if not uri:
        return None, "not anchored"
    config = await _target(db, snap.workspace_id)
    if config is None:
        return None, "anchored, but the workspace has no backup target to read it from"
    key, version_id = _parse_uri(uri)
    try:
        anchored = await asyncio.to_thread(_get, config, key, version_id)
    except Exception as exc:
        return None, f"anchor unreadable: {str(exc)[:200]}"
    current = anchor_payload(snap)
    diff = [f for f in _FIELDS if anchored.get(f) != current.get(f)]
    if diff:
        return False, f"database differs from the off-box anchor ({', '.join(diff)})"
    return True, None


async def retry_unanchored(db: AsyncSession, days: int = 30) -> int:
    """Anchor sealed snapshots of the last ``days`` that aren't anchored yet."""
    since = (datetime.now(UTC) - timedelta(days=days)).date()
    pending = list(
        (
            await db.execute(
                select(LedgerSnapshot).where(
                    LedgerSnapshot.entries_root.is_not(None),
                    LedgerSnapshot.anchor_uri.is_(None),
                    LedgerSnapshot.snapshot_date >= since,
                )
            )
        ).scalars()
    )
    done = 0
    for snap in pending:
        if await anchor_snapshot(db, snap) == "anchored":
            done += 1
    return done
