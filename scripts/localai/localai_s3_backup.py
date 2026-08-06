#!/usr/bin/env python3
r"""Back up and restore local RunLedger artifacts to LocalAIStack MinIO.

This is a local-dev companion to the Helm S3 CronJob. It targets the MinIO
container already running in `C:\Users\Abi\Desktop\LocalAIAgentStack`.
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


MINIO_CONTAINER = "langfuse-minio"
MINIO_ALIAS = "localai"


def run(cmd: list[str], *, input_bytes: bytes | None = None, capture: bool = False) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        cmd,
        input=input_bytes,
        check=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def minio_shell(command: str) -> None:
    run(
        [
            "docker",
            "exec",
            MINIO_CONTAINER,
            "sh",
            "-lc",
            f"mc alias set {MINIO_ALIAS} http://localhost:9000 minio langfuse-minio-local >/dev/null && {command}",
        ]
    )


def ensure_bucket(bucket: str) -> None:
    minio_shell(f"mc mb --ignore-existing {MINIO_ALIAS}/{bucket}")


def upload_file(local_file: Path, bucket: str, prefix: str) -> None:
    remote_tmp = f"/tmp/{local_file.name}"
    run(["docker", "cp", str(local_file), f"{MINIO_CONTAINER}:{remote_tmp}"])
    minio_shell(f"mc cp {remote_tmp} {MINIO_ALIAS}/{bucket}/{prefix}/{local_file.name}")
    minio_shell(f"rm -f {remote_tmp} 2>/dev/null || true")


def latest_object(bucket: str, prefix: str) -> str:
    result = run(
        [
            "docker",
            "exec",
            MINIO_CONTAINER,
            "sh",
            "-lc",
            (
                f"mc alias set {MINIO_ALIAS} http://localhost:9000 minio langfuse-minio-local >/dev/null && "
                f"mc ls {MINIO_ALIAS}/{bucket}/{prefix}/ | awk '{{print $NF}}' | sort | tail -1"
            ),
        ],
        capture=True,
    )
    name = result.stdout.decode("utf-8", errors="replace").strip()
    if not name:
        raise SystemExit(f"No backup found in s3://{bucket}/{prefix}/")
    return name


def download_latest(bucket: str, prefix: str, dest_dir: Path) -> Path:
    name = latest_object(bucket, prefix)
    remote_tmp = f"/tmp/{name}"
    minio_shell(f"mc cp {MINIO_ALIAS}/{bucket}/{prefix}/{name} {remote_tmp}")
    local_file = dest_dir / name
    run(["docker", "cp", f"{MINIO_CONTAINER}:{remote_tmp}", str(local_file)])
    minio_shell(f"rm -f {remote_tmp} 2>/dev/null || true")
    return local_file


def backup(bucket: str) -> None:
    ensure_bucket(bucket)
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    artifacts: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="runledger-backup-") as td:
        temp = Path(td)
        control_plane = temp / f"control-plane-{ts}.dump"
        memory_db = temp / f"memory-db-{ts}.dump"

        print("[control-plane] pg_dump runledger-postgres")
        dump = run(["docker", "exec", "runledger-postgres", "pg_dump", "-U", "runledger", "-Fc", "runledger"], capture=True)
        control_plane.write_bytes(dump.stdout)
        upload_file(control_plane, bucket, "control-plane")
        artifacts.append(
            {
                "name": control_plane.name,
                "prefix": "control-plane",
                "size_bytes": len(dump.stdout),
                "checksum": hashlib.sha256(dump.stdout).hexdigest(),
            }
        )

        print("[memory-db] pg_dump runledger-memory-db")
        try:
            dump = run(["docker", "exec", "runledger-memory-db", "pg_dump", "-U", "letta", "-Fc", "letta"], capture=True)
            memory_db.write_bytes(dump.stdout)
            upload_file(memory_db, bucket, "memory-db")
            artifacts.append(
                {
                    "name": memory_db.name,
                    "prefix": "memory-db",
                    "size_bytes": len(dump.stdout),
                    "checksum": hashlib.sha256(dump.stdout).hexdigest(),
                }
            )
        except subprocess.CalledProcessError:
            print("  memory DB backup skipped; container not available", file=sys.stderr)

        print(f"Backup uploaded to MinIO bucket s3://{bucket}/ with timestamp {ts}")
        summary_input = "|".join(f"{a['name']}:{a['checksum']}" for a in artifacts).encode("utf-8")
        print(
            json.dumps(
                {
                    "kind": "runledger_backup_summary",
                    "bucket": bucket,
                    "timestamp": ts,
                    "artifacts": artifacts,
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
        data = cp_dump.read_bytes()
        run(
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
            input_bytes=data,
        )

        try:
            mem_dump = download_latest(bucket, "memory-db", temp)
            print(f"[memory-db] restoring {mem_dump.name}")
            run(
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
    minio_shell(f"mc ls --recursive {MINIO_ALIAS}/{bucket}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Use LocalAIStack MinIO as RunLedger local backup storage.")
    parser.add_argument("action", choices=["ensure-bucket", "backup", "restore", "list"])
    parser.add_argument("--bucket", default=os.getenv("RUNLEDGER_LOCALAI_S3_BUCKET", "runledger-backups"))
    parser.add_argument("--confirm-restore", action="store_true")
    args = parser.parse_args()

    if args.action == "ensure-bucket":
        ensure_bucket(args.bucket)
        print(f"Bucket ready: s3://{args.bucket}")
    elif args.action == "backup":
        backup(args.bucket)
    elif args.action == "restore":
        restore(args.bucket, confirm=args.confirm_restore)
    elif args.action == "list":
        list_backups(args.bucket)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
