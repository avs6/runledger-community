"""
GitHub sync service for prompt management.

Pushes prompt versions to a GitHub repo as YAML files and pulls them back.
Each prompt becomes a file at {path_prefix}{name}.yaml containing:
  name, description, variables, versions (list of version objects)

Requires: PyGithub (pip install PyGithub) or uses raw REST API via httpx.
Falls back to raw REST if PyGithub is not installed.
"""

from __future__ import annotations

import base64
import json
import os
from datetime import UTC, datetime
from typing import Any

import httpx
import structlog

log = structlog.get_logger()

GITHUB_API = "https://api.github.com"


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def push_prompts_to_github(
    token: str,
    repo: str,
    branch: str,
    path_prefix: str,
    prompts: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Push a list of prompt dicts to GitHub.
    Each prompt: {name, description, versions: [{version, content, variables, environment, commit_message}]}
    Returns {"pushed": N, "skipped": N, "errors": [...]}
    """
    pushed = 0
    skipped = 0
    errors: list[str] = []

    async with httpx.AsyncClient(timeout=30) as client:
        for prompt in prompts:
            path = f"{path_prefix.rstrip('/')}/{prompt['name']}.yaml"
            content_str = _prompt_to_yaml(prompt)
            content_b64 = base64.b64encode(content_str.encode()).decode()

            # Check if file already exists (to get SHA for update)
            sha = None
            check_url = f"{GITHUB_API}/repos/{repo}/contents/{path}"
            check_r = await client.get(
                check_url,
                headers=_headers(token),
                params={"ref": branch},
            )
            if check_r.status_code == 200:
                sha = check_r.json().get("sha")

            # Create or update
            payload: dict[str, Any] = {
                "message": f"chore(prompts): sync {prompt['name']} from RunLedger",
                "content": content_b64,
                "branch": branch,
            }
            if sha:
                payload["sha"] = sha

            put_r = await client.put(check_url, headers=_headers(token), json=payload)
            if put_r.status_code in (200, 201):
                pushed += 1
            else:
                errors.append(f"{prompt['name']}: {put_r.status_code} {put_r.text[:100]}")

    return {"pushed": pushed, "skipped": skipped, "errors": errors}


async def pull_prompts_from_github(
    token: str,
    repo: str,
    branch: str,
    path_prefix: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Pull all .yaml prompt files from the GitHub repo path.
    Returns (list_of_prompt_dicts, list_of_errors).
    """
    prompts: list[dict[str, Any]] = []
    errors: list[str] = []

    async with httpx.AsyncClient(timeout=30) as client:
        # List directory
        list_url = f"{GITHUB_API}/repos/{repo}/contents/{path_prefix.rstrip('/')}"
        r = await client.get(list_url, headers=_headers(token), params={"ref": branch})
        if r.status_code == 404:
            return [], [f"Path '{path_prefix}' not found in {repo}@{branch}"]
        if r.status_code != 200:
            return [], [f"GitHub API error: {r.status_code}"]

        files = r.json()
        if not isinstance(files, list):
            return [], ["Unexpected response from GitHub — is path_prefix a directory?"]

        for f in files:
            if not isinstance(f, dict) or not f.get("name", "").endswith(".yaml"):
                continue
            # Download file content
            dl_r = await client.get(f["download_url"], headers=_headers(token))
            if dl_r.status_code != 200:
                errors.append(f"{f['name']}: download failed ({dl_r.status_code})")
                continue
            try:
                prompt = _yaml_to_prompt(dl_r.text, f["name"].replace(".yaml", ""))
                prompts.append(prompt)
            except Exception as exc:
                errors.append(f"{f['name']}: parse error — {exc}")

    return prompts, errors


def _prompt_to_yaml(prompt: dict[str, Any]) -> str:
    """Simple YAML serialiser (no PyYAML dependency required)."""
    lines = [
        f"name: {prompt.get('name', '')}",
        f"description: {_yaml_str(prompt.get('description') or '')}",
        "variables:",
    ]
    for v in (prompt.get("variables") or []):
        lines.append(f"  - {v}")
    lines.append("versions:")
    for pv in (prompt.get("versions") or []):
        lines += [
            f"  - version: {pv.get('version', 1)}",
            f"    environment: {pv.get('environment', 'production')}",
            f"    model_hint: {pv.get('model_hint') or ''}",
            f"    commit_message: {_yaml_str(pv.get('commit_message') or '')}",
            "    content: |",
        ]
        for line in (pv.get("content") or "").splitlines():
            lines.append(f"      {line}")
    return "\n".join(lines) + "\n"


def _yaml_str(s: str) -> str:
    if not s:
        return "''"
    if any(c in s for c in (":", "#", "'", "\n")):
        return f'"{s.replace(chr(34), chr(39))}"'
    return s


def _yaml_to_prompt(text: str, name: str) -> dict[str, Any]:
    """Very simple line-based YAML parser for our own format."""
    result: dict[str, Any] = {"name": name, "description": "", "variables": [], "versions": []}
    current_version: dict[str, Any] | None = None
    in_content = False
    content_lines: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip()

        if in_content:
            if line.startswith("      ") or not line.strip():
                content_lines.append(line[6:] if len(line) >= 6 else "")
                continue
            else:
                if current_version is not None:
                    current_version["content"] = "\n".join(content_lines)
                content_lines = []
                in_content = False

        stripped = line.strip()
        if stripped.startswith("name:") and not in_content:
            result["name"] = stripped[5:].strip()
        elif stripped.startswith("description:"):
            result["description"] = stripped[12:].strip().strip("'\"")
        elif stripped == "- version:" or stripped.startswith("- version:"):
            if current_version:
                result["versions"].append(current_version)
            current_version = {"version": int(stripped.split(":")[-1].strip() or "1")}
        elif current_version is not None:
            if stripped.startswith("environment:"):
                current_version["environment"] = stripped[12:].strip()
            elif stripped.startswith("model_hint:"):
                hint = stripped[11:].strip()
                current_version["model_hint"] = hint or None
            elif stripped.startswith("commit_message:"):
                current_version["commit_message"] = stripped[15:].strip().strip("'\"")
            elif stripped == "content: |":
                in_content = True

    if in_content and current_version is not None:
        current_version["content"] = "\n".join(content_lines)
    if current_version:
        result["versions"].append(current_version)

    return result
