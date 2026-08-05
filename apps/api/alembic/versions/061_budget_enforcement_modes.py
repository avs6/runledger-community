"""Add throttle and fallback budget enforcement modes.

No DDL changes — action column is varchar, not a Postgres enum.
This migration is a revision marker for the code changes.

Revision ID: 061
Revises: 060
"""

revision = "061"
down_revision = "060"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
