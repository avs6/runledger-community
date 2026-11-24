"""Audit event schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditEventResponse(BaseModel):
    id: uuid.UUID
    # NULL for org-scoped events (membership/identity changes); tenant_id is set.
    workspace_id: uuid.UUID | None = None
    tenant_id: uuid.UUID | None = None
    actor_user_id: uuid.UUID | None
    actor_api_key_prefix: str | None
    # Who acted (S-16): user, session, api_key, oidc, admin_secret, service, system.
    actor_type: str | None = None
    actor_label: str | None = None
    action: str
    target_type: str | None
    target_id: str | None
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    created_at: datetime
    # Hash chain (S-16): position in the workspace chain and the link hashes.
    seq: int | None = None
    prev_hash: str | None = None
    hash: str | None = None

    model_config = {"from_attributes": True}


class AuditEventList(BaseModel):
    items: list[AuditEventResponse]
    total: int
    limit: int
    offset: int


class AuditActor(BaseModel):
    actor_type: str | None
    actor_label: str | None
    actor_user_id: uuid.UUID | None
    actor_api_key_prefix: str | None
    events: int
    last_seen: datetime | None


class AuditActorList(BaseModel):
    items: list[AuditActor]


class AuditChainVerification(BaseModel):
    chain_key: str
    ok: bool
    checked: int
    # Events written before the chain existed (none after the migration backfill).
    unchained: int = 0
    first_bad_seq: int | None = None
    first_bad_event_id: str | None = None
    reason: str | None = None
    head_hash: str | None = None
