"""
Prompt-ref resolution in the gateway (review B-23).

A request may name a managed prompt instead of (or before) its own system message::

    {"model": "chat-default", "prompt": "support-triage@prod",
     "prompt_variables": {"product": "RunLedger"}, "messages": [...]}

Ref forms:

* ``name``             — the latest version in the prompt's default environment
* ``name@<env>``       — the latest version in that environment
                         (``prod`` → ``production``, ``stage`` → ``staging``, ``dev`` → ``development``)
* ``name@<n>`` / ``name@v<n>`` — that exact version number

The rendered content (``{{variable}}`` substitution, the same rule as the SDK) is
prepended as a ``system`` message. The run records ``prompt_ref`` and the resolved
version, and its ``deployment_version`` is ``name:version`` — the key the prompt
version metrics page already reads — so gateway traffic shows up there.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.prompts import Prompt, PromptVersion

_ENV_ALIASES = {
    "prod": "production",
    "production": "production",
    "stage": "staging",
    "staging": "staging",
    "dev": "development",
    "development": "development",
}
_VAR_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_.-]*)\s*\}\}")
_REF_RE = re.compile(r"^(?P<name>[^@\s]+)(?:@(?P<sel>[^@\s]+))?$")


@dataclass(frozen=True)
class PromptRef:
    name: str
    environment: str | None = None
    version: int | None = None


@dataclass(frozen=True)
class ResolvedPrompt:
    ref: str
    name: str
    version: int
    environment: str
    prompt_version_id: uuid.UUID
    content: str
    missing_variables: tuple[str, ...]

    @property
    def deployment_version(self) -> str:
        return f"{self.name}:{self.version}"

    def as_metadata(self) -> dict[str, Any]:
        return {
            "prompt_ref": self.ref,
            "prompt_name": self.name,
            "prompt_version": self.version,
            "prompt_environment": self.environment,
            "prompt_version_id": str(self.prompt_version_id),
        }


def parse_prompt_ref(ref: str) -> PromptRef:
    match = _REF_RE.match(ref.strip())
    if not match:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Invalid prompt ref {ref!r}; use 'name', 'name@prod' or 'name@3'",
        )
    name = match.group("name")
    selector = match.group("sel")
    if selector is None:
        return PromptRef(name=name)
    digits = selector[1:] if selector.lower().startswith("v") else selector
    if digits.isdigit():
        return PromptRef(name=name, version=int(digits))
    return PromptRef(name=name, environment=_ENV_ALIASES.get(selector.lower(), selector.lower()))


def render_prompt(content: str, variables: dict[str, Any] | None) -> tuple[str, list[str]]:
    """``{{var}}`` substitution; unknown variables are left in place and reported."""
    values = variables or {}
    missing: list[str] = []

    def _sub(match: re.Match[str]) -> str:
        key = match.group(1)
        if key in values and values[key] is not None:
            return str(values[key])
        if key not in missing:
            missing.append(key)
        return match.group(0)

    return _VAR_RE.sub(_sub, content), missing


async def resolve_prompt_ref(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    ref: str,
    variables: dict[str, Any] | None = None,
) -> ResolvedPrompt:
    parsed = parse_prompt_ref(ref)
    prompt = (
        await db.execute(
            select(Prompt).where(Prompt.workspace_id == workspace_id, Prompt.name == parsed.name)
        )
    ).scalar_one_or_none()
    if prompt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Prompt {parsed.name!r} not found")
    stmt = select(PromptVersion).where(PromptVersion.prompt_id == prompt.id)
    if parsed.version is not None:
        stmt = stmt.where(PromptVersion.version == parsed.version)
    else:
        environment = parsed.environment or prompt.default_environment or "production"
        stmt = stmt.where(PromptVersion.environment == environment)
    version = (
        await db.execute(stmt.order_by(PromptVersion.version.desc()).limit(1))
    ).scalar_one_or_none()
    if version is None:
        where = (
            f"version {parsed.version}"
            if parsed.version is not None
            else f"environment {(parsed.environment or prompt.default_environment)!r}"
        )
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Prompt {parsed.name!r} has no {where}")
    content, missing = render_prompt(version.content, variables)
    return ResolvedPrompt(
        ref=ref,
        name=prompt.name,
        version=version.version,
        environment=version.environment,
        prompt_version_id=version.id,
        content=content,
        missing_variables=tuple(missing),
    )


def apply_resolved_prompt(
    messages: list[dict[str, Any]], resolved: ResolvedPrompt
) -> list[dict[str, Any]]:
    """Prepend the rendered prompt as the system message."""
    return [{"role": "system", "content": resolved.content}, *messages]
