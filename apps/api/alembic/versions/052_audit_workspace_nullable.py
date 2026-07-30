"""052 — make audit_events.workspace_id nullable

Org/tenant-scoped audit events (member add/remove/role/status changes) have no
workspace, but `log_audit` wrote the *tenant* id into the NOT NULL workspace_id FK,
raising a ForeignKeyViolationError and 500ing every org-member removal. Drop the NOT
NULL so org-level events can store NULL.

Revision ID: 052
Revises: 051
Create Date: 2026-07-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "052"
down_revision = "051"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TABLE audit_events ALTER COLUMN workspace_id DROP NOT NULL"))


def downgrade() -> None:
    # Best-effort: only re-add NOT NULL if no NULLs exist (org-level rows would block it).
    op.execute(sa.text("ALTER TABLE audit_events ALTER COLUMN workspace_id SET NOT NULL"))
