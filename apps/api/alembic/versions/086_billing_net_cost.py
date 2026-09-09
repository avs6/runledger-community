"""Add net_cost_usd, currency, exchange_rate_to_usd to billing_periods.

Revision ID: 086_billing_net_cost
Revises: 085_workflow_run_identity
"""

import sqlalchemy as sa
from alembic import op

revision = "086_billing_net_cost"
down_revision = "085_workflow_run_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "billing_periods",
        sa.Column("net_cost_usd", sa.Numeric(14, 6), nullable=True),
    )
    op.add_column(
        "billing_periods",
        sa.Column("currency", sa.String(3), nullable=False, server_default=sa.text("'USD'")),
    )
    op.add_column(
        "billing_periods",
        sa.Column("exchange_rate_to_usd", sa.Numeric(12, 6), nullable=False, server_default=sa.text("1.0")),
    )


def downgrade() -> None:
    op.drop_column("billing_periods", "exchange_rate_to_usd")
    op.drop_column("billing_periods", "currency")
    op.drop_column("billing_periods", "net_cost_usd")
