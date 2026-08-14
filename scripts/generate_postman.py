"""Generate a Postman collection + environment from the RunLedger OpenAPI spec."""

from __future__ import annotations

import json
import sys
import uuid

# ── Load OpenAPI spec ──────────────────────────────────────────────────────────
with open(sys.argv[1] if len(sys.argv) > 1 else "/tmp/openapi.json") as f:
    d = json.load(f)

paths = d["paths"]
schemas = d.get("components", {}).get("schemas", {})

# ── Tag → folder display name + order ─────────────────────────────────────────
TAG_ORDER = [
    ("system", "System / Health"),
    ("auth", "Auth"),
    ("ingest", "Ingest"),
    ("runs", "Runs"),
    ("sessions", "Sessions"),
    ("analytics", "Analytics"),
    ("budgets", "Finance - Budgets"),
    ("billing", "Billing"),
    ("invoices", "Invoices"),
    ("outcomes", "Finance - Outcomes & ROI"),
    ("approvals", "Governance - Approvals"),
    ("gateway", "Model Gateway"),
    ("flywheel", "Optimization Flywheel"),
    ("evaluations", "Evaluations"),
    ("experiments", "Experiments"),
    ("prompts", "Prompts"),
    ("alerts", "Control Plane - Alert Rules"),
    ("ledger", "Ledger"),
    ("tools", "Tools"),
    ("pricing-intelligence", "Pricing Intelligence"),
    ("providers", "Provider Profiles"),
    ("settings", "Settings / API Keys"),
    ("sso", "SSO"),
    ("scim", "SCIM"),
    ("users", "Users"),
    ("organization", "Org Profile / Organizations"),
    ("platform-admin", "Platform Admin"),
    ("saas", "SaaS / Billing"),
    ("audit", "Governance - Audit Log"),
    ("policies", "Policies"),
    ("privacy", "Control Plane - Data Capture"),
    ("retention", "Platform Settings - Data Retention"),
    ("replay", "Replay"),
    ("warehouse", "Warehouse"),
    ("OTLP", "Observability - Telemetry"),
    ("Kafka Export", "Kafka Export"),
    ("admin", "Bootstrap / Admin"),
    ("intelligence", "ML Intelligence"),
    ("integrations", "Control Plane - MCP & Integrations"),
    ("Operations", "Operations"),
    ("agents", "Agent Registry & Memory"),
    ("workflows", "Workflows"),
    ("vector-stores", "Vector Store Management"),
    ("playground", "API Playground"),
]

LEGACY_ADMIN_PREFIXES = (
    "/admin/tenants",
    "/admin/workspaces",
    "/admin/api-keys",
    "/admin/global-pricing",
)


def should_skip_path(path: str) -> bool:
    """Hide legacy admin provisioning routes superseded by platform-admin org APIs."""
    return any(path == prefix or path.startswith(f"{prefix}/") for prefix in LEGACY_ADMIN_PREFIXES)


def make_url(path: str) -> tuple[list[str], list[dict]]:
    parts = path.lstrip("/").split("/")
    raw_parts: list[str] = []
    path_vars: list[dict] = []
    for p in parts:
        if p.startswith("{") and p.endswith("}"):
            varname = p[1:-1]
            raw_parts.append(":" + varname)
            path_vars.append({"key": varname, "value": "{{" + varname + "}}", "description": ""})
        else:
            raw_parts.append(p)
    return raw_parts, path_vars


def resolve_ref(schema: dict, depth: int = 0) -> dict:
    if "$ref" in schema:
        ref = schema["$ref"].split("/")[-1]
        return schemas.get(ref, schema)
    return schema


def build_example(schema: dict, depth: int = 0) -> object:
    if depth > 3:
        return {}
    schema = resolve_ref(schema, depth)
    if "allOf" in schema:
        result: dict = {}
        for s in schema["allOf"]:
            part = build_example(s, depth + 1)
            if isinstance(part, dict):
                result.update(part)
        return result
    t = schema.get("type", "")
    if t == "object" or "properties" in schema:
        props = schema.get("properties", {})
        required = schema.get("required", list(props.keys())[:4])
        return {k: build_example(props[k], depth + 1) for k in required[:8] if k in props}
    if t == "array":
        return [build_example(schema.get("items", {}), depth + 1)]
    if t == "string":
        fmt = schema.get("format", "")
        enum = schema.get("enum", [])
        if enum:
            return enum[0]
        if fmt == "date-time":
            return "2026-01-01T00:00:00Z"
        if fmt == "date":
            return "2026-01-01"
        if fmt == "email":
            return "user@example.com"
        if fmt == "uuid":
            return "{{workspace_id}}"
        return "string"
    if t == "integer":
        return 0
    if t == "number":
        return 0.0
    if t == "boolean":
        return True
    return None


