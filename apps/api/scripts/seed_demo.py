"""Compatibility shim for the canonical repo-root demo seed."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def main() -> None:
    subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "seed_demo.py")],
        cwd=str(REPO_ROOT),
        check=True,
    )


if __name__ == "__main__":
    main()
