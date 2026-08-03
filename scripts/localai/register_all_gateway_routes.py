#!/usr/bin/env python3
"""Register default local gateway routes across all workspaces in LocalAI Agent Stack."""

import json
from pathlib import Path
from urllib import request

state_file = Path("scripts/.localai-runledger.json")
if not state_file.exists():
    print("State file not found")
    exit(1)

state = json.loads(state_file.read_text(encoding="utf-8"))
workspaces = state.get("workspaces", {})

routes_to_add = [
    {"alias": "ollama/qwen2.5-coder", "provider": "ollama", "target_model": "qwen2.5-coder", "base_url": "http://localhost:11434/v1", "priority": 10},
    {"alias": "qwen2.5-coder", "provider": "ollama", "target_model": "qwen2.5-coder", "base_url": "http://localhost:11434/v1", "priority": 10},
    {"alias": "SWE-1.6 Slow", "provider": "ollama", "target_model": "qwen2.5-coder", "base_url": "http://localhost:11434/v1", "priority": 10},
    {"alias": "gpt-4o", "provider": "ollama", "target_model": "qwen2.5-coder", "base_url": "http://localhost:11434/v1", "priority": 10},
    {"alias": "*", "provider": "ollama", "target_model": "qwen2.5-coder", "base_url": "http://localhost:11434/v1", "priority": 100},
]

for ws_name, ws_info in workspaces.items():
    api_key = ws_info.get("api_key")
    if not api_key:
        continue
    for r in routes_to_add:
        try:
            req = request.Request(
                "http://localhost:8201/gateway/routes",
                data=json.dumps(r).encode("utf-8"),
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
                method="POST"
            )
            request.urlopen(req)
            print(f"Registered route '{r['alias']}' for workspace '{ws_name}'")
        except Exception as exc:
            pass

print("Finished registering gateway routes for all workspaces!")
