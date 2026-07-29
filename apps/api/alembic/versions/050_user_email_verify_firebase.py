"""050 — users: email_verified, email_verify_token, firebase_uid

These columns are on the User model (email verification + Firebase social login) but no
prior migration created them — so a from-scratch database was missing them and the startup
seed failed on `SELECT users.email_verified`. Idempotent (IF NOT EXISTS) so it's safe on
databases where the columns already exist.

Revision ID: 050
Revises: 049
Create Date: 2026-07-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "050"
down_revision = "049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
            "email_verified BOOLEAN NOT NULL DEFAULT false"
        )
    )
    op.execute(
        sa.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verify_token VARCHAR(64) NULL")
    )
    op.execute(sa.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS firebase_uid VARCHAR(128) NULL"))
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_users_email_verify_token ON users (email_verify_token)"
        )
    )
    op.execute(
        sa.text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_firebase_uid ON users (firebase_uid)")
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS ix_users_firebase_uid"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_users_email_verify_token"))
    op.execute(sa.text("ALTER TABLE users DROP COLUMN IF EXISTS firebase_uid"))
    op.execute(sa.text("ALTER TABLE users DROP COLUMN IF EXISTS email_verify_token"))
    op.execute(sa.text("ALTER TABLE users DROP COLUMN IF EXISTS email_verified"))
