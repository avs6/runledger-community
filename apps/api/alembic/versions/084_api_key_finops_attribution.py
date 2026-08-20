"""add api key attribution to runs and provider calls

Revision ID: 084_api_key_finops_attribution
Revises: 083_auto_approval_policies
Create Date: 2026-08-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "084_api_key_finops_attribution"
down_revision = "083_auto_approval_policies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent_runs",
        sa.Column("api_key_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_agent_runs_api_key_id",
        "agent_runs",
        "api_keys",
        ["api_key_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_agent_runs_api_key",
        "agent_runs",
        ["workspace_id", "api_key_id"],
        unique=False,
    )

    op.add_column(
        "provider_calls",
        sa.Column("api_key_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_provider_calls_api_key_id",
        "provider_calls",
        "api_keys",
        ["api_key_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_provider_calls_api_key",
        "provider_calls",
        ["workspace_id", "api_key_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_provider_calls_api_key", table_name="provider_calls")
    op.drop_constraint("fk_provider_calls_api_key_id", "provider_calls", type_="foreignkey")
    op.drop_column("provider_calls", "api_key_id")

    op.drop_index("ix_agent_runs_api_key", table_name="agent_runs")
    op.drop_constraint("fk_agent_runs_api_key_id", "agent_runs", type_="foreignkey")
    op.drop_column("agent_runs", "api_key_id")