def make_body(op: dict) -> dict | None:
    rb = op.get("requestBody", {})
    if not rb:
        return None
    content = rb.get("content", {})
    if "application/json" in content:
        schema = resolve_ref(content["application/json"].get("schema", {}))
        example = build_example(schema)
        return {
            "mode": "raw",
            "raw": json.dumps(example, indent=2),
            "options": {"raw": {"language": "json"}},
        }
    if "multipart/form-data" in content:
        return {"mode": "formdata", "formdata": [{"key": "file", "type": "file", "src": ""}]}
    return None


# ── Build folders ─────────────────────────────────────────────────────────────
items_list = []

for tag, display_name in TAG_ORDER:
    folder_items = []
    for path, methods in sorted(paths.items()):
        if should_skip_path(path):
            continue
        for method, op in methods.items():
            if method == "parameters":
                continue
            if tag not in op.get("tags", []):
                continue

            raw_parts, path_vars = make_url(path)
            host_var = "{{base_url}}"
            auth_var = "{{api_key}}"
            if path == "/gateway/chat/completions":
                host_var = "{{gateway_base_url}}"
                auth_var = "{{workspace_api_key}}"
            url_obj: dict = {
                "raw": host_var + "/" + "/".join(raw_parts),
                "host": [host_var],
                "path": raw_parts,
            }
            if path_vars:
                url_obj["variable"] = path_vars

            # query params (disabled by default)
            query_params = [
                {
                    "key": param["name"],
                    "value": "",
                    "description": param.get("description", ""),
                    "disabled": True,
                }
                for param in op.get("parameters", [])
                if param.get("in") == "query"
            ]
            if query_params:
                url_obj["query"] = query_params

            req: dict = {
                "method": method.upper(),
                "header": [
                    {"key": "Content-Type", "value": "application/json"},
                    {"key": "Authorization", "value": f"Bearer {auth_var}"},
                ],
                "url": url_obj,
                "description": op.get("description", op.get("summary", "")),
            }
            if path.startswith("/settings/api-keys"):
                req["description"] = (
                    (req.get("description") or "API key management")
                    + "\n\nRBAC: org/platform admins can manage keys across org workspaces; "
                    "workspace admins can manage keys only for their active workspace. Use a dashboard "
                    "session key from POST /auth/login."
                )
            elif path.startswith("/gateway/routes") or path in {
                "/gateway/requests",
                "/gateway/stats",
            }:
                req["description"] = (
                    (req.get("description") or "Gateway management")
                    + "\n\nRBAC: requires an org-admin or platform-admin dashboard session key. "
                    "The data-plane /gateway/chat/completions endpoint still accepts workspace API keys."
                )
            elif path == "/gateway/chat/completions":
                req["description"] = (
                    (req.get("description") or "Gateway chat completions")
                    + "\n\nData plane: served by the Rust gateway runtime at `gateway_base_url`, "
                    "not the control-plane `base_url`. Use `workspace_api_key` for this request."
                )
            elif path.startswith("/org/tenants"):
                req["description"] = (
                    req.get("description") or "Organization lifecycle"
                ) + "\n\nRBAC: platform-admin only. Use this for the Organizations lifecycle hub."
            elif path.startswith("/retention") or path.startswith("/settings/email") or path.startswith("/settings/webhooks/defaults"):
                req["description"] = (
                    req.get("description") or "Platform setting"
                ) + "\n\nRBAC: platform-admin only."
            elif path.startswith("/settings/backups"):
                req["description"] = (
                    req.get("description") or "Organization storage override"
                ) + "\n\nRBAC: org-admin or platform-admin dashboard session key. The Organization Console owns the working control surface for org-scoped storage overrides and backup operations."
            elif path.startswith("/budgets/notifications"):
                req["description"] = (
                    req.get("description") or "Outbound webhook destination"
                ) + "\n\nRBAC: org-admin or platform-admin dashboard session key. Use this surface for org-owned webhook and Slack destinations, delivery history, and smoke tests."
            elif path.startswith("/alerts"):
                req["description"] = (
                    req.get("description") or "Alert rules"
                ) + "\n\nRBAC: org-admin or platform-admin dashboard session key."
            elif path == "/runs/flow":
                req["description"] = (
                    (req.get("description") or "Request-flow records")
                    + "\n\nDashboard use: powers Request Flow, Sankey, optimization opportunity, "
                    "and executive AI Ops views. Use a dashboard session key or workspace API key "
                    "scoped to the workspace."
                )
            elif path.startswith("/integrations/kafka"):
                req["description"] = (
                    (req.get("description") or "Kafka export")
                    + "\n\nRBAC: org-admin or platform-admin dashboard session key. "
                    "Exports RunLedger events to Kafka topics for downstream analytics, SIEM, or warehouse pipelines. "
                    "The working control surface lives in Organization Console -> Destinations."
                )
            elif path.startswith("/integrations/slack"):
                req["description"] = (
                    req.get("description") or "Slack integration"
                ) + "\n\nRBAC: org-admin or platform-admin dashboard session key."
            elif path == "/org/dashboard":
                req["description"] = (
                    req.get("description") or "Org dashboard"
                ) + "\n\nDashboard use: org-level AI Ops and workspace rollup cards."
            elif path.startswith("/v1/traces/"):
                desc = (req.get("description") or "OTLP ingest management").replace(
                    "Settings → OTLP tab",
                    "Observe -> Monitoring -> Telemetry page",
                )
                desc = desc.replace(
                    "Settings â†’ OTLP tab",
                    "Observe -> Monitoring -> Telemetry page",
                )
                req["description"] = (
                    desc + "\n\nRBAC: org-admin or platform-admin dashboard session key."
                )
            body = make_body(op)
            if body:
                req["body"] = body

            summary = op.get("summary") or op.get("operationId") or f"{method.upper()} {path}"
            folder_items.append({"name": summary, "request": req, "response": []})

    if folder_items:
        items_list.append(
            {
                "name": display_name,
                "item": folder_items,
                "description": f"RunLedger {display_name} endpoints",
            }
        )


