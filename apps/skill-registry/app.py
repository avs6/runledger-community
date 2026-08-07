"""
Skill Registry service (Phase 5).

Stores reusable procedural knowledge (Anthropic Skills format: name + description + content),
versioned and scoped per workspace. File-backed (one JSON per skill) — no extra database.
MCP clients and the Context Compiler can list skills and fetch the ones relevant to a task.

Endpoints
---------
GET    /health
POST   /skills                 { workspace, name, description, content, version? }   (upsert)
GET    /skills?workspace=       → [{ name, description, version }]
GET    /skills/{name}?workspace= → full skill
DELETE /skills/{name}?workspace=
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

DATA_DIR = Path(os.getenv("SKILLS_DATA_DIR", "/data/skills"))

app = FastAPI(title="RunLedger Skill Registry", version="0.1.0")


def _safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)[:128]


def _dir(workspace: str) -> Path:
    d = DATA_DIR / _safe(workspace)
    d.mkdir(parents=True, exist_ok=True)
    return d


class Skill(BaseModel):
    workspace: str
    name: str
    description: str = ""
    content: str = ""
    version: int = 1
    metadata: dict = Field(default_factory=dict)


@app.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "dir": str(DATA_DIR)}


@app.get("/health/ready")
def readiness() -> dict[str, object]:
    return health()


@app.post("/skills")
def upsert(skill: Skill) -> dict[str, object]:
    path = _dir(skill.workspace) / f"{_safe(skill.name)}.json"
    body = skill.model_dump()
    body["updated_at"] = int(time.time())
    path.write_text(json.dumps(body), encoding="utf-8")
    return {"stored": True, "name": skill.name, "version": skill.version}


@app.get("/skills")
def list_skills(workspace: str) -> dict[str, object]:
    items = []
    for f in sorted(_dir(workspace).glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            items.append({"name": d["name"], "description": d.get("description", ""), "version": d.get("version", 1)})
        except Exception:  # noqa: BLE001
            continue
    return {"skills": items}


@app.get("/skills/{name}")
def get_skill(name: str, workspace: str) -> dict:
    path = _dir(workspace) / f"{_safe(name)}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="skill not found")
    return json.loads(path.read_text(encoding="utf-8"))


@app.delete("/skills/{name}", status_code=204)
def delete_skill(name: str, workspace: str) -> None:
    path = _dir(workspace) / f"{_safe(name)}.json"
    if path.exists():
        path.unlink()
