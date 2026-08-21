"""add identity columns to workflow_runs for access-group and api-key scope

Revision ID: 085_workflow_run_identity
Revises: 084_api_key_finops_attribution
Create Date: 2026-08-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "085_workflow_run_identity"
down_revision = "084_api_key_finops_attribution"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workflow_runs",
        sa.Column("api_key_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_workflow_runs_api_key_id",
        "workflow_runs",
        "api_keys",
        ["api_key_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "workflow_runs",
        sa.Column("access_group_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_workflow_runs_access_group_id",
        "workflow_runs",
        "access_groups",
        ["access_group_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_workflow_runs_api_key",
        "workflow_runs",
        ["workspace_id", "api_key_id"],
        unique=False,
    )
    op.create_index(
        "ix_workflow_runs_access_group",
        "workflow_runs",
        ["workspace_id", "access_group_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_workflow_runs_access_group", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_api_key", table_name="workflow_runs")
    op.drop_constraint("fk_workflow_runs_access_group_id", "workflow_runs", type_="foreignkey")
    op.drop_column("workflow_runs", "access_group_id")
    op.drop_constraint("fk_workflow_runs_api_key_id", "workflow_runs", type_="foreignkey")
    op.drop_column("workflow_runs", "api_key_id")
