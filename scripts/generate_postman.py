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
    ("budgets", "Budgets"),
    ("billing", "Billing"),
    ("invoices", "Invoices"),
    ("outcomes", "Outcomes & ROI"),
    ("approvals", "Approvals"),
    ("gateway", "Model Gateway"),
    ("evaluations", "Evaluations"),
    ("experiments", "Experiments"),
    ("prompts", "Prompts"),
    ("alerts", "Alerts"),
    ("ledger", "Ledger"),
    ("tools", "Tools"),
    ("pricing-intelligence", "Pricing Intelligence"),
    ("providers", "Providers"),
    ("settings", "Settings"),
    ("sso", "SSO"),
    ("scim", "SCIM"),
    ("users", "Users"),
    ("organization", "Organization"),
    ("platform-admin", "Platform Admin"),
    ("saas", "SaaS / Billing"),
    ("audit", "Audit"),
    ("policies", "Policies"),
    ("privacy", "Privacy"),
    ("retention", "Retention"),
    ("replay", "Replay"),
    ("warehouse", "Warehouse"),
    ("OTLP", "OTLP"),
    ("Kafka Export", "Kafka Export"),
    ("admin", "Bootstrap / Admin"),
    ("integrations", "Integrations"),
    ("Operations", "Operations"),
]


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
        for method, op in methods.items():
            if method == "parameters":
                continue
            if tag not in op.get("tags", []):
                continue

            raw_parts, path_vars = make_url(path)
            url_obj: dict = {
                "raw": "{{base_url}}/" + "/".join(raw_parts),
                "host": ["{{base_url}}"],
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
                    {"key": "Authorization", "value": "Bearer {{api_key}}"},
                ],
                "url": url_obj,
                "description": op.get("description", op.get("summary", "")),
            }
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
def _req(name, method, raw_url, desc, body=None, auth=True):
    parts = raw_url.split("/")
    headers = [{"key": "Content-Type", "value": "application/json"}]
    if auth:
        headers.append({"key": "Authorization", "value": "Bearer {{api_key}}"})
    r = {
        "method": method,
        "header": headers,
        "url": {"raw": raw_url, "host": [parts[0]], "path": parts[1:]},
        "description": desc,
    }
    if body is not None:
        r["body"] = {"mode": "raw", "raw": json.dumps(body, indent=2), "options": {"raw": {"language": "json"}}}
    return {"name": name, "request": r, "response": []}


