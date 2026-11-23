"""Audit helpers for gateway administration (review G-10).

Every gateway, routing-policy, tier, cache, pricing, guardrail and flywheel mutation
writes one audit event with a before/after snapshot. Call ``audit_change`` *before*
``db.commit()`` so the event lands in the same transaction as the change.

Snapshots never carry secret values: credential maps are reduced to their key names.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.services.audit import emit_audit_event

# Fields whose values are secrets: only the key names are recorded.
_SECRET_FIELDS = frozenset({"credentials", "auth_config", "secret", "api_key", "token"})


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [_json_safe(v) for v in value]
    return str(value)


def snapshot(obj: Any, fields: list[str] | tuple[str, ...]) -> dict[str, Any]:
    """A JSON-safe dict of ``fields`` from an ORM object, with secrets masked."""
    out: dict[str, Any] = {}
    for name in fields:
        value = getattr(obj, name, None)
        if name in _SECRET_FIELDS:
            out[name] = sorted(value.keys()) if isinstance(value, dict) else bool(value)
        else:
            out[name] = _json_safe(value)
    return out


def changed_only(before: dict[str, Any], after: dict[str, Any]) -> tuple[dict, dict]:
    """Trim two snapshots down to the keys whose values differ."""
    keys = [k for k in after if before.get(k) != after.get(k)]
    return {k: before.get(k) for k in keys}, {k: after.get(k) for k in keys}


def actor_of(auth: Any) -> uuid.UUID | None:
    """The acting user's id from an auth tuple ``(workspace, user, ...)``, if any."""
    if isinstance(auth, tuple) and len(auth) > 1:
        user_id = getattr(auth[1], "id", None)
        if isinstance(user_id, uuid.UUID):
            return user_id
        if user_id is not None:
            try:
                return uuid.UUID(str(user_id))
            except ValueError:
                return None
    return None


async def audit_change(
    db: AsyncSession,
    workspace_id: uuid.UUID | str,
    action: str,
    *,
    auth: Any = None,
    target_type: str,
    target_id: Any,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> None:
    """Record one gateway-admin mutation. Never raises (see ``emit_audit_event``)."""
    await emit_audit_event(
        db,
        workspace_id,
        action,
        actor_user_id=actor_of(auth),
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        before=_json_safe(before) if before is not None else None,
        after=_json_safe(after) if after is not None else None,
    )
