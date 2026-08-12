#!/usr/bin/env python3
"""Master runner for the normalized local demo surfaces."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from demo_scenario import scenario_lines

LABS_README = REPO_ROOT / "scripts" / "scenarios" / "labs" / "README.md"


def _run_script(script: Path, passthrough: list[str]) -> int:
    cmd = [sys.executable, str(script), *passthrough]
    completed = subprocess.run(cmd, cwd=str(REPO_ROOT), check=False)
    return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the canonical RunLedger demo seed, simulator, or labs view."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("scenario", help="Print the canonical org/user/workspace scenario.")

    labs_parser = subparsers.add_parser("labs", help="Print the labs workbook path and scenario.")
    labs_parser.add_argument(
        "--open",
        action="store_true",
        help="Reserved flag for callers that want an explicit labs intent.",
    )

    seed_parser = subparsers.add_parser(
        "seed-demo", help="Run the normalized REST demo seed under scripts/seed_demo.py."
    )
    seed_parser.add_argument("args", nargs=argparse.REMAINDER)

    full_parser = subparsers.add_parser(
        "full-simulate", help="Run scripts/full_simulate.py with passthrough arguments."
    )
    full_parser.add_argument("args", nargs=argparse.REMAINDER)

    args = parser.parse_args()

    if args.command == "scenario":
        print("\n".join(scenario_lines()))
        return 0

    if args.command == "labs":
        print("\n".join(scenario_lines()))
        print("")
        print(f"Labs workbook: {LABS_README}")
        return 0

    if args.command == "seed-demo":
        return _run_script(REPO_ROOT / "scripts" / "seed_demo.py", args.args)

    if args.command == "full-simulate":
        return _run_script(REPO_ROOT / "scripts" / "full_simulate.py", args.args)

    parser.error("Unsupported command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
