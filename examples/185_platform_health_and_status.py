"""
examples/185_platform_health_and_status.py

Watch a RunLedger deployment the way an operator or uptime check would:

  1. GET /health — 200 when healthy, 503 when degraded (database or Redis down, schema
     behind this build, or Celery beat silent). Use the status code, not the body.
  2. GET /health/ready — readiness for load balancers / Kubernetes (schema at head).
  3. GET /system/status — platform admins: workers, queues, beat, migrations, backups,
     and whether api, workers and beat run the same build (version skew).

Exit code is non-zero when the deployment is degraded or skewed, so this can run from
cron or CI as a post-deploy check.

Required env vars:
  RUNLEDGER_API_KEY   a platform admin's session key (for step 3)
Optional:
  RUNLEDGER_BASE_URL  (default http://localhost:8201)
"""

from __future__ import annotations

import os
import sys

import httpx

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8201").rstrip("/")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")


def main() -> int:
    http = httpx.Client(base_url=BASE_URL, timeout=30)
    problems: list[str] = []

    health = http.get("/health")
    body = health.json()
    print(f"/health        {health.status_code}  {body}")
    if health.status_code == 503:
        problems.append(f"degraded: {body}")

    ready = http.get("/health/ready")
    print(f"/health/ready  {ready.status_code}")
    if ready.status_code != 200:
        problems.append("not ready")

    if not API_KEY:
        print("Set RUNLEDGER_API_KEY (platform admin) to read /system/status.")
    else:
        status = http.get("/system/status", headers={"Authorization": f"Bearer {API_KEY}"})
        status.raise_for_status()
        data = status.json()
        print(f"\nenvironment {data['environment']}, API up {data['uptime_seconds']:.0f}s")
        for c in data["versions"]["components"]:
            print(f"  {c['component']:<28} {c['version']}  {c['build_sha']}  {c['status']}")
        if data["versions"]["skew"]:
            problems.append("version skew between api, workers and beat")
        print(f"beat: {data['beat']['status']} (last heartbeat {data['beat'].get('age_seconds')}s ago)")
        for q in data["queues"]:
            print(f"  queue {q['queue']:<12} {q['depth']:>5} waiting")
        backups = data.get("backups") or {}
        last = (backups.get("last_success") or {}).get("completed_at")
        print(f"backups enabled={backups.get('enabled')} last success={last}")
        for warning in data["config_warnings"]:
            problems.append(f"config: {warning}")

    if problems:
        print("\nPROBLEMS:\n  " + "\n  ".join(problems))
        return 1
    print("\nAll good.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