# ── Optimization-layer extras (not in the API's OpenAPI) ──────────────────────
# The semantic cache and context compiler are standalone microservices; their toggles
# ride on the gateway. These curated requests demonstrate both, and give direct access
# to each microservice for testing.
def _req(name, method, raw_url, desc, body=None, auth=True, auth_token_var="api_key"):
    parts = raw_url.split("/")
    headers = [{"key": "Content-Type", "value": "application/json"}]
    if auth:
        headers.append({"key": "Authorization", "value": f"Bearer {{{{{auth_token_var}}}}}"})
    r = {
        "method": method,
        "header": headers,
        "url": {"raw": raw_url, "host": [parts[0]], "path": parts[1:]},
        "description": desc,
    }
    if body is not None:
        r["body"] = {
            "mode": "raw",
            "raw": json.dumps(body, indent=2),
            "options": {"raw": {"language": "json"}},
        }
    return {"name": name, "request": r, "response": []}


def _add_optimization_extras(items: list[dict]) -> None:
    gw = next((it for it in items if it["name"] == "Model Gateway"), None)
    if gw is not None:
        sys_hr = {"role": "system", "content": "You are a concise HR assistant."}
        gw["item"] += [
            _req(
                "Gateway Chat Completions (Semantic Cache)",
                "POST",
                "{{gateway_base_url}}/gateway/chat/completions",
                "Near-duplicate prompt served from the semantic cache (decision_reason=semantic_cache_hit).",
                {
                    "model": "llama3.2",
                    "messages": [
                        sys_hr,
                        {"role": "user", "content": "how much parental leave do employees get"},
                    ],
                    "semantic_cache": True,
                },
                auth_token_var="workspace_api_key",
            ),
            _req(
                "Gateway Chat Completions (Context Compiler)",
                "POST",
                "{{gateway_base_url}}/gateway/chat/completions",
                "Request shrunk (dedup/tool-output/rerank/compaction) before routing.",
                {
                    "model": "llama3.2",
                    "messages": [
                        sys_hr,
                        {"role": "user", "content": "How much parental leave do employees get?"},
                    ],
                    "context_compiler": True,
                },
                auth_token_var="workspace_api_key",
            ),
            _req(
                "Gateway Chat Completions (Intelligent Routing)",
                "POST",
                "{{gateway_base_url}}/gateway/chat/completions",
                "Classify complexity × risk and route to a model tier (decision_reason shows the tier).",
                {
                    "model": "auto",
                    "messages": [
                        sys_hr,
                        {
                            "role": "user",
                            "content": "Does this contract create regulatory exposure?",
                        },
                    ],
                    "intelligent_routing": True,
                },
                auth_token_var="workspace_api_key",
            ),
            _req(
                "Create Gateway Route (Semantic Cache + Compiler on)",
                "POST",
                "{{base_url}}/gateway/routes",
                "Create a route with the semantic cache and context compiler enabled, incl. compiler config.",
                {
                    "alias": "llama3.2",
                    "provider": "ollama",
                    "target_model": "llama3.2",
                    "base_url": "http://host.docker.internal:11434/v1",
                    "priority": 10,
                    "semantic_cache_enabled": True,
                    "context_compiler_enabled": True,
                    "context_compiler_config": {
                        "model": "llama3.1:8b",
                        "reranker_model": "flashrank",
                        "token_threshold": 2000,
                        "token_budget": 32000,
                    },
                },
            ),
        ]
    scope = {
        "tenant": "{{workspace_id}}",
        "model": "llama3.2",
        "system_prompt_hash": "",
        "knowledge_version": "",
        "security_scope": "",
    }
    items.append(
        {
            "name": "Semantic Cache Service",
            "description": "Direct calls to the semantic-cache microservice ({{semantic_cache_url}}, default :8205). No auth.",
            "item": [
                _req(
                    "Health",
                    "GET",
                    "{{semantic_cache_url}}/health",
                    "Liveness + Qdrant collection status.",
                    None,
                    auth=False,
                ),
                _req(
                    "Lookup",
                    "POST",
                    "{{semantic_cache_url}}/lookup",
                    "Semantic hit within scope (score >= threshold).",
                    {
                        "text": "how much parental leave do employees get",
                        "scope": scope,
                        "threshold": 0.95,
                    },
                    auth=False,
                ),
                _req(
                    "Store",
                    "POST",
                    "{{semantic_cache_url}}/store",
                    "Store a response for future semantic hits.",
                    {
                        "text": "How much parental leave do employees get?",
                        "scope": scope,
                        "response": {
                            "choices": [
                                {"message": {"role": "assistant", "content": "16 weeks paid."}}
                            ],
                            "usage": {"prompt_tokens": 20, "completion_tokens": 12},
                        },
                        "prompt_tokens": 20,
                        "completion_tokens": 12,
                    },
                    auth=False,
                ),
            ],
        }
    )
    items.append(
        {
            "name": "Context Compiler Service",
            "description": "Direct calls to the context-compiler microservice ({{context_compiler_url}}, default :8207). No auth.",
            "item": [
                _req(
                    "Health",
                    "GET",
                    "{{context_compiler_url}}/health",
                    "Liveness + downstream URLs.",
                    None,
                    auth=False,
                ),
                _req(
                    "Select tools",
                    "POST",
                    "{{context_compiler_url}}/select-tools",
                    "Return the subset of tool definitions relevant to a query (dynamic tool filtering).",
                    {
                        "query": "Check my Salesforce opportunity",
                        "tools": [
                            {
                                "type": "function",
                                "function": {
                                    "name": "salesforce_search",
                                    "description": "Search Salesforce",
                                },
                            },
                            {
                                "type": "function",
                                "function": {
                                    "name": "k8s_scale",
                                    "description": "Scale a Kubernetes deployment",
                                },
                            },
                        ],
                    },
                    auth=False,
                ),
                _req(
                    "Compile",
                    "POST",
                    "{{context_compiler_url}}/compile",
                    "Shrink a messages array; returns { messages, token_report, dropped }.",
                    {
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a concise HR assistant. Parental leave is 16 weeks paid.",
                            },
                            {
                                "role": "system",
                                "content": "You are a concise HR assistant. Parental leave is 16 weeks paid.",
                            },
                            {
                                "role": "user",
                                "content": "How much parental leave do employees get?",
                            },
                        ],
                        "config": {
                            "reranker_model": "flashrank",
                            "token_threshold": 0,
                            "token_budget": 400,
                            "stages": {
                                "dedup": True,
                                "tool_output": True,
                                "rerank": True,
                                "compaction": True,
                                "compress": False,
                            },
                        },
                    },
                    auth=False,
                ),
            ],
        }
    )
    items.append(
        {
            "name": "Router Service",
            "description": "Direct calls to the intelligent-router microservice ({{router_url}}, default :8210). No auth.",
            "item": [
                _req(
                    "Health",
                    "GET",
                    "{{router_url}}/health",
                    "Liveness + classifier modes.",
                    None,
                    auth=False,
                ),
                _req(
                    "Classify",
                    "POST",
                    "{{router_url}}/classify",
                    "Classify complexity × risk → tier; returns { complexity, risk, reasoning_effort, tier, alias }.",
                    {
                        "messages": [
                            {
                                "role": "user",
                                "content": "Does this contract create regulatory exposure?",
                            }
                        ],
                        "config": {
                            "classifier_mode": "hybrid",
                            "tiers": {
                                "cheap": "llama3.2",
                                "mid": "qwen2.5-coder:14b",
                                "frontier": "deepseek-r1:14b",
                            },
                            "matrix": {
                                "simple": {"low": "cheap", "high": "mid"},
                                "medium": {"low": "mid", "high": "frontier"},
                                "complex": {"low": "frontier", "high": "frontier"},
                            },
                            "reasoning_effort": True,
                            "on_failure": "passthrough",
                        },
                    },
                    auth=False,
                ),
            ],
        }
    )
    items.append(
        {
            "name": "Memory Service",
            "description": "Cognitive layer — Letta-backed memory ({{memory_url}}, default :8211). No auth.",
            "item": [
                _req(
                    "Health",
                    "GET",
                    "{{memory_url}}/health",
                    "Liveness + Letta reachability.",
                    None,
                    auth=False,
                ),
                _req(
                    "Store",
                    "POST",
                    "{{memory_url}}/memory",
                    "Store a memory (kind: fact|preference|decision|episode).",
                    {
                        "workspace": "{{workspace_id}}",
                        "kind": "decision",
                        "text": "We standardized on Qdrant.",
                    },
                    auth=False,
                ),
                _req(
                    "Recall",
                    "POST",
                    "{{memory_url}}/recall",
                    "Recall top-k memories for a query.",
                    {
                        "workspace": "{{workspace_id}}",
                        "query": "what vector database do we use?",
                        "k": 3,
                    },
                    auth=False,
                ),
            ],
        }
    )
    items.append(
        {
            "name": "Knowledge Graph",
            "description": "Cognitive layer — Kùzu graph ({{kg_url}}, default :8212). No auth.",
            "item": [
                _req("Health", "GET", "{{kg_url}}/health", "Liveness.", None, auth=False),
                _req(
                    "Add entity",
                    "POST",
                    "{{kg_url}}/entities",
                    "Upsert an entity.",
                    {
                        "workspace": "{{workspace_id}}",
                        "id": "svc-api",
                        "type": "service",
                        "name": "API",
                    },
                    auth=False,
                ),
                _req(
                    "Add relation",
                    "POST",
                    "{{kg_url}}/relations",
                    "Add a relationship.",
                    {
                        "workspace": "{{workspace_id}}",
                        "from_id": "svc-api",
                        "to_id": "db-pg",
                        "type": "depends_on",
                    },
                    auth=False,
                ),
                _req(
                    "Neighbors",
                    "GET",
                    "{{kg_url}}/neighbors?workspace={{workspace_id}}&entity=svc-api",
                    "Connected entities.",
                    None,
                    auth=False,
                ),
            ],
        }
    )
    items.append(
        {
            "name": "Skill Registry",
            "description": "Cognitive layer — skills ({{skill_url}}, default :8213). No auth.",
            "item": [
                _req("Health", "GET", "{{skill_url}}/health", "Liveness.", None, auth=False),
                _req(
                    "Upsert skill",
                    "POST",
                    "{{skill_url}}/skills",
                    "Store a skill.",
                    {
                        "workspace": "{{workspace_id}}",
                        "name": "deploy",
                        "description": "How to deploy",
                        "content": "1. build 2. push",
                        "version": 1,
                    },
                    auth=False,
                ),
                _req(
                    "List skills",
                    "GET",
                    "{{skill_url}}/skills?workspace={{workspace_id}}",
                    "List skills.",
                    None,
                    auth=False,
                ),
            ],
        }
    )
    items.append(
        {
            "name": "Compression Service",
            "description": "Direct calls to the LLMLingua-2 compression microservice ({{compression_url}}, default :8209). No auth.",
            "item": [
                _req(
                    "Health",
                    "GET",
                    "{{compression_url}}/health",
                    "Liveness + available models.",
                    None,
                    auth=False,
                ),
                _req(
                    "Compress",
                    "POST",
                    "{{compression_url}}/compress",
                    "Compress text to a target keep-rate; returns { compressed_text, original_tokens, compressed_tokens, ratio }.",
                    {
                        "text": "The parental leave policy grants sixteen weeks of fully paid leave to all "
                        "full-time employees and benefits continue throughout the leave period.",
                        "rate": 0.5,
                        "model": "bert-base-multilingual",
                    },
                    auth=False,
                ),
            ],
        }
    )
    items.append(
        {
            "name": "Flywheel Service",
            "description": "Direct calls to the stateless flywheel analyzer ({{flywheel_url}}, default :8215). No auth.",
            "item": [
                _req("Health", "GET", "{{flywheel_url}}/health", "Liveness.", None, auth=False),
                _req(
                    "Analyze",
                    "POST",
                    "{{flywheel_url}}/analyze",
                    "Given per-segment observations, return the cheapest config per segment that holds the SLA.",
                    {
                        "segment_by": "outcome_type",
                        "min_quality": 0.85,
                        "min_sample_size": 20,
                        "segments": [
                            {
                                "segment_key": "refund_resolved",
                                "observations": [
                                    {
                                        "config": {"model": "deepseek-r1:14b"},
                                        "n": 140,
                                        "avg_cost_per_req": 0.0028,
                                        "quality": 0.94,
                                    },
                                    {
                                        "config": {"model": "llama3.2"},
                                        "n": 90,
                                        "avg_cost_per_req": 0.0006,
                                        "quality": 0.90,
                                    },
                                ],
                            }
                        ],
                    },
                    auth=False,
                ),
            ],
        }
    )


