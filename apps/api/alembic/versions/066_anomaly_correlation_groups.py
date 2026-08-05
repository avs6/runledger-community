"""Add correlation_group_id to ml_anomalies for co-occurring anomaly grouping.

Revision ID: 066
Revises: 065
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "066"
down_revision = "065"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ml_anomalies",
        sa.Column("correlation_group_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_ml_anomalies_correlation_group",
        "ml_anomalies",
        ["correlation_group_id"],
        postgresql_where=sa.text("correlation_group_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_ml_anomalies_correlation_group", table_name="ml_anomalies")
    op.drop_column("ml_anomalies", "correlation_group_id")
