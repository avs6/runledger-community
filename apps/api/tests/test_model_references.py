"""Static guards against two classes of bug that type checks don't catch.

1. ``Model.attribute`` references to columns that don't exist. SQLAlchemy builds the
   query at request time, so a stale name (``ProviderCall.cost`` for ``cost_usd``,
   ``AlertFiring.created_at`` for ``fired_at``) only fails as a 500 when that endpoint
   is called. 45 dashboard endpoints were broken this way.
2. ORM tables that no Alembic migration creates. The model imports fine, but every
   request fails with "relation does not exist" (three billing tables were lost when a
   migration was removed).

Both scans are text-based and run without a database.
"""

from __future__ import annotations

import re
from pathlib import Path

import runledger_api.models  # noqa: F401 - registers every mapper
from runledger_api.core.db import Base

API_ROOT = Path(__file__).resolve().parents[1]
CODE = API_ROOT / "runledger_api"
MIGRATIONS = API_ROOT / "alembic" / "versions"

_REF = re.compile(r"\b([A-Z][A-Za-z0-9]+)\.([a-z_][a-z0-9_]*)\b")


def _mapped_classes() -> dict[str, type]:
    return {m.class_.__name__: m.class_ for m in Base.registry.mappers}


def test_no_references_to_missing_model_attributes() -> None:
    mapped = _mapped_classes()
    missing: list[str] = []
    for path in sorted(CODE.rglob("*.py")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            for cls_name, attr in _REF.findall(line):
                cls = mapped.get(cls_name)
                if cls is not None and not hasattr(cls, attr):
                    rel = path.relative_to(API_ROOT).as_posix()
                    missing.append(f"{rel}:{lineno} {cls_name}.{attr}")
    assert not missing, "References to model attributes that don't exist:\n" + "\n".join(missing)


def test_every_model_table_is_created_by_a_migration() -> None:
    migrations = "\n".join(p.read_text(encoding="utf-8") for p in MIGRATIONS.glob("*.py"))
    uncreated = [
        name
        for name in sorted(Base.metadata.tables)
        if not re.search(
            rf"""(create_table\(\s*["']{name}["']|CREATE TABLE (IF NOT EXISTS )?{name}\b)""",
            migrations,
        )
    ]
    assert not uncreated, "ORM tables with no creating migration: " + ", ".join(uncreated)