_add_optimization_extras(items_list)


def _split_settings(items: list[dict]) -> None:
    """Split mixed /settings endpoints into UI-aligned Control Plane and Settings folders."""
    settings = next((it for it in items if it["name"] == "Settings / API Keys"), None)
    if settings is None:
        return

    api_key_items = []
    email_items = []
    other_items = []
    for item in settings["item"]:
        raw = item["request"]["url"].get("raw", "")
        if "/settings/api-keys" in raw:
            api_key_items.append(item)
        elif "/settings/email" in raw:
            email_items.append(item)
        else:
            other_items.append(item)

    items.remove(settings)
    insert_at = 0
    for idx, folder in enumerate(items):
        if folder["name"].startswith("Provider Profiles"):
            insert_at = idx + 1
            break

    if api_key_items:
        items.insert(
            insert_at,
            {
                "name": "Control Plane - API Keys",
                "item": api_key_items,
                "description": (
                    "Workspace API-key management. Org/platform admins can manage keys across "
                    "org workspaces; workspace admins can manage keys for their active workspace."
                ),
            },
        )
        insert_at += 1

    if email_items:
        items.insert(
            insert_at,
            {
                "name": "Platform Settings - Email",
                "item": email_items,
                "description": "Platform-admin-only email preferences, log, and test-send endpoints.",
            },
        )
        insert_at += 1

    if other_items:
        items.insert(
            insert_at,
            {
                "name": "Settings / Other",
                "item": other_items,
                "description": "Other settings endpoints.",
            },
        )


