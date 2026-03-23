"""
Audit event emission service.

Call ``emit_audit_event()`` from any router after a sensitive mutation.
The call is fire-and-forget (non-blocking) — audit failures never block
the primary request path.

Action naming convention: ``<resource>.<verb>``
  api_key.created         api_key.revoked
  budget.created          budget.updated          budget.deleted
  billing_period.closed
  prompt.promoted
  invoice.imported        invoice.reconciled
  approval.approved       approval.denied         approval.cancelled
  gateway_policy.created  gateway_policy.updated  gateway_policy.deleted
  capture_policy.created  capture_policy.updated
  workspace_member.role_changed
  workspace.created       workspace.deleted
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.audit import AuditEvent

log = structlog.get_logger()


async def emit_audit_event(
    db: AsyncSession,
    workspace_id: uuid.UUID | str,
    action: str,
    *,
    actor_user_id: uuid.UUID | str | None = None,
    actor_api_key: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    client_ip: str | None = None,
) -> None:
    """
    Write one audit record.  Never raises — errors are logged and swallowed
    so audit failures cannot break the primary request.
    """
    try:
        event = AuditEvent(
            workspace_id=uuid.UUID(str(workspace_id)),
            action=action,
            actor_user_id=uuid.UUID(str(actor_user_id)) if actor_user_id else None,
            actor_api_key_prefix=actor_api_key[:8] if actor_api_key else None,
            target_type=target_type,
            target_id=str(target_id) if target_id else None,
            before=before,
            after=after,
            ip_hash=_hash_ip(client_ip),
        )
        db.add(event)
        await db.flush()
    except Exception:
        log.exception("audit_emit_failed", action=action, workspace_id=str(workspace_id))


def _hash_ip(ip: str | None) -> str | None:
    """SHA-256 of the client IP — preserves audit trail without storing raw PII."""
    if not ip:
        return None
    return hashlib.sha256(ip.encode()).hexdigest()
