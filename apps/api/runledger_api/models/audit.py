"""AuditEvent ORM model."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from runledger_api.core.db import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (Index("ix_audit_events_chain_seq", "chain_key", "seq", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Nullable: org/tenant-scoped audit events (e.g. member changes) have no workspace.
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True
    )
    # Organization the event belongs to. Set for tenant-scoped events (member and
    # identity changes) and for workspace events, so the org audit view sees both.
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_api_key_prefix: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Who acted (review S-16): user, api_key, session, oidc, admin_secret, service
    # or system. Filled from the request's actor context when the caller omits it.
    actor_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_label: Mapped[str | None] = mapped_column(Text, nullable=True)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    target_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    before: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    ip_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    # Hash chain (review S-16): one chain per workspace (``ws:<id>``), org
    # (``tenant:<id>``) or ``global``. ``hash`` = SHA-256 over the canonical
    # event plus ``prev_hash``; ``GET /audit/verify`` recomputes it.
    chain_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    seq: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    prev_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    hash: Mapped[str | None] = mapped_column(Text, nullable=True)