_split_settings(items_list)

# ── Assemble collection ───────────────────────────────────────────────────────
collection = {
    "info": {
        "_postman_id": str(uuid.uuid4()),
        "name": "RunLedger API",
        "description": (
            "RunLedger — Agent FinOps Control Plane.\n\n"
            "Full API surface: ingest, analytics, budgets, billing, model gateway, "
            "evaluations, prompts, SSO, SCIM, warehouse, OTLP and more.\n\n"
            "**RBAC token model:** use a dashboard session key from `POST /auth/login` "
            "for management APIs (Organizations, Gateway routes, Provider Profiles, "
            "Control Plane, Budgets). Use a workspace API key minted from Control Plane "
            "-> API Keys for data-plane APIs (`/ingest`, `/gateway/chat/completions`, "
            "`/v1/traces`). Keep the active token in `api_key`.\n\n"
            "**Setup:**\n"
            "1. Import this collection\n"
            "2. Import the companion environment (RunLedger Environment)\n"
            "3. Set `base_url`\n"
            "4. Run `POST /admin/bootstrap` once on a fresh install\n"
            "5. Log in with `POST /auth/login`; copy the returned key into `api_key` "
            "and `session_api_key`\n"
            "6. For agent traffic, create a workspace key with `POST /settings/api-keys`; "
            "copy it into `workspace_api_key` and swap `api_key` when calling data-plane endpoints"
        ),
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
    },
    "item": items_list,
}