def _add_optimization_extras(items: list[dict]) -> None:
    gw = next((it for it in items if it["name"] == "Model Gateway"), None)
    if gw is not None:
        sys_hr = {"role": "system", "content": "You are a concise HR assistant."}
        gw["item"] += [
            _req("Gateway Chat Completions (Semantic Cache)", "POST",
                 "{{base_url}}/gateway/chat/completions",
                 "Near-duplicate prompt served from the semantic cache (decision_reason=semantic_cache_hit).",
                 {"model": "gpt-4o-mini", "messages": [sys_hr, {"role": "user", "content": "how much parental leave do employees get"}], "semantic_cache": True}),
            _req("Gateway Chat Completions (Context Compiler)", "POST",
                 "{{base_url}}/gateway/chat/completions",
                 "Request shrunk (dedup/tool-output/rerank/compaction) before routing.",
                 {"model": "gpt-4o-mini", "messages": [sys_hr, {"role": "user", "content": "How much parental leave do employees get?"}], "context_compiler": True}),
            _req("Gateway Chat Completions (Intelligent Routing)", "POST",
                 "{{base_url}}/gateway/chat/completions",
                 "Classify complexity × risk and route to a model tier (decision_reason shows the tier).",
                 {"model": "auto", "messages": [sys_hr, {"role": "user", "content": "Does this contract create regulatory exposure?"}], "intelligent_routing": True}),
            _req("Create Gateway Route (Semantic Cache + Compiler on)", "POST",
                 "{{base_url}}/gateway/routes",
                 "Create a route with the semantic cache and context compiler enabled, incl. compiler config.",
                 {"alias": "gpt-4o-mini", "provider": "openai", "target_model": "gpt-4o-mini",
                  "api_key_env_var": "OPENAI_API_KEY", "priority": 10, "semantic_cache_enabled": True,
                  "context_compiler_enabled": True,
                  "context_compiler_config": {"model": "llama3.1:8b", "reranker_model": "flashrank", "token_threshold": 2000, "token_budget": 32000}}),
        ]
    scope = {"tenant": "{{workspace_id}}", "model": "gpt-4o-mini", "system_prompt_hash": "", "knowledge_version": "", "security_scope": ""}
    items.append({"name": "Semantic Cache Service",
        "description": "Direct calls to the semantic-cache microservice ({{semantic_cache_url}}, default :8205). No auth.",
        "item": [
            _req("Health", "GET", "{{semantic_cache_url}}/health", "Liveness + Qdrant collection status.", None, auth=False),
            _req("Lookup", "POST", "{{semantic_cache_url}}/lookup", "Semantic hit within scope (score >= threshold).",
                 {"text": "how much parental leave do employees get", "scope": scope, "threshold": 0.95}, auth=False),
            _req("Store", "POST", "{{semantic_cache_url}}/store", "Store a response for future semantic hits.",
                 {"text": "How much parental leave do employees get?", "scope": scope,
                  "response": {"choices": [{"message": {"role": "assistant", "content": "16 weeks paid."}}], "usage": {"prompt_tokens": 20, "completion_tokens": 12}},
                  "prompt_tokens": 20, "completion_tokens": 12}, auth=False),
        ]})
    items.append({"name": "Context Compiler Service",
        "description": "Direct calls to the context-compiler microservice ({{context_compiler_url}}, default :8207). No auth.",
        "item": [
            _req("Health", "GET", "{{context_compiler_url}}/health", "Liveness + downstream URLs.", None, auth=False),
            _req("Compile", "POST", "{{context_compiler_url}}/compile",
                 "Shrink a messages array; returns { messages, token_report, dropped }.",
                 {"messages": [{"role": "system", "content": "You are a concise HR assistant. Parental leave is 16 weeks paid."},
                               {"role": "system", "content": "You are a concise HR assistant. Parental leave is 16 weeks paid."},
                               {"role": "user", "content": "How much parental leave do employees get?"}],
                  "config": {"reranker_model": "flashrank", "token_threshold": 0, "token_budget": 400,
                             "stages": {"dedup": True, "tool_output": True, "rerank": True, "compaction": True, "compress": False}}}, auth=False),
        ]})
    items.append({"name": "Router Service",
        "description": "Direct calls to the intelligent-router microservice ({{router_url}}, default :8210). No auth.",
        "item": [
            _req("Health", "GET", "{{router_url}}/health", "Liveness + classifier modes.", None, auth=False),
            _req("Classify", "POST", "{{router_url}}/classify",
                 "Classify complexity × risk → tier; returns { complexity, risk, reasoning_effort, tier, alias }.",
                 {"messages": [{"role": "user", "content": "Does this contract create regulatory exposure?"}],
                  "config": {"classifier_mode": "hybrid",
                             "tiers": {"cheap": "gpt-4o-mini", "mid": "gpt-4o", "frontier": "o1"},
                             "matrix": {"simple": {"low": "cheap", "high": "mid"},
                                        "medium": {"low": "mid", "high": "frontier"},
                                        "complex": {"low": "frontier", "high": "frontier"}},
                             "reasoning_effort": True, "on_failure": "passthrough"}}, auth=False),
        ]})
    items.append({"name": "Memory Service",
        "description": "Cognitive layer — Letta-backed memory ({{memory_url}}, default :8211). No auth.",
        "item": [
            _req("Health", "GET", "{{memory_url}}/health", "Liveness + Letta reachability.", None, auth=False),
            _req("Store", "POST", "{{memory_url}}/memory",
                 "Store a memory (kind: fact|preference|decision|episode).",
                 {"workspace": "{{workspace_id}}", "kind": "decision", "text": "We standardized on Qdrant."}, auth=False),
            _req("Recall", "POST", "{{memory_url}}/recall", "Recall top-k memories for a query.",
                 {"workspace": "{{workspace_id}}", "query": "what vector database do we use?", "k": 3}, auth=False),
        ]})
    items.append({"name": "Knowledge Graph",
        "description": "Cognitive layer — Kùzu graph ({{kg_url}}, default :8212). No auth.",
        "item": [
            _req("Health", "GET", "{{kg_url}}/health", "Liveness.", None, auth=False),
            _req("Add entity", "POST", "{{kg_url}}/entities", "Upsert an entity.",
                 {"workspace": "{{workspace_id}}", "id": "svc-api", "type": "service", "name": "API"}, auth=False),
            _req("Add relation", "POST", "{{kg_url}}/relations", "Add a relationship.",
                 {"workspace": "{{workspace_id}}", "from_id": "svc-api", "to_id": "db-pg", "type": "depends_on"}, auth=False),
            _req("Neighbors", "GET", "{{kg_url}}/neighbors?workspace={{workspace_id}}&entity=svc-api",
                 "Connected entities.", None, auth=False),
        ]})
    items.append({"name": "Skill Registry",
        "description": "Cognitive layer — skills ({{skill_url}}, default :8213). No auth.",
        "item": [
            _req("Health", "GET", "{{skill_url}}/health", "Liveness.", None, auth=False),
            _req("Upsert skill", "POST", "{{skill_url}}/skills", "Store a skill.",
                 {"workspace": "{{workspace_id}}", "name": "deploy", "description": "How to deploy", "content": "1. build 2. push", "version": 1}, auth=False),
            _req("List skills", "GET", "{{skill_url}}/skills?workspace={{workspace_id}}", "List skills.", None, auth=False),
        ]})
    items.append({"name": "Compression Service",
        "description": "Direct calls to the LLMLingua-2 compression microservice ({{compression_url}}, default :8209). No auth.",
        "item": [
            _req("Health", "GET", "{{compression_url}}/health", "Liveness + available models.", None, auth=False),
            _req("Compress", "POST", "{{compression_url}}/compress",
                 "Compress text to a target keep-rate; returns { compressed_text, original_tokens, compressed_tokens, ratio }.",
                 {"text": "The parental leave policy grants sixteen weeks of fully paid leave to all "
                          "full-time employees and benefits continue throughout the leave period.",
                  "rate": 0.5, "model": "bert-base-multilingual"}, auth=False),
        ]})


