"""Secret inventory (review ENH: secret age, rotation and per-secret audit timeline).

One row per stored credential. Rows are written by the session hook in
``services/secrets_inventory.py`` whenever a registered secret column changes, so
the inventory can never drift from the data. The secret value itself is never
stored here, only a keyed fingerprint and the id of the key that encrypted it.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from runledger_api.core.db import Base


class SecretRecord(Base):
    __tablename__ = "secret_records"
    __table_args__ = (
        sa.Index("ix_secret_records_workspace_kind", "workspace_id", "kind"),
        sa.UniqueConstraint("owner_table", "owner_id", "field", name="uq_secret_records_owner"),
    )

    # Deterministic: uuid5(owner_table:owner_id:field), so audit events can point
    # at a secret before the row exists.
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True
    )
    kind: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    owner_table: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    field: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    label: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    key_id: Mapped[str | None] = mapped_column(sa.String(16), nullable=True)
    fingerprint: Mapped[str | None] = mapped_column(sa.String(32), nullable=True)
    rotation_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    rotated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    rotated_by_label: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    rotated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
