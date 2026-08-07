#!/usr/bin/env python3
r"""Back up and restore local RunLedger artifacts to S3-compatible object storage.

This helper is used by the dashboard backup flows and local demo environments.
It supports AWS S3, MinIO, and other S3-compatible targets through the standard
AWS environment variables plus optional endpoint override.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import boto3
from botocore.client import Config


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _s3_client():
    endpoint_url = _env("RUNLEDGER_BACKUP_ENDPOINT_URL") or None
    region = _env("RUNLEDGER_BACKUP_REGION", "us-east-1")
    access_key = _env("RUNLEDGER_BACKUP_ACCESS_KEY_ID") or None
    secret_key = _env("RUNLEDGER_BACKUP_SECRET_ACCESS_KEY") or None
    force_path_style = _env("RUNLEDGER_BACKUP_FORCE_PATH_STYLE", "true").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        region_name=region or None,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(s3={"addressing_style": "path" if force_path_style else "auto"}),
    )


def _bucket_name(raw: str) -> str:
    value = raw.strip()
    if value.startswith("s3://"):
        value = value[5:]
    return value.strip("/").split("/", 1)[0]


def _run(
    cmd: list[str], *, input_bytes: bytes | None = None, capture: bool = False
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        cmd,
        input=input_bytes,
        check=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def ensure_bucket(bucket: str) -> None:
    client = _s3_client()
    name = _bucket_name(bucket)
    try:
        client.head_bucket(Bucket=name)
        return
    except Exception:
        pass
    region = _env("RUNLEDGER_BACKUP_REGION", "us-east-1")
    if region and region != "us-east-1":
        client.create_bucket(
            Bucket=name,
            CreateBucketConfiguration={"LocationConstraint": region},
        )
    else:
        client.create_bucket(Bucket=name)


def upload_file(local_file: Path, bucket: str, key: str) -> None:
    client = _s3_client()
    encryption_mode = _env("RUNLEDGER_BACKUP_ENCRYPTION_MODE", "server_side")
    extra_args: dict[str, str] | None = None
    if encryption_mode == "server_side":
        extra_args = {"ServerSideEncryption": "AES256"}
    client.upload_file(str(local_file), _bucket_name(bucket), key, ExtraArgs=extra_args or {})


def list_objects(bucket: str) -> list[dict[str, Any]]:
    client = _s3_client()
    paginator = client.get_paginator("list_objects_v2")
    rows: list[dict[str, Any]] = []
    for page in paginator.paginate(Bucket=_bucket_name(bucket)):
        for item in page.get("Contents", []):
            rows.append(item)
    rows.sort(key=lambda item: item["Key"])
    return rows


def latest_object(bucket: str, prefix: str) -> str:
    keys = [item["Key"] for item in list_objects(bucket) if item["Key"].startswith(prefix + "/")]
    if not keys:
        raise SystemExit(f"No backup found in s3://{_bucket_name(bucket)}/{prefix}/")
    return keys[-1]


def download_latest(bucket: str, prefix: str, dest_dir: Path) -> Path:
    client = _s3_client()
    key = latest_object(bucket, prefix)
    local_file = dest_dir / Path(key).name
    client.download_file(_bucket_name(bucket), key, str(local_file))
    return local_file


def _artifact(prefix: str, file: Path, payload: bytes) -> dict[str, object]:
    return {
        "name": file.name,
        "prefix": prefix,
        "key": f"{prefix}/{file.name}",
        "size_bytes": len(payload),
        "checksum": hashlib.sha256(payload).hexdigest(),
    }


def backup(bucket: str) -> None:
    ensure_bucket(bucket)
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    include_memory = _env("RUNLEDGER_BACKUP_INCLUDE_MEMORY_DB", "true").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    artifacts: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="runledger-backup-") as td:
        temp = Path(td)
        control_plane = temp / f"control-plane-{ts}.dump"
        print("[control-plane] pg_dump runledger-postgres")
        dump = _run(
            ["docker", "exec", "runledger-postgres", "pg_dump", "-U", "runledger", "-Fc", "runledger"],
            capture=True,
        )
        control_plane.write_bytes(dump.stdout)
        upload_file(control_plane, bucket, f"control-plane/{control_plane.name}")
        artifacts.append(_artifact("control-plane", control_plane, dump.stdout))

        if include_memory:
            memory_db = temp / f"memory-db-{ts}.dump"
            print("[memory-db] pg_dump runledger-memory-db")
            try:
                dump = _run(
                    ["docker", "exec", "runledger-memory-db", "pg_dump", "-U", "letta", "-Fc", "letta"],
                    capture=True,
                )
                memory_db.write_bytes(dump.stdout)
                upload_file(memory_db, bucket, f"memory-db/{memory_db.name}")
                artifacts.append(_artifact("memory-db", memory_db, dump.stdout))
            except subprocess.CalledProcessError:
                print("  memory DB backup skipped; container not available", file=sys.stderr)

        print(f"Backup uploaded to s3://{_bucket_name(bucket)}/ with timestamp {ts}")
        summary_input = "|".join(f"{a['name']}:{a['checksum']}" for a in artifacts).encode("utf-8")
        print(
            json.dumps(
                {
                    "kind": "runledger_backup_summary",
                    "bucket": _bucket_name(bucket),
                    "timestamp": ts,
                    "artifacts": artifacts,
                    "manifest_key": f"manifests/{ts}.json",
                    "total_size_bytes": sum(int(a["size_bytes"]) for a in artifacts),
                    "checksum": hashlib.sha256(summary_input).hexdigest() if artifacts else None,
                }
            )
        )


def restore(bucket: str, *, confirm: bool) -> None:
    if not confirm:
        raise SystemExit("Restore is destructive. Re-run with --confirm-restore.")
    with tempfile.TemporaryDirectory(prefix="runledger-restore-") as td:
        temp = Path(td)
        cp_dump = download_latest(bucket, "control-plane", temp)
        print(f"[control-plane] restoring {cp_dump.name}")
        _run(
            [
                "docker",
                "exec",
                "-i",
                "runledger-postgres",
                "pg_restore",
                "--clean",
                "--if-exists",
                "--no-owner",
                "--no-acl",
                "-U",
                "runledger",
                "-d",
                "runledger",
            ],
            input_bytes=cp_dump.read_bytes(),
        )

        try:
            mem_dump = download_latest(bucket, "memory-db", temp)
            print(f"[memory-db] restoring {mem_dump.name}")
            _run(
                [
                    "docker",
                    "exec",
                    "-i",
                    "runledger-memory-db",
                    "pg_restore",
                    "--clean",
                    "--if-exists",
                    "--no-owner",
                    "--no-acl",
                    "-U",
                    "letta",
                    "-d",
                    "letta",
                ],
                input_bytes=mem_dump.read_bytes(),
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  memory DB restore skipped: {exc}", file=sys.stderr)

    print("Restore complete. Restart RunLedger API/worker/beat after restore.")


def list_backups(bucket: str) -> None:
    ensure_bucket(bucket)
    for item in list_objects(bucket):
        print(item["Key"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Use S3-compatible storage as RunLedger backup storage.")
    parser.add_argument("action", choices=["ensure-bucket", "backup", "restore", "list"])
    parser.add_argument("--bucket", default=_env("RUNLEDGER_LOCALAI_S3_BUCKET", "runledger-backups"))
    parser.add_argument("--confirm-restore", action="store_true")
    args = parser.parse_args()

    if args.action == "ensure-bucket":
        ensure_bucket(args.bucket)
        print(f"Bucket ready: s3://{_bucket_name(args.bucket)}")
    elif args.action == "backup":
        backup(args.bucket)
    elif args.action == "restore":
        restore(args.bucket, confirm=args.confirm_restore)
    elif args.action == "list":
        list_backups(args.bucket)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
