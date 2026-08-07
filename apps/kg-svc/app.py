"""
Knowledge Graph service (Phase 5).

An embedded Kùzu graph DB storing entities + relationships, scoped by workspace. Feeds the
cognitive layer: the memory/consolidation flow adds entities and relations, and MCP clients query
the graph for connected facts.

Endpoints
---------
GET  /health
POST /entities   { workspace, id, type?, name?, props? }        (upsert)
POST /relations  { workspace, from_id, to_id, type }
POST /query      { workspace, cypher, params? }                  (raw Cypher, internal)
GET  /neighbors  ?workspace=&entity=&limit=                      (1-hop out-neighbours)
"""

from __future__ import annotations

import json
import os
from typing import Any

import kuzu
from fastapi import FastAPI
from pydantic import BaseModel, Field

DB_PATH = os.getenv("KUZU_DB_PATH", "/data/kg")

app = FastAPI(title="RunLedger Knowledge Graph", version="0.1.0")
_db = kuzu.Database(DB_PATH)
_conn = kuzu.Connection(_db)


def _init_schema() -> None:
    _conn.execute(
        "CREATE NODE TABLE IF NOT EXISTS Entity("
        "id STRING, ws STRING, type STRING, name STRING, props STRING, PRIMARY KEY(id))"
    )
    _conn.execute("CREATE REL TABLE IF NOT EXISTS Rel(FROM Entity TO Entity, ws STRING, type STRING)")


@app.on_event("startup")
def _startup() -> None:
    _init_schema()


def _rows(result: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    while result.has_next():
        out.append(dict(zip(result.get_column_names(), result.get_next(), strict=False)))
    return out


class Entity(BaseModel):
    workspace: str
    id: str
    type: str = ""
    name: str = ""
    props: dict[str, Any] = Field(default_factory=dict)


class Relation(BaseModel):
    workspace: str
    from_id: str
    to_id: str
    type: str


class Query(BaseModel):
    workspace: str
    cypher: str
    params: dict[str, Any] = Field(default_factory=dict)


@app.get("/health")
def health() -> dict[str, object]:
    ok = True
    try:
        _conn.execute("RETURN 1")
    except Exception:
        ok = False
    return {"status": "ok" if ok else "degraded", "db": DB_PATH}


@app.get("/health/ready")
def readiness() -> dict[str, object]:
    return health()


@app.post("/entities")
def upsert_entity(e: Entity) -> dict[str, str]:
    # Scoped id so entities never collide across workspaces.
    eid = f"{e.workspace}:{e.id}"
    _conn.execute(
        "MERGE (n:Entity {id: $id}) SET n.ws=$ws, n.type=$type, n.name=$name, n.props=$props",
        {"id": eid, "ws": e.workspace, "type": e.type, "name": e.name, "props": json.dumps(e.props)},
    )
    return {"id": e.id, "status": "upserted"}


@app.post("/relations")
def add_relation(r: Relation) -> dict[str, str]:
    fid, tid = f"{r.workspace}:{r.from_id}", f"{r.workspace}:{r.to_id}"
    _conn.execute(
        "MATCH (a:Entity {id: $f}), (b:Entity {id: $t}) "
        "CREATE (a)-[:Rel {ws: $ws, type: $type}]->(b)",
        {"f": fid, "t": tid, "ws": r.workspace, "type": r.type},
    )
    return {"status": "created"}


@app.get("/neighbors")
def neighbors(workspace: str, entity: str, limit: int = 25) -> dict[str, Any]:
    eid = f"{workspace}:{entity}"
    result = _conn.execute(
        "MATCH (a:Entity {id: $id})-[r:Rel]->(b:Entity) "
        "RETURN b.name AS name, b.type AS type, r.type AS relation LIMIT $limit",
        {"id": eid, "limit": limit},
    )
    return {"entity": entity, "neighbors": _rows(result)}


@app.post("/query")
def query(q: Query) -> dict[str, Any]:
    result = _conn.execute(q.cypher, q.params)
    return {"rows": _rows(result)}
