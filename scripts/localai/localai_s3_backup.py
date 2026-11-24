#!/usr/bin/env python3
"""Back up and restore RunLedger to S3-compatible object storage (local operators).

Thin wrapper around ``runledger_api.services.pg_backup`` so local runs and the
dashboard's backup jobs use the same code: network ``pg_dump`` / ``pg_restore`` with
DATABASE_URL (and MEMORY_DB_URL), never ``docker exec`` (review P-21).

    cd apps/api && DATABASE_URL=postgresql://runledger:...@localhost:5432/runledger \
        uv run python ../../scripts/localai/localai_s3_backup.py backup
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))

from runledger_api.services.pg_backup import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
