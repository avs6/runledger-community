"""053 - add email report schedule fields

Revision ID: 053
Revises: 052
Create Date: 2026-07-30
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "053"
down_revision = "052"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "email_preferences",
        sa.Column("report_hour", sa.Integer(), nullable=False, server_default=sa.text("7")),
    )
    op.add_column(
        "email_preferences",
        sa.Column(
            "report_timezone",
            sa.String(length=64),
            nullable=False,
            server_default=sa.text("'UTC'"),
        ),
    )
    op.add_column(
        "email_preferences",
        sa.Column(
            "report_recipient_mode",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'workspace_admins'"),
        ),
    )
    op.add_column("email_preferences", sa.Column("report_recipients", sa.Text(), nullable=True))
    op.add_column(
        "email_preferences",
        sa.Column("report_last_sent_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("email_preferences", "report_last_sent_at")
    op.drop_column("email_preferences", "report_recipients")
    op.drop_column("email_preferences", "report_recipient_mode")
    op.drop_column("email_preferences", "report_timezone")
    op.drop_column("email_preferences", "report_hour")
