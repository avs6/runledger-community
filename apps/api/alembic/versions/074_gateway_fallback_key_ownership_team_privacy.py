"""074 - gateway fallback, key ownership, team privacy

Revision ID: 074_gateway_fallback_key_ownership_team_privacy
Revises: 073_backup_runs_and_kafka_single_topic
Create Date: 2026-08-06
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "074_gateway_fallback_key_ownership_team_privacy"
down_revision = "073_backup_runs_and_kafka_single_topic"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "gateway_routes",
        sa.Column("fallback_config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "api_keys",
        sa.Column("ownership_type", sa.String(length=32), server_default=sa.text("'user'"), nullable=False),
    )
    op.add_column(
        "api_keys",
        sa.Column("owner_reference", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "team_models",
        sa.Column("logging_opt_out", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("team_models", "logging_opt_out")
    op.drop_column("api_keys", "owner_reference")
    op.drop_column("api_keys", "ownership_type")
    op.drop_column("gateway_routes", "fallback_config")
