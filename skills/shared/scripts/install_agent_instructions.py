"""Create RunLedger agent instruction files for supported clients.

This writes safe markdown/config templates that reference environment variables.
It never writes RUNLEDGER_API_KEY values into files.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from agent_instruction_generator import build_client_artifacts, write_artifact


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and "RunLedger Agent Instructions" not in path.read_text(encoding="utf-8", errors="ignore"):
        path.write_text(path.read_text(encoding="utf-8") + "\n\n" + content, encoding="utf-8")
    else:
        path.write_text(content, encoding="utf-8")
    print(f"wrote {path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--client",
        choices=["claude", "codex", "cursor", "windsurf", "devin"],
        required=True,
    )
    parser.add_argument("--repo", default=".", help="Target repo root")
    args = parser.parse_args()

    root = Path(args.repo).resolve()
    for artifact in build_client_artifacts(args.client):
        path = root / artifact.path
        if path.suffix in {".json", ".md", ".mdc"}:
            write_artifact(root, artifact)
            print(f"wrote {path}")
        else:
            write(path, artifact.content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