_add_optimization_extras(items_list)

# ── Assemble collection ───────────────────────────────────────────────────────
collection = {
    "info": {
        "_postman_id": str(uuid.uuid4()),
        "name": "RunLedger API",
        "description": (
            "RunLedger — Agent FinOps Control Plane.\n\n"
            "Full API surface: ingest, analytics, budgets, billing, model gateway, "
            "evaluations, prompts, SSO, SCIM, warehouse, OTLP and more.\n\n"
            "**Setup:**\n"
            "1. Import this collection\n"
            "2. Import the companion environment (RunLedger Environment)\n"
            "3. Set `base_url`, `api_key`, and `workspace_id` in the environment\n"
            "4. Run `POST /admin/bootstrap` once on a fresh install to get your api_key"
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
        {"key": "memory_url", "value": "http://localhost:8211", "type": "default", "enabled": True,
         "description": "Memory microservice base URL (cognitive layer)."},
        {"key": "kg_url", "value": "http://localhost:8212", "type": "default", "enabled": True,
         "description": "Knowledge-graph microservice base URL (cognitive layer)."},
        {"key": "skill_url", "value": "http://localhost:8213", "type": "default", "enabled": True,
         "description": "Skill-registry microservice base URL (cognitive layer)."},
        {
            "key": "api_key",
            "value": "",
            "type": "secret",
            "enabled": True,
            "description": "RunLedger API key (rl_... prefix). Get one from POST /admin/bootstrap or POST /auth/login.",
        },
        {
            "key": "workspace_id",
            "value": "",
            "type": "default",
            "enabled": True,
            "description": "Workspace UUID — set after login. Most endpoints scope data to this workspace.",
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
