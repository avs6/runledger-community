"""ORM models for provider invoice reconciliation."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from runledger_api.core.db import Base


class ProviderInvoice(Base):
    """An uploaded provider usage invoice (OpenAI, Anthropic, Google, etc.)."""

    __tablename__ = "provider_invoices"
    __table_args__ = (
        sa.Index("ix_provider_invoices_workspace", "workspace_id"),
        sa.Index("ix_provider_invoices_workspace_period", "workspace_id", "period_start"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    provider: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    period_start: Mapped[date] = mapped_column(sa.Date, nullable=False)
    period_end: Mapped[date] = mapped_column(sa.Date, nullable=False)
    currency: Mapped[str] = mapped_column(sa.String(8), nullable=False, server_default="USD")
    total_amount: Mapped[Decimal] = mapped_column(sa.Numeric(14, 4), nullable=False)
    line_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("0"))
    matched_count: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default=sa.text("0")
    )
    unmatched_amount: Mapped[Decimal | None] = mapped_column(sa.Numeric(14, 6), nullable=True)
    status: Mapped[str] = mapped_column(sa.String(16), nullable=False, server_default="imported")
    filename: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class ProviderInvoiceLine(Base):
    """A single line item from a provider invoice."""

    __tablename__ = "provider_invoice_lines"
    __table_args__ = (
        sa.Index("ix_invoice_lines_invoice", "invoice_id"),
        sa.Index("ix_invoice_lines_match_status", "invoice_id", "match_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    provider_request_id: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    model: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True)
    amount: Mapped[Decimal] = mapped_column(sa.Numeric(14, 6), nullable=False)
    occurred_at: Mapped[datetime | None] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=True)
    # Reconciliation fields
    match_status: Mapped[str] = mapped_column(
        sa.String(16), nullable=False, server_default="unmatched"
    )  # unmatched | exact | fuzzy | disputed
    matched_call_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    token_delta: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    cost_delta: Mapped[Decimal | None] = mapped_column(sa.Numeric(14, 6), nullable=True)
    dispute_note: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    raw: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'{}'")
    )
