"""Restore billing tables the Community Edition extraction left without a migration.

``billing_adjustments``, ``cost_centers`` and ``shared_cost_policies`` back live
billing endpoints (period adjustments, shared-cost policies, cost-center allocation),
but the migration that created them was removed with the enterprise code, so every
request to those endpoints failed with "relation does not exist". ``IF NOT EXISTS``
keeps this safe for installs created before the extraction, which still have them.

Revision ID: 093_restore_billing_tables
Revises: 092_otlp_metric_rollups
"""

from alembic import op

revision = "093_restore_billing_tables"
down_revision = "092_otlp_metric_rollups"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cost_centers (
            id UUID PRIMARY KEY,
            workspace_id UUID NOT NULL,
            name TEXT NOT NULL,
            code VARCHAR(64),
            parent_id UUID REFERENCES cost_centers (id) ON DELETE SET NULL,
            description TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_cost_centers_workspace ON cost_centers (workspace_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_cost_centers_parent"
        " ON cost_centers (workspace_id, parent_id)"
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS billing_adjustments (
            id UUID PRIMARY KEY,
            workspace_id UUID NOT NULL,
            billing_period_id UUID NOT NULL
                REFERENCES billing_periods (id) ON DELETE CASCADE,
            adjustment_type VARCHAR(32) NOT NULL,
            amount_usd NUMERIC(14, 6) NOT NULL,
            description TEXT,
            reference_id TEXT,
            created_by TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_billing_adjustments_period"
        " ON billing_adjustments (billing_period_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_billing_adjustments_workspace"
        " ON billing_adjustments (workspace_id)"
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS shared_cost_policies (
            id UUID PRIMARY KEY,
            workspace_id UUID NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            formula_type VARCHAR(32) NOT NULL,
            allocations JSONB NOT NULL DEFAULT '[]'::jsonb,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_shared_cost_policies_workspace"
        " ON shared_cost_policies (workspace_id, is_active)"
    )


def downgrade() -> None:
    # Intentionally a no-op: on installs that predate the extraction these tables
    # existed before this revision, so dropping them here could destroy data.
    pass
