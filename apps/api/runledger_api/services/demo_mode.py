from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

DemoAction = Literal["seed", "reset"]
DemoStatus = Literal["idle", "queued", "running", "completed", "failed"]
DemoProfile = Literal["full", "quick", "manual"]

API_ROOT = Path(__file__).resolve().parents[2]


def _discover_repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists() and (parent / "scripts").exists():
            return parent
    return current.parents[2]


REPO_ROOT = _discover_repo_root()
API_ROOT = REPO_ROOT / "apps" / "api" if (REPO_ROOT / "apps" / "api").exists() else REPO_ROOT
DEFAULT_STATE_FILE = Path(tempfile.gettempdir()) / "runledger_demo_mode_state.json"
RUNBOOK_PATH = REPO_ROOT / "docs" / "demo-runbook.md"

DEMO_PROFILES: dict[str, dict[str, Any]] = {
    "full": {
        "id": "full",
        "label": "Full Simulator",
        "kind": "automated",
        "description": "Runs scripts/full_simulate.py for the complete multi-workspace local demo.",
        "entrypoint": str(REPO_ROOT / "scripts" / "full_simulate.py"),
        "runbook_path": str(RUNBOOK_PATH),
    },
    "quick": {
        "id": "quick",
        "label": "Quick Seed",
        "kind": "automated",
        "description": "Runs apps/api/scripts/seed_demo.py for a lightweight REST-only feature seed.",
        "entrypoint": str(API_ROOT / "scripts" / "seed_demo.py"),
        "runbook_path": str(RUNBOOK_PATH),
    },
    "manual": {
        "id": "manual",
        "label": "Hands-on Labs",
        "kind": "manual",
        "description": "Follow the guided workbook under scripts/scenarios/labs.",
        "entrypoint": str(REPO_ROOT / "scripts" / "scenarios" / "labs" / "README.md"),
        "runbook_path": str(REPO_ROOT / "scripts" / "scenarios" / "labs" / "README.md"),
    },
}


def _state_file() -> Path:
    override = os.getenv("RUNLEDGER_DEMO_STATE_FILE")
    return Path(override) if override else DEFAULT_STATE_FILE


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def default_demo_state() -> dict[str, Any]:
    return {
        "status": "idle",
        "action": None,
        "profile": "full",
        "message": "Demo mode has not been run yet.",
        "pid": None,
        "started_at": None,
        "finished_at": None,
        "updated_at": now_iso(),
        "runbook_path": str(RUNBOOK_PATH),
        "available_profiles": list(DEMO_PROFILES.values()),
    }


def read_demo_state() -> dict[str, Any]:
    path = _state_file()
    if not path.exists():
        return default_demo_state()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default_demo_state()
    return {**default_demo_state(), **data}


def write_demo_state(**updates: Any) -> dict[str, Any]:
    state = {
        **read_demo_state(),
        **updates,
        "updated_at": now_iso(),
        "available_profiles": list(DEMO_PROFILES.values()),
    }
    profile = str(state.get("profile") or "full")
    state["runbook_path"] = str(DEMO_PROFILES.get(profile, DEMO_PROFILES["full"])["runbook_path"])
    path = _state_file()
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return state


def _seed_command(profile: str) -> tuple[list[str], str]:
    if profile == "quick":
        return ([sys.executable, "-m", "scripts.demo_mode", "seed", "--profile", "quick"], str(API_ROOT))
    return (
        [sys.executable, "-m", "scripts.demo_mode", "seed", "--profile", "full"],
        str(API_ROOT),
    )


def _reset_command() -> tuple[list[str], str]:
    return ([sys.executable, "-m", "scripts.demo_mode", "reset"], str(API_ROOT))


def launch_demo_process(action: DemoAction, profile: str = "full") -> dict[str, Any]:
    current = read_demo_state()
    if current.get("status") in {"queued", "running"}:
        return {
            "status": "busy",
            "message": f"Demo {current.get('action') or 'task'} already in progress",
            "state": current,
        }

    selected_profile = "full" if action == "reset" else profile
    if selected_profile not in DEMO_PROFILES:
        raise ValueError(f"Unsupported demo profile: {selected_profile}")
    if action == "seed" and DEMO_PROFILES[selected_profile]["kind"] != "automated":
        raise ValueError(f"Demo profile '{selected_profile}' is manual and cannot be launched")

    cmd, cwd = _reset_command() if action == "reset" else _seed_command(selected_profile)
    env = os.environ.copy()
    env["RUNLEDGER_DEMO_STATE_FILE"] = str(_state_file())

    proc = subprocess.Popen(  # noqa: S603
        cmd,
        cwd=cwd,
        env=env,
    )
    profile_label = DEMO_PROFILES[selected_profile]["label"]
    state = write_demo_state(
        status="queued",
        action=action,
        profile=selected_profile,
        message=f"{profile_label} {action} queued.",
        pid=proc.pid,
        started_at=now_iso(),
        finished_at=None,
    )
    return {
        "status": "started",
        "message": f"{profile_label} {action} started in background",
        "state": state,
    }
