"""082 - platform webhook settings

Revision ID: 082
Revises: 081
Create Date: 2026-08-12 15:05:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "082"
down_revision = "081"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "platform_webhook_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("generic_webhook_url", sa.Text(), nullable=True),
        sa.Column("slack_webhook_url", sa.Text(), nullable=True),
        sa.Column("events", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("platform_webhook_settings")
