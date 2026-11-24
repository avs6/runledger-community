"""
Audit event emission service.

Call ``emit_audit_event()`` from any router **before** committing the mutation
it describes, so the event and the change land in the same transaction (review
S-02). If a caller has already committed, the event is committed on its own
rather than being left in a session nobody commits.

Every event carries an actor (review S-16): when the caller passes none, the
request's actor context (set by authentication in ``core/deps.py``) is used, and
anything outside a request is recorded as ``system``.

Events form a hash chain per workspace (``ws:<id>``), org (``tenant:<id>``) or
``global``: ``hash = sha256(canonical(event) + prev_hash)``, numbered by ``seq``.
A Postgres advisory lock serialises appends to one chain. ``verify_chain()``
recomputes the chain and reports the first broken link (``GET /audit/verify``).

Action naming convention: ``<resource>.<verb>``
  api_key.created         api_key.revoked
  budget.created          budget.updated          budget.deleted
  approval.approved       approval.denied         approval.cancelled
  secret.created          secret.rotated          secret.rewrapped   secret.deleted
  workspace_member.role_changed
"""

from __future__ import annotations

import contextvars
import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import event as sa_event
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from runledger_api.models.audit import AuditEvent

log = structlog.get_logger()

GENESIS_HASH = "0" * 64


# ── Actor context ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Actor:
    kind: str  # user | session | api_key | oidc | admin_secret | service | system
    user_id: uuid.UUID | None = None
    api_key_prefix: str | None = None
    label: str | None = None
    client_ip: str | None = None


SYSTEM_ACTOR = Actor(kind="system", label="system")
_current_actor: contextvars.ContextVar[Actor | None] = contextvars.ContextVar(
    "runledger_audit_actor", default=None
)


def set_actor(actor: Actor | None) -> contextvars.Token[Actor | None]:
    """Record who is acting for the rest of this request/task."""
    return _current_actor.set(actor)


def reset_actor(token: contextvars.Token[Actor | None]) -> None:
    _current_actor.reset(token)


def current_actor() -> Actor:
    return _current_actor.get() or SYSTEM_ACTOR


def actor_from_api_key(api_key: Any, *, user: Any = None, client_ip: str | None = None) -> Actor:
    is_session = bool(getattr(api_key, "is_session", False))
    user_id = getattr(user, "id", None) or getattr(api_key, "user_id", None)
    label = getattr(user, "email", None) or getattr(api_key, "created_by", None)
    if not label:
        label = getattr(api_key, "name", None) or getattr(api_key, "key_prefix", None)
    return Actor(
        kind="session" if is_session else "api_key",
        user_id=user_id if isinstance(user_id, uuid.UUID) else None,
        api_key_prefix=getattr(api_key, "key_prefix", None),
        label=str(label) if label else None,
        client_ip=client_ip,
    )


# ── Emission ──────────────────────────────────────────────────────────────────


async def emit_audit_event(
    db: AsyncSession,
    workspace_id: uuid.UUID | str | None,
    action: str,
    *,
    actor_user_id: uuid.UUID | str | None = None,
    actor_api_key: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    client_ip: str | None = None,
    tenant_id: uuid.UUID | str | None = None,
) -> None:
    """
    Add one audit record to the caller's transaction. Never raises — errors are
    logged and swallowed so audit failures cannot break the primary request.
    """
    try:
        ws_uuid = uuid.UUID(str(workspace_id)) if workspace_id else None
        tenant_uuid = await _resolve_tenant_id(db, ws_uuid, tenant_id)
        actor = current_actor()
        event = AuditEvent(
            workspace_id=ws_uuid,
            tenant_id=tenant_uuid,
            action=action,
            actor_user_id=uuid.UUID(str(actor_user_id)) if actor_user_id else actor.user_id,
            actor_api_key_prefix=actor_api_key[:8] if actor_api_key else actor.api_key_prefix,
            actor_type=actor.kind,
            actor_label=actor.label,
            target_type=target_type,
            target_id=str(target_id) if target_id else None,
            before=_jsonable(before),
            after=_jsonable(after),
            ip_hash=_hash_ip(client_ip or actor.client_ip),
        )
        info = getattr(db, "info", None)
        # The caller committed its change and has started nothing since (no flush,
        # no pending objects): nobody would commit this event, so commit it here.
        orphaned = (
            isinstance(info, dict)
            and bool(info.get("rl_committed"))
            and not (db.new or db.dirty or db.deleted)
        )
        db.add(event)
        await db.flush()
        if orphaned:
            await db.commit()
    except Exception:
        log.exception("audit_emit_failed", action=action, workspace_id=str(workspace_id))


