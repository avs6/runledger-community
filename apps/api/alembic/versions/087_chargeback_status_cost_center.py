"""Add status and cost_center_id columns to chargeback_rules.

Revision ID: 087_chargeback_status_cost_center
Revises: 086_billing_net_cost
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision = "087_chargeback_status"
down_revision = "086_billing_net_cost"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "chargeback_rules",
        sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'active'")),
    )
    op.add_column(
        "chargeback_rules",
        sa.Column("cost_center_id", PGUUID(as_uuid=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("chargeback_rules", "cost_center_id")
    op.drop_column("chargeback_rules", "status")
