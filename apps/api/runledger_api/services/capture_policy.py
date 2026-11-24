"""Scoped capture policy, resolved at ingest per run (review S-09).

The workspace ``CapturePolicy`` is the default. ``CapturePolicyScope`` overrides
apply to a run by the run's own attributes, most specific first:

    api_key (run.api_key_id) > user (run.end_user_id) > feature_tag > intent > workspace

So "capture FULL payloads for the ``checkout`` feature tag only" or "never capture for
key X" are enforced on every span the pipeline stores. Scope types that can't be
resolved from a run (org, model_route, agent) are refused when saved.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.events import AgentRun
from runledger_api.models.ledger import CapturePolicy, CapturePolicyScope

ENFORCED_SCOPE_TYPES: tuple[str, ...] = ("api_key", "user", "feature_tag", "intent", "workspace")
_PRECEDENCE = ("api_key", "user", "feature_tag", "intent", "workspace")
DEFAULT_MODE = ("METADATA_ONLY", 0.0)


def _rate(value: Any, fallback: float = 0.1) -> float:
    return float(value) if value is not None else fallback


@dataclass
class CaptureResolver:
    default: tuple[str, float] = DEFAULT_MODE
    scopes: dict[tuple[str, str], tuple[str, float]] = field(default_factory=dict)
    _run_cache: dict[str, tuple[str, float]] = field(default_factory=dict)

    def resolve(self, attrs: dict[str, Any]) -> tuple[str, float]:
        """Pure precedence lookup over a run's attributes."""
        keys = {
            "api_key": attrs.get("api_key_id"),
            "user": attrs.get("end_user_id"),
            "feature_tag": attrs.get("feature_tag"),
            "intent": attrs.get("intent"),
            "workspace": attrs.get("workspace_id"),
        }
        for scope_type in _PRECEDENCE:
            value = keys.get(scope_type)
            if value is None or value == "":
                continue
            hit = self.scopes.get((scope_type, str(value)))
            if hit is not None:
                return hit
        return self.default

    async def for_run(self, session: AsyncSession, run_id: str | None) -> tuple[str, float]:
        if not self.scopes or not run_id:
            return self.default
        if run_id in self._run_cache:
            return self._run_cache[run_id]
        try:
            row = (
                await session.execute(
                    select(
                        AgentRun.workspace_id,
                        AgentRun.api_key_id,
                        AgentRun.end_user_id,
                        AgentRun.feature_tag,
                        AgentRun.intent,
                    ).where(AgentRun.id == uuid.UUID(str(run_id)))
                )
            ).one_or_none()
        except Exception:  # noqa: BLE001 - never block ingest on a lookup
            return self.default
        mode = self.default if row is None else self.resolve(dict(row._mapping))
        self._run_cache[run_id] = mode
        return mode


async def load_resolver(session: AsyncSession, workspace_id: str) -> CaptureResolver:
    """Workspace default + scoped overrides. Fails closed to METADATA_ONLY."""
    try:
        ws_uuid = uuid.UUID(workspace_id)
        policy = (
            await session.execute(
                select(CapturePolicy).where(CapturePolicy.workspace_id == ws_uuid)
            )
        ).scalar_one_or_none()
        default = (
            (policy.privacy_mode, _rate(policy.sampled_rate))
            if policy is not None
            else DEFAULT_MODE
        )
        rows = (
            (
                await session.execute(
                    select(CapturePolicyScope).where(CapturePolicyScope.workspace_id == ws_uuid)
                )
            )
            .scalars()
            .all()
        )
        scopes = {
            (r.scope_type, str(r.scope_id)): (r.privacy_mode, _rate(r.sampled_rate))
            for r in rows
            if r.scope_type in ENFORCED_SCOPE_TYPES
        }
        return CaptureResolver(default=default, scopes=scopes)
    except Exception:  # noqa: BLE001
        return CaptureResolver()
