"""Validate RunLedger publishable skill scaffolds.

The default validation checks that each client skill can generate the expected
repo instruction files. Use ``--smoke`` to also send one telemetry smoke run per
client to the configured RunLedger workspace.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


CLIENTS = ("claude", "codex", "cursor", "devin")
EXPECTED_FILES = {
    "claude": ("CLAUDE.md",),
    "codex": ("AGENTS.md", ".codex/runledger-hooks.template.json"),
    "cursor": (".cursor/rules/runledger.mdc",),
    "devin": ("RUNLEDGER_AGENT.md",),
}


def run(command: list[str], *, env: dict[str, str] | None = None) -> None:
    subprocess.run(command, check=True, env=env)


def validate_instruction_generation(repo_root: Path, skills_root: Path) -> None:
    installer = skills_root / "shared" / "scripts" / "install_agent_instructions.py"
    for client in CLIENTS:
        run([sys.executable, str(installer), "--client", client, "--repo", str(repo_root)])
        for relative in EXPECTED_FILES[client]:
            path = repo_root / relative
            if not path.exists():
                raise SystemExit(f"{client}: expected file was not generated: {path}")
            content = path.read_text(encoding="utf-8", errors="ignore")
            if "RUNLEDGER_API_KEY" not in content:
                raise SystemExit(f"{client}: generated file is missing RUNLEDGER_API_KEY env guidance: {path}")
    print("instruction generation: ok")


def validate_smoke(skills_root: Path) -> None:
    if not os.getenv("RUNLEDGER_API_KEY"):
        raise SystemExit("RUNLEDGER_API_KEY is required for --smoke")
    smoke = skills_root / "shared" / "scripts" / "runledger_smoke.py"
    for client in CLIENTS:
        run(
            [
                sys.executable,
                str(smoke),
                "--client",
                client,
                "--task",
                f"{client} connector validation",
            ]
        )
    print("smoke telemetry: ok")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate RunLedger publishable skills.")
    parser.add_argument("--skills-root", default="skills")
    parser.add_argument("--smoke", action="store_true", help="also send telemetry smoke runs")
    args = parser.parse_args()

    skills_root = Path(args.skills_root).resolve()
    with tempfile.TemporaryDirectory(prefix="runledger-skill-validate-") as temp_dir:
        validate_instruction_generation(Path(temp_dir), skills_root)
    if args.smoke:
        validate_smoke(skills_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
