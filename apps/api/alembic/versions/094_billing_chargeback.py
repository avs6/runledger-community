"""Billing & chargeback: applicable chargeback rules, persisted shared-cost
allocations, per-workspace billing signing keys, period close/reopen tracking.

- chargeback_rules: dimension_value (the value a rule maps, e.g. a workflow tag),
  approval_id, created_by, updated_at. Rules that can't be applied (no value or no
  cost center) are set inactive; legacy allocation types collapse to shared_weight.
- cost_allocations: shared-cost pools applied to a period, one row per cost center.
- workspaces.billing_signing_version: key version for snapshot/export signatures.
- billing_periods: closed_by, reopened_at, reopen_reason.
- budget_notifications.signing_version: per-destination webhook signing secret.

Revision ID: 094_billing_chargeback
Revises: 093_restore_billing_tables
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision = "094_billing_chargeback"
down_revision = "093_restore_billing_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("chargeback_rules", sa.Column("dimension_value", sa.Text, nullable=True))
    op.add_column("chargeback_rules", sa.Column("approval_id", PGUUID(as_uuid=True), nullable=True))
    op.add_column("chargeback_rules", sa.Column("created_by", sa.Text, nullable=True))
    op.add_column(
        "chargeback_rules",
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.execute(
        "UPDATE chargeback_rules SET allocation_type = 'shared_weight' "
        "WHERE allocation_type NOT IN ('direct', 'shared_weight')"
    )
    op.execute(
        "UPDATE chargeback_rules SET status = 'inactive' "
        "WHERE status = 'active' AND (dimension_value IS NULL OR cost_center_id IS NULL)"
    )
    op.create_index(
        "ix_chargeback_rules_lookup",
        "chargeback_rules",
        ["workspace_id", "dimension", "dimension_value", "status"],
    )

    op.create_table(
        "cost_allocations",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column(
            "policy_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("shared_cost_policies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "cost_center_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("cost_centers.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("label", sa.Text, nullable=False),
        sa.Column("pool_usd", sa.Numeric(14, 6), nullable=False),
        sa.Column("amount_usd", sa.Numeric(14, 6), nullable=False),
        sa.Column("created_by", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index("ix_cost_allocations_period", "cost_allocations", ["workspace_id", "period"])

    op.add_column(
        "workspaces",
        sa.Column("billing_signing_version", sa.Integer, nullable=False, server_default="1"),
    )

    # Budget webhook destinations sign with their own secret (review F-03).
    op.add_column(
        "budget_notifications",
        sa.Column("signing_version", sa.Integer, nullable=False, server_default="1"),
    )

    op.add_column("billing_periods", sa.Column("closed_by", sa.Text, nullable=True))
    op.add_column(
        "billing_periods", sa.Column("reopened_at", sa.TIMESTAMP(timezone=True), nullable=True)
    )
    op.add_column("billing_periods", sa.Column("reopen_reason", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("budget_notifications", "signing_version")
    op.drop_column("billing_periods", "reopen_reason")
    op.drop_column("billing_periods", "reopened_at")
    op.drop_column("billing_periods", "closed_by")
    op.drop_column("workspaces", "billing_signing_version")
    op.drop_index("ix_cost_allocations_period", table_name="cost_allocations")
    op.drop_table("cost_allocations")
    op.drop_index("ix_chargeback_rules_lookup", table_name="chargeback_rules")
    op.drop_column("chargeback_rules", "updated_at")
    op.drop_column("chargeback_rules", "created_by")
    op.drop_column("chargeback_rules", "approval_id")
    op.drop_column("chargeback_rules", "dimension_value")
