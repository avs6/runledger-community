"""Secret inventory: which credentials exist, how old they are, which key wraps them.

The registry below lists every column that holds a secret. A ``before_flush``
hook (installed by ``services/audit.py``) watches those columns: when one is
created, changed or deleted it upserts the matching :class:`SecretRecord` and
writes a ``secret.created`` / ``secret.rotated`` / ``secret.deleted`` audit event
whose ``target_id`` is the record id, so each secret has its own audit timeline.

Rotation is a value change; re-wrap (``rewrap_secret``) re-encrypts the stored
value with the current primary key without changing it (master-key rotation).
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import inspect as sa_inspect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from runledger_api.core import secrets

_NAMESPACE = uuid.UUID("5f0c1d1e-6a0b-4c55-9a5e-2b1f9d3e7a10")


@dataclass(frozen=True)
class SecretField:
    kind: str
    model_path: str  # "module:Class"
    field: str
    is_json: bool = False
    label_attr: str = "name"
    description: str = ""

    def model(self) -> type[Any]:
        module, _, cls = self.model_path.partition(":")
        mod = __import__(module, fromlist=[cls])
        return getattr(mod, cls)  # type: ignore[no-any-return]

    @property
    def table(self) -> str:
        return str(self.model().__tablename__)


REGISTRY: tuple[SecretField, ...] = (
    SecretField(
        "oidc_client_secret",
        "runledger_api.models.security:OIDCProvider",
        "client_secret_encrypted",
        description="OIDC provider client secret",
    ),
    SecretField(
        "oauth2_client_secret",
        "runledger_api.models.security:OAuth2Provider",
        "client_secret_encrypted",
        description="OAuth2 provider client secret",
    ),
    SecretField(
        "ldap_bind_password",
        "runledger_api.models.security:LDAPProvider",
        "bind_password_encrypted",
        description="LDAP bind password",
    ),
    SecretField(
        "search_provider_auth",
        "runledger_api.models.search_tools:SearchTool",
        "auth_config",
        is_json=True,
        description="Search provider credentials",
    ),
    SecretField(
        "passthrough_auth",
        "runledger_api.models.gateway:GatewayPassThroughEndpoint",
        "auth_config",
        is_json=True,
        label_attr="slug",
        description="Pass-through endpoint credentials",
    ),
    SecretField(
        "passthrough_headers",
        "runledger_api.models.gateway:GatewayPassThroughEndpoint",
        "header_config",
        is_json=True,
        label_attr="slug",
        description="Pass-through secret headers",
    ),
    SecretField(
        "notification_webhook",
        "runledger_api.models.budgets:BudgetNotification",
        "destination_url",
        label_attr="channel",
        description="Notification webhook URL",
    ),
    SecretField(
        "evaluator_api_key",
        "runledger_api.models.evaluators:Evaluator",
        "config",
        is_json=True,
        description="Evaluator provider key",
    ),
)

KINDS = {f.kind: f for f in REGISTRY}


def secret_id(table: str, owner_id: Any, field: str) -> uuid.UUID:
    return uuid.uuid5(_NAMESPACE, f"{table}:{owner_id}:{field}")


def _secret_material(entry: SecretField, value: Any) -> str | None:
    """The part of a column value that is secret (``None`` when nothing is set)."""
    if entry.is_json:
        if not isinstance(value, dict):
            return None
        subset = {k: v for k, v in value.items() if secrets.is_secret_key(k) and v}
        return json.dumps(subset, sort_keys=True) if subset else None
    return str(value) if value else None


def _label(entry: SecretField, obj: Any) -> str:
    label = getattr(obj, entry.label_attr, None) or getattr(obj, "name", None)
    return f"{entry.description}: {label}" if label else entry.description


def _record_event(
    session: Session,
    *,
    action: str,
    record_id: uuid.UUID,
    workspace_id: Any,
    after: dict[str, Any],
) -> None:
    from runledger_api.models.audit import AuditEvent  # noqa: PLC0415

    session.add(
        AuditEvent(
            workspace_id=workspace_id,
            action=action,
            target_type="secret",
            target_id=str(record_id),
            after=after,
        )
    )


def track_secret_changes(session: Session) -> None:
    """``before_flush`` hook: keep SecretRecord rows and secret.* audit events current."""
    from runledger_api.models.secrets import SecretRecord  # noqa: PLC0415
    from runledger_api.services.audit import current_actor  # noqa: PLC0415

    by_model: dict[type[Any], list[SecretField]] = {}
    for entry in REGISTRY:
        by_model.setdefault(entry.model(), []).append(entry)
    watched = tuple(by_model)
    actor = current_actor()
    now = datetime.now(UTC)

    for obj in list(session.new) + list(session.dirty):
        if not isinstance(obj, watched):
            continue
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        state = sa_inspect(obj)
        for entry in by_model[type(obj)]:
            hist = state.attrs[entry.field].history
            if obj not in session.new and not hist.has_changes():
                continue
            material = _secret_material(entry, getattr(obj, entry.field))
            rid = secret_id(entry.table, obj.id, entry.field)
            with session.no_autoflush:
                record = session.get(SecretRecord, rid)
            if material is None:
                if record is not None:
                    session.delete(record)
                    _record_event(
                        session,
                        action="secret.deleted",
                        record_id=rid,
                        workspace_id=record.workspace_id,
                        after={"kind": entry.kind, "label": record.label, "reason": "cleared"},
                    )
                continue
            fp = secrets.fingerprint(material)
            if record is not None and record.fingerprint == fp:
                continue  # same value written back (e.g. a masked field kept)
            if record is None:
                record = SecretRecord(
                    id=rid,
                    workspace_id=getattr(obj, "workspace_id", None),
                    kind=entry.kind,
                    owner_table=entry.table,
                    owner_id=obj.id,
                    field=entry.field,
                    created_at=now,
                    rotation_count=0,
                )
                session.add(record)
                action = "secret.created"
            else:
                record.rotation_count = int(record.rotation_count or 0) + 1
                action = "secret.rotated"
            record.label = _label(entry, obj)
            record.fingerprint = fp
            record.key_id = secrets.primary_key_id()
            record.rotated_at = now
            record.rotated_by_user_id = actor.user_id
            record.rotated_by_label = actor.label or actor.kind
            _record_event(
                session,
                action=action,
                record_id=rid,
                workspace_id=record.workspace_id,
                after={
                    "kind": entry.kind,
                    "label": record.label,
                    "key_id": record.key_id,
                    "fingerprint": fp,
                },
            )

    for obj in list(session.deleted):
        if not isinstance(obj, watched) or getattr(obj, "id", None) is None:
            continue
        for entry in by_model[type(obj)]:
            rid = secret_id(entry.table, obj.id, entry.field)
            with session.no_autoflush:
                record = session.get(SecretRecord, rid)
            if record is None:
                continue
            session.delete(record)
            _record_event(
                session,
                action="secret.deleted",
                record_id=rid,
                workspace_id=record.workspace_id,
                after={"kind": entry.kind, "label": record.label, "reason": "owner deleted"},
            )


# ── Queries and actions used by routers/security.py ───────────────────────────


async def list_records(db: AsyncSession, workspace_id: uuid.UUID) -> list[Any]:
    from runledger_api.models.secrets import SecretRecord  # noqa: PLC0415

    rows = await db.execute(
        select(SecretRecord)
        .where(SecretRecord.workspace_id == workspace_id)
        .order_by(SecretRecord.rotated_at.asc())
    )
    return list(rows.scalars().all())


async def get_record(db: AsyncSession, workspace_id: uuid.UUID, record_id: uuid.UUID) -> Any:
    from runledger_api.models.secrets import SecretRecord  # noqa: PLC0415

    row = await db.execute(
        select(SecretRecord).where(
            SecretRecord.id == record_id, SecretRecord.workspace_id == workspace_id
        )
    )
    return row.scalar_one_or_none()


async def _owner(db: AsyncSession, record: Any) -> tuple[SecretField, Any]:
    entry = KINDS[record.kind]
    owner = await db.get(entry.model(), record.owner_id)
    return entry, owner


async def rotate_secret(
    db: AsyncSession, record: Any, *, value: str | None, values: dict[str, str] | None
) -> None:
    """Replace the secret value. JSON secrets take ``values`` (key -> new value)."""
    entry, owner = await _owner(db, record)
    if owner is None:
        raise LookupError("the object that owns this secret no longer exists")
    if entry.is_json:
        current = dict(getattr(owner, entry.field) or {})
        updates = dict(values or {})
        if value is not None and not updates:
            keys = [k for k in current if secrets.is_secret_key(k)]
            if len(keys) != 1:
                raise ValueError("this secret has several fields; send 'values' by key")
            updates = {keys[0]: value}
        if not updates:
            raise ValueError("a new secret value is required")
        for k, v in updates.items():
            if not secrets.is_secret_key(k):
                raise ValueError(f"'{k}' is not a secret field")
            if not v or secrets.is_mask(v):
                raise ValueError("a new secret value is required")
            current[k] = v
        setattr(owner, entry.field, current)
    else:
        if not value or secrets.is_mask(value):
            raise ValueError("a new secret value is required")
        setattr(owner, entry.field, value)


async def rewrap_secret(db: AsyncSession, record: Any) -> bool:
    """Re-encrypt one secret with the current primary key. Returns True if it changed.

    The value is unchanged, so the fingerprint is the same and the session hook
    does not count a rotation; the record's key id is updated here.
    """
    entry, owner = await _owner(db, record)
    if owner is None:
        return False
    primary = secrets.primary_key_id()
    if record.key_id == primary:
        return False
    # Force a rewrite: the column type re-encrypts with the primary key on bind.
    from sqlalchemy.orm.attributes import flag_modified  # noqa: PLC0415

    flag_modified(owner, entry.field)
    record.key_id = primary
    return True


def age_days(record: Any, now: datetime | None = None) -> int:
    now = now or datetime.now(UTC)
    rotated = record.rotated_at
    if rotated.tzinfo is None:
        rotated = rotated.replace(tzinfo=UTC)
    return max(0, (now - rotated).days)