def _jsonable(value: dict[str, Any] | None) -> dict[str, Any] | None:
    if value is None:
        return None
    return json.loads(json.dumps(value, default=str))


async def _resolve_tenant_id(
    db: AsyncSession, workspace_id: uuid.UUID | None, tenant_id: uuid.UUID | str | None
) -> uuid.UUID | None:
    """Best-effort org id for the event (never raises)."""
    try:
        if tenant_id is not None:
            return uuid.UUID(str(tenant_id))
        if workspace_id is None:
            return None
        from runledger_api.models.tenant import Workspace  # noqa: PLC0415

        ws = await db.get(Workspace, workspace_id)
        value = getattr(ws, "tenant_id", None)
        return value if isinstance(value, uuid.UUID) else None
    except Exception:  # noqa: BLE001
        return None


def _hash_ip(ip: str | None) -> str | None:
    """SHA-256 of the client IP — preserves audit trail without storing raw PII."""
    if not ip:
        return None
    return hashlib.sha256(ip.encode()).hexdigest()


# ── Hash chain ────────────────────────────────────────────────────────────────


def chain_key_for(workspace_id: Any, tenant_id: Any) -> str:
    if workspace_id:
        return f"ws:{workspace_id}"
    if tenant_id:
        return f"tenant:{tenant_id}"
    return "global"


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).isoformat()


def canonical_event(event: AuditEvent) -> str:
    """The exact bytes an event's hash covers (stable across DB round trips)."""
    body = {
        "id": str(event.id),
        "seq": event.seq,
        "chain_key": event.chain_key,
        "workspace_id": str(event.workspace_id) if event.workspace_id else None,
        "tenant_id": str(event.tenant_id) if event.tenant_id else None,
        "actor_user_id": str(event.actor_user_id) if event.actor_user_id else None,
        "actor_api_key_prefix": event.actor_api_key_prefix,
        "actor_type": event.actor_type,
        "actor_label": event.actor_label,
        "action": event.action,
        "target_type": event.target_type,
        "target_id": event.target_id,
        "before": event.before,
        "after": event.after,
        "ip_hash": event.ip_hash,
        "created_at": _iso(event.created_at),
    }
    return json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)


def compute_hash(event: AuditEvent, prev_hash: str) -> str:
    return hashlib.sha256((prev_hash + canonical_event(event)).encode()).hexdigest()


def _fill_actor(event: AuditEvent) -> None:
    if event.actor_type:
        return
    actor = current_actor()
    if event.actor_user_id is None and actor.user_id is not None:
        event.actor_user_id = actor.user_id
    if event.actor_api_key_prefix is None and actor.api_key_prefix:
        event.actor_api_key_prefix = actor.api_key_prefix
    event.actor_type = actor.kind
    if event.actor_label is None:
        event.actor_label = actor.label


def _link_new_events(session: Session) -> None:
    """Assign seq/prev_hash/hash to every new AuditEvent in this flush."""
    pending = [obj for obj in session.new if isinstance(obj, AuditEvent) and obj.hash is None]
    if not pending:
        return
    conn = session.connection()
    is_pg = conn.dialect.name == "postgresql"
    by_chain: dict[str, list[AuditEvent]] = {}
    for ev in pending:
        _fill_actor(ev)
        if ev.id is None:
            ev.id = uuid.uuid4()
        if ev.created_at is None:
            ev.created_at = datetime.now(UTC)
        ev.chain_key = chain_key_for(ev.workspace_id, ev.tenant_id)
        by_chain.setdefault(ev.chain_key, []).append(ev)
    for key, events in by_chain.items():
        if is_pg:
            conn.execute(text("SELECT pg_advisory_xact_lock(hashtext(:k))"), {"k": key})
        row = conn.execute(
            select(AuditEvent.seq, AuditEvent.hash)
            .where(AuditEvent.chain_key == key, AuditEvent.seq.is_not(None))
            .order_by(AuditEvent.seq.desc())
            .limit(1)
        ).first()
        seq = int(row[0]) if row else 0
        prev = str(row[1]) if row and row[1] else GENESIS_HASH
        for ev in events:
            seq += 1
            ev.seq = seq
            ev.prev_hash = prev
            ev.hash = compute_hash(ev, prev)
            prev = ev.hash


