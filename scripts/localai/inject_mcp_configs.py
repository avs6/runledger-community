#!/usr/bin/env python3
"""Inject RunLedger MCP config into Claude Desktop and Codex.

The script reads `scripts/.localai-runledger.json` by default and uses the
workspace-scoped keys created by `bootstrap_runledger_org.py`. Existing config
files are backed up before modification.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BRIDGE = ROOT / "scripts" / "runledger" / "mcp_stdio_bridge.py"


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"State file not found: {path}. Run bootstrap_runledger_org.py first.")
    return json.loads(path.read_text(encoding="utf-8"))


def key_for(state: dict[str, Any], workspace_name: str) -> str:
    ws = state.get("workspaces", {}).get(workspace_name, {})
    key = ws.get("api_key")
    if not key:
        raise SystemExit(f"No API key found for workspace '{workspace_name}' in state file.")
    return key


def backup(path: Path) -> None:
    if path.exists():
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        shutil.copy2(path, path.with_suffix(path.suffix + f".bak-{stamp}"))


def inject_claude(path: Path, base_url: str, api_key: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    backup(path)
    doc = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    servers = doc.setdefault("mcpServers", {})
    servers["runledger"] = {
        "command": "python",
        "args": [str(BRIDGE)],
        "env": {
            "RUNLEDGER_BASE_URL": base_url,
            "RUNLEDGER_API_KEY": api_key,
        },
    }
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def _remove_toml_table(text: str, table: str) -> str:
    pattern = re.compile(rf"^\[{re.escape(table)}\]\r?\n(?:^[^\[].*(?:\r?\n)?)*", re.MULTILINE)
    return pattern.sub("", text).rstrip() + "\n"


def inject_codex(path: Path, base_url: str, api_key: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    backup(path)
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    text = _remove_toml_table(text, "mcp_servers.runledger")
    text = _remove_toml_table(text, "mcp_servers.runledger.env")
    block = f"""
[mcp_servers.runledger]
command = "python"
args = [ "{str(BRIDGE).replace('\\', '\\\\')}" ]
startup_timeout_sec = 60

[mcp_servers.runledger.env]
RUNLEDGER_BASE_URL = "{base_url}"
RUNLEDGER_API_KEY = "{api_key}"
"""
    path.write_text(text.rstrip() + "\n" + block.lstrip(), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Configure local Claude Desktop and Codex MCP entries for RunLedger.")
    parser.add_argument("--state-file", default="scripts/.localai-runledger.json")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--claude-config", default=str(Path(os.environ["APPDATA"]) / "Claude" / "claude_desktop_config.json"))
    parser.add_argument("--codex-config", default=str(Path.home() / ".codex" / "config.toml"))
    parser.add_argument("--skip-claude", action="store_true")
    parser.add_argument("--skip-codex", action="store_true")
    args = parser.parse_args()

    state = load_state(Path(args.state_file))
    base_url = (args.base_url or state.get("base_url") or "http://localhost:8201").rstrip("/")

    if not args.skip_claude:
        inject_claude(Path(args.claude_config), base_url, key_for(state, "Claude Desktop"))
        print(f"Claude Desktop MCP updated: {args.claude_config}")
    if not args.skip_codex:
        inject_codex(Path(args.codex_config), base_url, key_for(state, "OpenAI Codex"))
        print(f"Codex MCP updated: {args.codex_config}")

    print("Restart Claude Desktop/Codex after config changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
