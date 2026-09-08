from __future__ import annotations

import argparse
import subprocess
import sys

from runledger_api.services.demo_mode import REPO_ROOT, now_iso, write_demo_state

RUN_DEMO = REPO_ROOT / "scripts" / "run_demo.py"


def _run_script(*args: str) -> None:
    subprocess.run(
        [sys.executable, str(RUN_DEMO), *args],
        cwd=str(REPO_ROOT),
        check=True,
    )


def _run_seed(profile: str) -> None:
    if profile == "quick":
        write_demo_state(
            status="running",
            action="seed",
            profile="quick",
            message="Resetting demo data, then running quick REST demo seed.",
        )
        _run_script("cleanup")
        _run_script("seed-demo")
        write_demo_state(
            status="completed",
            action="seed",
            profile="quick",
            message="Quick REST demo seed completed successfully from a clean slate.",
            finished_at=now_iso(),
        )
        return

    write_demo_state(
        status="running",
        action="seed",
        profile="full",
        message="Running full simulator with scenarios, governance, guardrails, intelligence, and agent ops.",
    )
    _run_script("full-simulate")
    write_demo_state(
        status="completed",
        action="seed",
        profile="full",
        message="Full simulator completed successfully.",
        finished_at=now_iso(),
    )


def _run_reset() -> None:
    write_demo_state(
        status="running",
        action="reset",
        profile="full",
        message="Resetting demo data to a clean slate.",
    )
    _run_script("cleanup")
    write_demo_state(
        status="completed",
        action="reset",
        profile="full",
        message="Demo data reset completed successfully.",
        finished_at=now_iso(),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run demo seed/reset tasks with tracked state.")
    parser.add_argument("action", choices=["seed", "reset"])
    parser.add_argument("--profile", choices=["full", "quick"], default="full")
    args = parser.parse_args()

    try:
        if args.action == "seed":
            _run_seed(args.profile)
        else:
            _run_reset()
    except Exception as exc:  # noqa: BLE001
        write_demo_state(
            status="failed",
            action=args.action,
            profile=args.profile if args.action == "seed" else "full",
            message=str(exc),
            finished_at=now_iso(),
        )
        raise


if __name__ == "__main__":
    main()
