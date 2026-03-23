"""Add provider_invoices and provider_invoice_lines tables.

Revision ID: 023
Revises: 022
Create Date: 2026-03-22
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "provider_invoices",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("currency", sa.String(8), nullable=False, server_default="USD"),
        sa.Column("total_amount", sa.Numeric(14, 4), nullable=False),
        sa.Column("line_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("matched_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("unmatched_amount", sa.Numeric(14, 6), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="imported"),
        sa.Column("filename", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("ix_provider_invoices_workspace", "provider_invoices", ["workspace_id"])
    op.create_index(
        "ix_provider_invoices_workspace_period",
        "provider_invoices",
        ["workspace_id", "period_start"],
    )

    op.create_table(
        "provider_invoice_lines",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("invoice_id", UUID(as_uuid=True), nullable=False),
        sa.Column("provider_request_id", sa.Text, nullable=True),
        sa.Column("model", sa.Text, nullable=True),
        sa.Column("input_tokens", sa.BigInteger, nullable=True),
        sa.Column("output_tokens", sa.BigInteger, nullable=True),
        sa.Column("amount", sa.Numeric(14, 6), nullable=False),
        sa.Column("occurred_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("match_status", sa.String(16), nullable=False, server_default="unmatched"),
        sa.Column("matched_call_id", UUID(as_uuid=True), nullable=True),
        sa.Column("token_delta", sa.Integer, nullable=True),
        sa.Column("cost_delta", sa.Numeric(14, 6), nullable=True),
        sa.Column("dispute_note", sa.Text, nullable=True),
        sa.Column("raw", JSONB, nullable=False, server_default="{}"),
    )
    op.create_index("ix_invoice_lines_invoice", "provider_invoice_lines", ["invoice_id"])
    op.create_index(
        "ix_invoice_lines_match_status",
        "provider_invoice_lines",
        ["invoice_id", "match_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_invoice_lines_match_status", table_name="provider_invoice_lines")
    op.drop_index("ix_invoice_lines_invoice", table_name="provider_invoice_lines")
    op.drop_table("provider_invoice_lines")
    op.drop_index("ix_provider_invoices_workspace_period", table_name="provider_invoices")
    op.drop_index("ix_provider_invoices_workspace", table_name="provider_invoices")
    op.drop_table("provider_invoices")
