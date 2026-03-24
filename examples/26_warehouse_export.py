"""
Example 26 — Warehouse Export (S3 / GCS / R2)
===============================================
Expected cost: $0.00 (export configuration only — no LLM calls)

Demonstrates:
- Registering a warehouse destination (S3-compatible)
- Testing the connection before saving
- Triggering a manual export job
- Polling job status until completion

Prerequisites:
    export RUNLEDGER_API_KEY=rl_live_...
    export AWS_BUCKET=my-runledger-exports  (or R2/GCS bucket)
    export AWS_ACCESS_KEY=...
    export AWS_SECRET_KEY=...
"""

from __future__ import annotations

import os
import time

import httpx

BASE_URL = os.environ.get("RUNLEDGER_BASE_URL", "http://localhost:8000")
API_KEY = os.environ.get("RUNLEDGER_API_KEY", "")
AWS_BUCKET = os.environ.get("AWS_BUCKET", "my-runledger-exports")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY", "")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_KEY", "")

client = httpx.Client(
    base_url=BASE_URL,
    headers={"Authorization": f"Bearer {API_KEY}"},
    timeout=30,
)


def register_destination() -> str:
    """Register an S3 warehouse destination."""
    # Check if one already exists
    resp = client.get("/warehouse/destinations")
    resp.raise_for_status()
    for dest in resp.json().get("items", []):
        if dest["bucket"] == AWS_BUCKET:
            print(f"  Destination exists: {dest['id'][:8]}…")
            return dest["id"]

    payload = {
        "name": f"S3 Export — {AWS_BUCKET}",
        "provider": "s3",
        "bucket": AWS_BUCKET,
        "region": AWS_REGION,
        "prefix": "runledger/",
        "format": "parquet",
        "credentials": {
            "aws_access_key_id": AWS_ACCESS_KEY,
            "aws_secret_access_key": AWS_SECRET_KEY,
        },
    }
    resp = client.post("/warehouse/destinations", json=payload)
    resp.raise_for_status()
    dest_id = resp.json()["id"]
    print(f"  Registered destination: {dest_id[:8]}…")
    return dest_id


def test_connection(dest_id: str) -> bool:
    """Verify RunLedger can write to the bucket."""
    resp = client.post(f"/warehouse/destinations/{dest_id}/test")
    if resp.status_code == 200:
        result = resp.json()
        ok = result.get("ok", False)
        print(f"  Connection test: {'✓ OK' if ok else '✗ FAILED — ' + result.get('error','')}")
        return ok
    print(f"  Connection test: ✗ HTTP {resp.status_code}")
    return False


def trigger_export(dest_id: str) -> str:
    """Trigger an on-demand export job."""
    resp = client.post(f"/warehouse/destinations/{dest_id}/export")
    resp.raise_for_status()
    job_id = resp.json()["id"]
    print(f"  Export job started: {job_id[:8]}…")
    return job_id


def poll_job(dest_id: str, job_id: str, max_wait: int = 120) -> str:
    """Poll until the job completes or times out."""
    deadline = time.time() + max_wait
    while time.time() < deadline:
        resp = client.get(f"/warehouse/destinations/{dest_id}/jobs/{job_id}")
        if resp.status_code != 200:
            break
        job = resp.json()
        status = job.get("status", "unknown")
        rows = job.get("rows_exported", 0)
        print(f"  [{status}] rows_exported={rows}  ", end="\r")
        if status in ("completed", "failed"):
            print()
            return status
        time.sleep(3)
    print()
    return "timeout"


def list_recent_jobs(dest_id: str) -> None:
    """Show the last 5 export jobs."""
    resp = client.get(f"/warehouse/destinations/{dest_id}/jobs", params={"limit": 5})
    if resp.status_code != 200:
        return
    jobs = resp.json().get("items", [])
    print(f"\n  Recent jobs for destination {dest_id[:8]}…:")
    for j in jobs:
        rows = j.get("rows_exported") or 0
        size = j.get("size_bytes") or 0
        print(
            f"    [{j['status']:10s}] {j.get('created_at','')[:10]}  "
            f"rows={rows:6d}  size={size//1024}KB"
        )


def main() -> None:
    print("=== RunLedger Warehouse Export Example ===\n")

    if not AWS_ACCESS_KEY or not AWS_SECRET_KEY:
        print("⚠  AWS_ACCESS_KEY / AWS_SECRET_KEY not set.")
        print("   This example will register a placeholder destination but skip the connection test.\n")

    print("1. Registering warehouse destination…")
    dest_id = register_destination()

    if AWS_ACCESS_KEY and AWS_SECRET_KEY:
        print("2. Testing connection…")
        ok = test_connection(dest_id)
        if not ok:
            print("   Connection failed — check credentials and bucket policy.")
            client.close()
            return

        print("3. Triggering manual export…")
        job_id = trigger_export(dest_id)

        print("4. Waiting for job completion…")
        final_status = poll_job(dest_id, job_id)
        print(f"   Final status: {final_status}")
    else:
        print("2–4. Skipped (no AWS credentials).")

    print("5. Job history:")
    list_recent_jobs(dest_id)

    print(
        "\nExported files are written as Hive-partitioned Parquet:\n"
        f"  s3://{AWS_BUCKET}/runledger/agent_runs/date=YYYY-MM-DD/data.parquet"
    )

    client.close()
    print("\n✓ Done.")


if __name__ == "__main__":
    main()
