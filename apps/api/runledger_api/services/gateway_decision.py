"""
The gateway's "why" record for one request (ENH: X-RunLedger-Decision).

Preflight fills a :class:`DecisionTrace` as it goes — prompt ref, guardrails, cache,
budget, intelligent routing, the candidate routes and any skipped by caps — and
returns it twice:

* ``decision`` (dict): echoed by gateway-rs on finalize and stored on the run as
  ``run_metadata.gateway_decision`` (finalize adds the route that actually served).
  The run-detail "Why this route" panel reads it.
* ``decision_header`` (str): ``cache=…; budget=…; guardrail=…`` — gateway-rs prepends
  ``route=<alias>/<provider>:<model>; trigger=<trigger>`` for the step that served and
  returns it as the ``X-RunLedger-Decision`` response header.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.guardrails import GuardrailEvent

_HEADER_UNSAFE = re.compile(r"[^A-Za-z0-9._:/@+\-]")


def _token(value: Any) -> str:
    """Header-safe token (ASCII, no separators)."""
    return _HEADER_UNSAFE.sub("_", str(value))[:80] or "_"


@dataclass
class DecisionTrace:
    request_id: uuid.UUID
    model_requested: str
    route: dict[str, Any] = field(default_factory=dict)
    cache: dict[str, str] = field(default_factory=dict)
    budget: dict[str, Any] = field(default_factory=dict)
    guardrail: dict[str, Any] = field(default_factory=dict)
    prompt: dict[str, Any] | None = None
    intelligent_routing: dict[str, Any] | None = None
    candidates: list[dict[str, Any]] = field(default_factory=list)
    skipped: list[dict[str, Any]] = field(default_factory=list)

    def cache_summary(self) -> str:
        if self.cache.get("exact") == "hit":
            return "exact"
        if self.cache.get("semantic") == "hit":
            return "semantic"
        if "miss" in self.cache.values():
            return "miss"
        return "off"

    def guardrail_summary(self) -> str:
        pre = self.guardrail.get("pre_call")
        if pre in (None, "off"):
            return "off"
        return "modified" if pre == "modify" else "pass"

    def as_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "version": 1,
            "request_id": str(self.request_id),
            "model_requested": self.model_requested,
            "route": dict(self.route),
            "cache": {"result": self.cache_summary(), **self.cache},
            "budget": dict(self.budget) or {"status": "ok"},
            "guardrail": {"result": self.guardrail_summary(), **self.guardrail},
            "candidates": list(self.candidates),
            "skipped_routes": list(self.skipped),
        }
        if self.prompt:
            data["prompt"] = dict(self.prompt)
        if self.intelligent_routing:
            data["intelligent_routing"] = dict(self.intelligent_routing)
        return data

    def header(self) -> str:
        parts = []
        cache = self.cache_summary()
        if cache in ("exact", "semantic"):
            parts.append("route=cache")
        parts.append(f"cache={cache}")
        parts.append(f"budget={_token((self.budget or {}).get('status', 'ok'))}")
        parts.append(f"guardrail={self.guardrail_summary()}")
        if self.prompt and self.prompt.get("prompt_name"):
            parts.append(
                f"prompt={_token(self.prompt['prompt_name'])}@{_token(self.prompt.get('prompt_version'))}"
            )
        return "; ".join(parts)


async def link_guardrail_events_to_run(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    request_id: uuid.UUID | None,
    run_id: uuid.UUID | None,
) -> None:
    """Point this request's guardrail events at the run finalize recorded (G-19)."""
    if request_id is None or run_id is None:
        return
    await db.execute(
        update(GuardrailEvent)
        .where(
            GuardrailEvent.workspace_id == workspace_id,
            GuardrailEvent.gateway_request_id == request_id,
        )
        .values(run_id=run_id)
    )
    await db.flush()
