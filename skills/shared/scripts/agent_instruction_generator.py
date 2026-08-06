"""Generate RunLedger agent instruction files from one shared policy template."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


POLICY_TEMPLATE = """# RunLedger Agent Instructions

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


@dataclass(frozen=True)
class GeneratedArtifact:
    path: str
    content: str


def _append_instruction(base: str, extra: str) -> str:
    return f"{base}\n{extra.strip()}\n"


def build_client_artifacts(client: str) -> list[GeneratedArtifact]:
    if client == "claude":
        return [
            GeneratedArtifact(
                "CLAUDE.md",
                _append_instruction(
                    POLICY_TEMPLATE,
                    "Claude-specific: use RunLedger MCP tools before long tasks and record outcomes at task close.",
                ),
            )
        ]
    if client == "codex":
        hooks = {
            "runledger": {
                "enabled": False,
                "note": "Template only. Enable once local Codex hook support is configured.",
                "env": ["RUNLEDGER_BASE_URL", "RUNLEDGER_API_KEY", "RUNLEDGER_WORKSPACE"],
            }
        }
        return [
            GeneratedArtifact(
                "AGENTS.md",
                _append_instruction(
                    POLICY_TEMPLATE,
                    "Codex-specific: apply these instructions to the main agent and every subagent spawned for this repo.",
                ),
            ),
            GeneratedArtifact(".codex/runledger-hooks.template.json", json.dumps(hooks, indent=2) + "\n"),
        ]
    if client == "cursor":
        return [
            GeneratedArtifact(
                ".cursor/rules/runledger.mdc",
                _append_instruction(
                    POLICY_TEMPLATE,
                    "Cursor-specific: use RunLedger MCP and Gateway settings when available for agent mode.",
                ),
            )
        ]
    if client == "windsurf":
        return [
            GeneratedArtifact(
                ".windsurf/rules/runledger.md",
                _append_instruction(
                    POLICY_TEMPLATE,
                    "Windsurf-specific: run budget and policy checks before tool use, and log outcomes for every agent task.",
                ),
            )
        ]
    if client == "devin":
        return [
            GeneratedArtifact(
                "RUNLEDGER_AGENT.md",
                _append_instruction(
                    POLICY_TEMPLATE,
                    "Devin-specific: wrap Devin session creation with RunLedger run start/end and outcome recording.",
                ),
            )
        ]
    raise ValueError(f"Unsupported client: {client}")


def write_artifact(root: Path, artifact: GeneratedArtifact) -> Path:
    path = root / artifact.path
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and "RunLedger Agent Instructions" not in path.read_text(
        encoding="utf-8", errors="ignore"
    ):
        path.write_text(
            path.read_text(encoding="utf-8") + "\n\n" + artifact.content,
            encoding="utf-8",
        )
    else:
        path.write_text(artifact.content, encoding="utf-8")
    return path
