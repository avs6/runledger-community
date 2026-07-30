"""Create RunLedger agent instruction files for supported clients.

This writes safe markdown/config templates that reference environment variables.
It never writes RUNLEDGER_API_KEY values into files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


COMMON = """# RunLedger Agent Instructions

Use RunLedger as the telemetry, FinOps, and policy control plane for this repo.

Before expensive or risky work:

- Check budget and policy through RunLedger MCP where available.
- Prefer RunLedger Gateway when a custom OpenAI-compatible base URL is configured.
- Record task start, tool calls, model calls, outcomes, and final status.
- Keep secrets in environment variables. Do not write API keys into markdown.

Environment expected by local helpers:

- `RUNLEDGER_BASE_URL`
- `RUNLEDGER_API_KEY`
- `RUNLEDGER_WORKSPACE`
"""


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and "RunLedger Agent Instructions" not in path.read_text(encoding="utf-8", errors="ignore"):
        path.write_text(path.read_text(encoding="utf-8") + "\n\n" + content, encoding="utf-8")
    else:
        path.write_text(content, encoding="utf-8")
    print(f"wrote {path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--client", choices=["claude", "codex", "cursor", "devin"], required=True)
    parser.add_argument("--repo", default=".", help="Target repo root")
    args = parser.parse_args()

    root = Path(args.repo).resolve()
    if args.client == "claude":
      write(root / "CLAUDE.md", COMMON + "\nClaude-specific: use RunLedger MCP tools before long tasks and record outcomes at task close.\n")
    elif args.client == "codex":
      write(root / "AGENTS.md", COMMON + "\nCodex-specific: apply these instructions to the main agent and every subagent spawned for this repo.\n")
      hooks = {
          "runledger": {
              "enabled": False,
              "note": "Template only. Enable once local Codex hook support is configured.",
              "env": ["RUNLEDGER_BASE_URL", "RUNLEDGER_API_KEY", "RUNLEDGER_WORKSPACE"],
          }
      }
      hook_path = root / ".codex" / "runledger-hooks.template.json"
      hook_path.parent.mkdir(parents=True, exist_ok=True)
      hook_path.write_text(json.dumps(hooks, indent=2) + "\n", encoding="utf-8")
      print(f"wrote {hook_path}")
    elif args.client == "cursor":
      write(root / ".cursor" / "rules" / "runledger.mdc", COMMON + "\nCursor-specific: use RunLedger MCP and Gateway settings when available for agent mode.\n")
    elif args.client == "devin":
      write(root / "RUNLEDGER_AGENT.md", COMMON + "\nDevin-specific: wrap Devin session creation with RunLedger run start/end and outcome recording.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