# ── Companion environment ──────────────────────────────────────────────────────
environment = {
    "id": str(uuid.uuid4()),
    "name": "RunLedger Environment",
    "values": [
        {
            "key": "base_url",
            "value": "http://localhost:8201",
            "type": "default",
            "enabled": True,
            "description": "RunLedger API base URL. Change to your deployed URL for production.",
        },
        {
            "key": "gateway_base_url",
            "value": "http://localhost:8210",
            "type": "default",
            "enabled": True,
            "description": "RunLedger Rust gateway runtime base URL for live /gateway/chat/completions traffic.",
        },
        {
            "key": "semantic_cache_url",
            "value": "http://localhost:8205",
            "type": "default",
            "enabled": True,
            "description": "Semantic-cache microservice base URL (optimization layer).",
        },
        {
            "key": "context_compiler_url",
            "value": "http://localhost:8207",
            "type": "default",
            "enabled": True,
            "description": "Context-compiler microservice base URL (optimization layer).",
        },
        {
            "key": "flywheel_url",
            "value": "http://localhost:8215",
            "type": "default",
            "enabled": True,
            "description": "Flywheel analyzer microservice base URL (optimization layer).",
        },
        {
            "key": "compression_url",
            "value": "http://localhost:8209",
            "type": "default",
            "enabled": True,
            "description": "LLMLingua-2 compression microservice base URL (optimization layer).",
        },
        {
            "key": "router_url",
            "value": "http://localhost:8210",
            "type": "default",
            "enabled": True,
            "description": "Intelligent-router microservice base URL (optimization layer).",
        },
        {
            "key": "memory_url",
            "value": "http://localhost:8211",
            "type": "default",
            "enabled": True,
            "description": "Memory microservice base URL (cognitive layer).",
        },
        {
            "key": "kg_url",
            "value": "http://localhost:8212",
            "type": "default",
            "enabled": True,
            "description": "Knowledge-graph microservice base URL (cognitive layer).",
        },
        {
            "key": "skill_url",
            "value": "http://localhost:8213",
            "type": "default",
            "enabled": True,
            "description": "Skill-registry microservice base URL (cognitive layer).",
        },
        {
            "key": "api_key",
            "value": "",
            "type": "secret",
            "enabled": True,
            "description": "Active Bearer token. Use a dashboard session key for management APIs, or a workspace API key for data-plane APIs.",
        },
        {
            "key": "session_api_key",
            "value": "",
            "type": "secret",
            "enabled": True,
            "description": "Dashboard session key returned by POST /auth/login. Required for management APIs and RBAC checks.",
        },
        {
            "key": "workspace_api_key",
            "value": "",
            "type": "secret",
            "enabled": True,
            "description": "Long-lived workspace API key minted from Control Plane -> API Keys or POST /settings/api-keys. Use for ingest, OTLP, and gateway chat completions.",
        },
        {
            "key": "platform_admin_key",
            "value": "",
            "type": "secret",
            "enabled": True,
            "description": "Optional platform-admin dashboard session key for Organizations and platform Settings.",
        },
        {
            "key": "org_admin_key",
            "value": "",
            "type": "secret",
            "enabled": True,
            "description": "Optional org-admin dashboard session key for Gateway, Provider Profiles, Control Plane, Users, and Workspaces.",
        },
        {
            "key": "workspace_admin_key",
            "value": "",
            "type": "secret",
            "enabled": True,
            "description": "Optional workspace-admin dashboard session key for active-workspace API Keys, Budgets, Approvals, and Audit Log.",
        },
        {
            "key": "workspace_id",
            "value": "",
            "type": "default",
            "enabled": True,
            "description": "Workspace UUID — set after login. Most endpoints scope data to this workspace.",
        },
        {
            "key": "kafka_config_id",
            "value": "",
            "type": "default",
            "enabled": True,
            "description": "Kafka export config UUID from POST /integrations/kafka/configs.",
        },
        {
            "key": "kafka_bootstrap_servers",
            "value": "localhost:9092",
            "type": "default",
            "enabled": True,
            "description": "Kafka bootstrap servers for export tests.",
        },
        {
            "key": "kafka_topic_prefix",
            "value": "runledger",
            "type": "default",
            "enabled": True,
            "description": "Topic prefix for RunLedger export events.",
        },
        {
            "key": "tenant_id",
            "value": "",
            "type": "default",
            "enabled": True,
            "description": "Tenant / organisation UUID — returned by /admin/bootstrap and /auth/login.",
        },
        {
            "key": "user_id",
            "value": "",
            "type": "default",
            "enabled": True,
            "description": "Authenticated user UUID — returned by /auth/login.",
        },
        {
            "key": "run_id",
            "value": "",
            "type": "default",
            "enabled": True,
            "description": "Agent run UUID — set after ingesting a run_start event.",
        },
        {
            "key": "span_id",
            "value": "",
            "type": "default",
            "enabled": True,
            "description": "Span UUID — set after ingesting a span_start event.",
        },
        {
            "key": "budget_id",
            "value": "",
            "type": "default",
            "enabled": True,
            "description": "Budget UUID — set after creating a budget.",
        },
        {
            "key": "billing_period_id",
            "value": "",
            "type": "default",
            "enabled": True,
            "description": "Billing period UUID — set after creating a billing period.",
        },
        {
            "key": "gateway_route_id",
            "value": "",
            "type": "default",
            "enabled": True,
            "description": "Gateway route UUID — set after creating a route.",
        },
        {
            "key": "prompt_name",
            "value": "my-prompt",
            "type": "default",
            "enabled": True,
            "description": "Prompt name slug — used in prompt version and promotion endpoints.",
        },
        {
            "key": "alert_rule_id",
            "value": "",
            "type": "default",
            "enabled": True,
            "description": "Alert rule UUID.",
        },
        {
            "key": "approval_id",
            "value": "",
            "type": "default",
            "enabled": True,
            "description": "Approval request UUID.",
        },
        {
            "key": "sso_config_id",
            "value": "",
            "type": "default",
            "enabled": True,
            "description": "SSO configuration UUID.",
        },
        {
            "key": "warehouse_destination_id",
            "value": "",
            "type": "default",
            "enabled": True,
            "description": "Warehouse destination UUID.",
        },
        {
            "key": "retention_policy_id",
            "value": "",
            "type": "default",
            "enabled": True,
            "description": "Retention policy UUID.",
        },
        {
            "key": "invoice_id",
            "value": "",
            "type": "default",
            "enabled": True,
            "description": "Provider invoice UUID.",
        },
        {
            "key": "experiment_id",
            "value": "",
            "type": "default",
            "enabled": True,
            "description": "Replay experiment UUID.",
        },
        {
            "key": "dataset_id",
            "value": "",
            "type": "default",
            "enabled": True,
            "description": "Replay dataset UUID.",
        },
        {
            "key": "agent_id",
            "value": "",
            "type": "default",
            "enabled": True,
            "description": "Agent UUID — set after registering an agent.",
        },
        {
            "key": "workflow_id",
            "value": "",
            "type": "default",
            "enabled": True,
            "description": "Workflow definition UUID — set after creating a workflow.",
        },
        {
            "key": "step_id",
            "value": "",
            "type": "default",
            "enabled": True,
            "description": "Workflow step UUID — set after creating a step.",
        },
        {
            "key": "collection_id",
            "value": "",
            "type": "default",
            "enabled": True,
            "description": "Vector store collection UUID — set after creating a collection.",
        },
        {
            "key": "session_id",
            "value": "",
            "type": "default",
            "enabled": True,
            "description": "Playground session UUID — set after creating a session.",
        },
        {
            "key": "request_id",
            "value": "",
            "type": "default",
            "enabled": True,
            "description": "Playground request UUID — set after sending a request.",
        },
        {
            "key": "admin_secret",
            "value": "runledger-admin",
            "type": "secret",
            "enabled": True,
            "description": "X-Admin-Secret header value for /admin/bootstrap.",
        },
    ],
    "_postman_variable_scope": "environment",
}

# ── Write output files ─────────────────────────────────────────────────────────
collection_path = sys.argv[2] if len(sys.argv) > 2 else "/tmp/RunLedger.postman_collection.json"
env_path = sys.argv[3] if len(sys.argv) > 3 else "/tmp/RunLedger.postman_environment.json"

with open(collection_path, "w") as f:
    json.dump(collection, f, indent=2)

with open(env_path, "w") as f:
    json.dump(environment, f, indent=2)

folders = len(items_list)
ops = sum(len(folder["item"]) for folder in items_list)
print(f"Collection: {collection_path}  ({folders} folders, {ops} requests)")
print(f"Environment: {env_path}  ({len(environment['values'])} variables)")