def _before_flush(session: Session, flush_context: Any, instances: Any) -> None:
    try:
        from runledger_api.services.secrets_inventory import track_secret_changes  # noqa: PLC0415

        track_secret_changes(session)
    except Exception:  # noqa: BLE001
        log.exception("secret_inventory_hook_failed")
    _link_new_events(session)


def _after_commit(session: Session) -> None:
    session.info["rl_committed"] = True


def _after_flush(session: Session, flush_context: Any) -> None:
    # New work was flushed after the last commit; the caller will commit it.
    session.info.pop("rl_committed", None)


_installed = False


def install_session_hooks() -> None:
    """Register the audit chain + secret inventory hooks on every ORM session."""
    global _installed  # noqa: PLW0603
    if _installed:
        return
    sa_event.listen(Session, "before_flush", _before_flush)
    sa_event.listen(Session, "after_commit", _after_commit)
    sa_event.listen(Session, "after_flush", _after_flush)
    _installed = True


install_session_hooks()


# ── Verification ──────────────────────────────────────────────────────────────


@dataclass
class ChainVerification:
    chain_key: str
    checked: int
    ok: bool
    unchained: int = 0
    first_bad_seq: int | None = None
    first_bad_event_id: str | None = None
    reason: str | None = None
    head_hash: str | None = None


async def verify_chain(db: AsyncSession, chain_key: str, *, batch: int = 1000) -> ChainVerification:
    """Walk a chain in seq order and recompute every hash."""
    prev = GENESIS_HASH
    expected_seq = 1
    checked = 0
    last_seq = 0
    while True:
        rows = (
            (
                await db.execute(
                    select(AuditEvent)
                    .where(AuditEvent.chain_key == chain_key, AuditEvent.seq > last_seq)
                    .order_by(AuditEvent.seq)
                    .limit(batch)
                )
            )
            .scalars()
            .all()
        )
        if not rows:
            break
        for ev in rows:
            checked += 1
            if ev.seq != expected_seq:
                return ChainVerification(
                    chain_key,
                    checked,
                    False,
                    first_bad_seq=expected_seq,
                    first_bad_event_id=str(ev.id),
                    reason="missing event (gap in seq)",
                )
            if ev.prev_hash != prev:
                return ChainVerification(
                    chain_key,
                    checked,
                    False,
                    first_bad_seq=ev.seq,
                    first_bad_event_id=str(ev.id),
                    reason="prev_hash does not match",
                )
            if compute_hash(ev, prev) != ev.hash:
                return ChainVerification(
                    chain_key,
                    checked,
                    False,
                    first_bad_seq=ev.seq,
                    first_bad_event_id=str(ev.id),
                    reason="event content was modified",
                )
            prev = ev.hash or prev
            expected_seq += 1
            last_seq = int(ev.seq or 0)
        if len(rows) < batch:
            break
    from sqlalchemy import func  # noqa: PLC0415

    workspace_part = chain_key.split(":", 1)[1] if ":" in chain_key else None
    unchained = 0
    if chain_key.startswith("ws:") and workspace_part:
        unchained = int(
            (
                await db.execute(
                    select(func.count())
                    .select_from(AuditEvent)
                    .where(
                        AuditEvent.workspace_id == uuid.UUID(workspace_part),
                        AuditEvent.hash.is_(None),
                    )
                )
            ).scalar()
            or 0
        )
    return ChainVerification(chain_key, checked, True, unchained=unchained, head_hash=prev)
