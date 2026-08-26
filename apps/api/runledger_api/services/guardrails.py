"""Guardrail execution engine — sandboxed evaluation, built-in content filters, templates."""

from __future__ import annotations

import re
import time
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.guardrails import GuardrailEvent, GuardrailRule

log = structlog.get_logger()

# ── Guardrail execution result helpers ───────────────────────────────────────


class GuardrailResult:
    """Outcome of evaluating one guardrail against a request."""

    __slots__ = ("decision", "reason", "modified_texts", "modified_images", "modified_tool_calls")

    def __init__(
        self,
        decision: str = "allow",
        reason: str | None = None,
        modified_texts: list[str] | None = None,
        modified_images: list[str] | None = None,
        modified_tool_calls: list[dict[str, Any]] | None = None,
    ):
        self.decision = decision
        self.reason = reason
        self.modified_texts = modified_texts
        self.modified_images = modified_images
        self.modified_tool_calls = modified_tool_calls


def allow() -> GuardrailResult:
    return GuardrailResult("allow")


def block(reason: str = "Blocked by guardrail") -> GuardrailResult:
    return GuardrailResult("block", reason=reason)


def modify(
    texts: list[str] | None = None,
    images: list[str] | None = None,
    tool_calls: list[dict[str, Any]] | None = None,
) -> GuardrailResult:
    return GuardrailResult(
        "modify",
        reason="Modified by guardrail",
        modified_texts=texts,
        modified_images=images,
        modified_tool_calls=tool_calls,
    )


# ── Sandboxed execution (RestrictedPython-style) ─────────────────────────────


_SANDBOX_GLOBALS: dict[str, Any] = {
    "__builtins__": {
        "len": len,
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "list": list,
        "dict": dict,
        "set": set,
        "tuple": tuple,
        "range": range,
        "enumerate": enumerate,
        "zip": zip,
        "any": any,
        "all": all,
        "min": min,
        "max": max,
        "sum": sum,
        "abs": abs,
        "sorted": sorted,
        "reversed": reversed,
        "isinstance": isinstance,
        "True": True,
        "False": False,
        "None": None,
    },
    "allow": allow,
    "block": block,
    "modify": modify,
    "re": re,
}

_BLOCKED_PATTERNS = [
    r"\bimport\b",
    r"\b__import__\b",
    r"\bexec\b",
    r"\beval\b",
    r"\bcompile\b",
    r"\bopen\b",
    r"\bgetattr\b",
    r"\bsetattr\b",
    r"\bdelattr\b",
    r"\bglobals\b",
    r"\blocals\b",
    r"\bvars\b",
    r"\bdir\b",
    r"\b__class__\b",
    r"\b__subclasses__\b",
    r"\b__bases__\b",
    r"\b__mro__\b",
    r"\bbreakpoint\b",
    r"\bos\.\b",
    r"\bsys\.\b",
    r"\bsubprocess\b",
]


def _validate_logic(logic: str) -> str | None:
    for pattern in _BLOCKED_PATTERNS:
        if re.search(pattern, logic):
            return f"Blocked pattern detected: {pattern}"
    return None


def execute_custom_logic(
    logic: str,
    texts: list[str],
    images: list[str],
    tools: list[dict[str, Any]],
    tool_calls: list[dict[str, Any]],
    structured_messages: list[dict[str, Any]],
    model: str | None,
    user_id: str | None,
    team_id: str | None,
    end_user_id: str | None,
    metadata: dict[str, Any],
    timeout_ms: float = 500,
) -> GuardrailResult:
    """Execute custom guardrail logic in a restricted sandbox."""
    validation_err = _validate_logic(logic)
    if validation_err:
        return GuardrailResult("allow", reason=f"Logic validation failed: {validation_err}")

    sandbox_locals: dict[str, Any] = {
        "texts": texts,
        "images": images,
        "tools": tools,
        "tool_calls": tool_calls,
        "structured_messages": structured_messages,
        "model": model,
        "user_id": user_id,
        "team_id": team_id,
        "end_user_id": end_user_id,
        "metadata": metadata,
    }

    try:
        compiled = compile(logic, "<guardrail>", "exec")
        exec(compiled, dict(_SANDBOX_GLOBALS), sandbox_locals)  # noqa: S102
        result = sandbox_locals.get("result")
        if isinstance(result, GuardrailResult):
            return result
        return GuardrailResult("allow", reason="No result returned from guardrail logic")
    except Exception as exc:
        log.warning("guardrail_execution_error", error=str(exc))
        return GuardrailResult("allow", reason=f"Execution error: {exc}")


# ── Built-in content filters ─────────────────────────────────────────────────


BUILTIN_FILTERS: dict[str, dict[str, Any]] = {
    "denied_financial_advice": {
        "name": "Denied Financial Advice",
        "description": "Block personalized investment/financial advice",
        "category": "content_safety",
        "keywords": [
            "invest in",
            "buy stock",
            "sell stock",
            "portfolio advice",
            "financial advice",
            "investment recommendation",
            "trade shares",
            "crypto investment",
            "retirement planning advice",
        ],
        "patterns": [
            r"(?i)\b(should|recommend|advise)\b.{0,30}\b(invest|buy|sell|trade)\b",
            r"(?i)\b(financial|investment)\s+(advice|recommendation|guidance)\b",
        ],
    },
    "health_personal_advice": {
        "name": "Health And Personal Advice",
        "description": "Detect health-related advice requests",
        "category": "content_safety",
        "keywords": [
            "diagnose",
            "diagnosis",
            "medical advice",
            "health advice",
            "prescription",
            "medication",
            "treatment plan",
            "symptoms indicate",
        ],
        "patterns": [
            r"(?i)\b(diagnose|prescribe|treat)\b.{0,40}\b(condition|disease|illness|symptoms)\b",
            r"(?i)\bmedical\s+(advice|diagnosis|recommendation)\b",
        ],
    },
    "denied_legal_advice": {
        "name": "Denied Legal Advice",
        "description": "Block unauthorized legal advice",
        "category": "content_safety",
        "keywords": [
            "legal advice",
            "sue them",
            "file lawsuit",
            "legal counsel",
            "legally obligated",
            "legal recommendation",
        ],
        "patterns": [
            r"(?i)\blegal\s+(advice|recommendation|counsel|guidance)\b",
            r"(?i)\b(should|recommend).{0,20}\b(sue|lawsuit|litigate)\b",
        ],
    },
    "denied_medical_advice": {
        "name": "Denied Medical Advice",
        "description": "Block medical diagnosis/treatment advice",
        "category": "content_safety",
        "keywords": [
            "take this medication",
            "dosage recommendation",
            "stop taking",
            "increase dosage",
            "medical treatment",
            "drug interaction",
        ],
        "patterns": [
            r"(?i)\b(take|stop|increase|decrease)\s+\w+\s*(mg|dosage|medication)\b",
            r"(?i)\bdrug\s+interaction\b",
        ],
    },
    "harmful_violence": {
        "name": "Harmful Violence",
        "description": "Detect violent content",
        "category": "harmful",
        "keywords": [
            "how to kill",
            "make a weapon",
            "build a bomb",
            "hurt someone",
            "attack plan",
            "assassinate",
            "mass shooting",
        ],
        "patterns": [
            r"(?i)\bhow\s+to\s+(kill|harm|hurt|attack|assassinate)\b",
            r"(?i)\b(build|make|construct)\s+a?\s*(bomb|weapon|explosive)\b",
        ],
    },
    "harmful_self_harm": {
        "name": "Harmful Self-Harm",
        "description": "Detect self-harm content",
        "category": "harmful",
        "keywords": [
            "kill myself",
            "commit suicide",
            "end my life",
            "self-harm",
            "cut myself",
            "ways to die",
        ],
        "patterns": [
            r"(?i)\b(kill|harm|hurt|end)\s+(myself|my\s+life)\b",
            r"(?i)\bsuicid(e|al)\b",
        ],
    },
    "harmful_child_safety": {
        "name": "Harmful Child Safety",
        "description": "Detect child safety violations",
        "category": "harmful",
        "keywords": [
            "child exploitation",
            "minor abuse",
            "underage",
        ],
        "patterns": [
            r"(?i)\bchild\s+(exploitation|abuse|pornography)\b",
            r"(?i)\bunderage\s+(content|material|images)\b",
        ],
    },
    "harmful_illegal": {
        "name": "Harmful Illegal",
        "description": "Detect content related to illegal activities",
        "category": "harmful",
        "keywords": [
            "how to hack",
            "steal identity",
            "forge documents",
            "money laundering",
            "drug manufacturing",
            "counterfeit",
        ],
        "patterns": [
            r"(?i)\bhow\s+to\s+(hack|steal|forge|counterfeit|launder)\b",
            r"(?i)\b(manufacture|produce|synthesize)\s+\w*\s*(drugs|narcotics|methamphetamine)\b",
        ],
    },
    "bias_gender": {
        "name": "Bias Gender",
        "description": "Detect gender-based discrimination",
        "category": "bias",
        "keywords": [
            "women can't",
            "men are better",
            "girls shouldn't",
            "boys are smarter",
            "female weakness",
        ],
        "patterns": [
            r"(?i)\b(women|girls|females)\s+(can't|cannot|shouldn't|are\s+not\s+able)\b",
            r"(?i)\b(men|boys|males)\s+are\s+(better|superior|smarter)\b",
        ],
    },
    "bias_racial": {
        "name": "Bias Racial",
        "description": "Detect racial discrimination and bias",
        "category": "bias",
        "keywords": [
            "racial superiority",
            "ethnic cleansing",
            "race is inferior",
        ],
        "patterns": [
            r"(?i)\bracial\s+(superiority|inferiority|purity)\b",
            r"(?i)\bethnic\s+cleansing\b",
        ],
    },
    "toxicity": {
        "name": "Toxicity",
        "description": "Detect toxic language and harassment",
        "category": "content_safety",
        "keywords": [
            "you idiot",
            "stupid moron",
            "hate you",
            "kill yourself",
            "worthless",
            "die in a fire",
        ],
        "patterns": [
            r"(?i)\b(idiot|moron|imbecile|retard|loser)\b",
            r"(?i)\b(kill|die)\s+(yourself|in\s+a\s+fire)\b",
        ],
    },
    "code_injection": {
        "name": "Code Injection",
        "description": "Detect attempts to inject executable code",
        "category": "security",
        "keywords": [
            "ignore previous instructions",
            "system prompt",
            "jailbreak",
            "DAN mode",
            "developer mode override",
        ],
        "patterns": [
            r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|rules|guidelines)",
            r"(?i)\b(system|developer)\s+(prompt|mode)\s*(override|bypass|ignore)\b",
            r"(?i)\bjailbreak\b",
            r"<script\b",
            r"(?i)\bDAN\s+mode\b",
        ],
    },
    "data_exfiltration": {
        "name": "Data Exfiltration",
        "description": "Detect attempts to extract sensitive data",
        "category": "security",
        "keywords": [
            "show me the system prompt",
            "reveal your instructions",
            "what are your rules",
            "dump all data",
            "export all records",
        ],
        "patterns": [
            r"(?i)(show|reveal|display|dump|print)\s+(me\s+)?(the\s+)?(system\s+prompt|instructions|rules|training\s+data)",
            r"(?i)(export|extract|dump)\s+(all|every)\s+(data|records|users|customers)",
        ],
    },
}

# Severity thresholds: how many pattern/keyword hits trigger a block
_SEVERITY_THRESHOLDS = {
    "off": float("inf"),
    "low": 3,
    "medium": 2,
    "high": 1,
    "strict": 1,
}


def evaluate_builtin_filter(
    filter_name: str,
    texts: list[str],
    severity: str = "medium",
) -> GuardrailResult:
    """Run a built-in content filter against the provided texts."""
    if severity == "off":
        return allow()

    filter_def = BUILTIN_FILTERS.get(filter_name)
    if not filter_def:
        return allow()

    threshold = _SEVERITY_THRESHOLDS.get(severity, 2)
    combined_text = " ".join(texts).lower()
    hit_count = 0
    matched_reasons: list[str] = []

    for kw in filter_def.get("keywords", []):
        if kw.lower() in combined_text:
            hit_count += 1
            matched_reasons.append(f"keyword: {kw}")

    for pat in filter_def.get("patterns", []):
        if re.search(pat, " ".join(texts)):
            hit_count += 1
            matched_reasons.append("pattern match")

    if hit_count >= threshold:
        return block(f"{filter_def['name']}: {'; '.join(matched_reasons[:3])}")
    return allow()


# ── Guardrail templates ──────────────────────────────────────────────────────


GUARDRAIL_TEMPLATES: dict[str, dict[str, Any]] = {
    "pii_detection": {
        "name": "PII Detection",
        "description": "Detect and block personally identifiable information (email, phone, SSN, credit card)",
        "mode": "both",
        "category": "security",
        "default_logic": """
import re
pii_patterns = {
    "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}",
    "phone": r"\\b\\d{3}[-.]?\\d{3}[-.]?\\d{4}\\b",
    "ssn": r"\\b\\d{3}-\\d{2}-\\d{4}\\b",
    "credit_card": r"\\b(?:\\d{4}[- ]?){3}\\d{4}\\b",
}
combined = " ".join(texts)
found = []
for pii_type, pattern in pii_patterns.items():
    if re.search(pattern, combined):
        found.append(pii_type)
if found:
    result = block(f"PII detected: {', '.join(found)}")
else:
    result = allow()
""",
        "default_config": {},
    },
    "prompt_injection": {
        "name": "Prompt Injection Detection",
        "description": "Detect prompt injection and jailbreak attempts",
        "mode": "pre_call",
        "category": "security",
        "default_logic": """
injection_markers = [
    "ignore previous instructions", "ignore all prior",
    "system prompt", "reveal your", "jailbreak",
    "DAN mode", "developer mode", "bypass safety",
    "pretend you are", "act as if you have no restrictions",
]
combined = " ".join(texts).lower()
hits = [m for m in injection_markers if m in combined]
if hits:
    result = block(f"Prompt injection detected: {hits[0]}")
else:
    result = allow()
""",
        "default_config": {},
    },
    "topic_restriction": {
        "name": "Topic Restriction",
        "description": "Restrict conversation to approved topics only",
        "mode": "pre_call",
        "category": "policy",
        "default_logic": """
allowed_topics = metadata.get("allowed_topics", [])
if not allowed_topics:
    result = allow()
else:
    combined = " ".join(texts).lower()
    topic_found = any(t.lower() in combined for t in allowed_topics)
    if topic_found:
        result = allow()
    else:
        result = block(f"Off-topic: allowed topics are {', '.join(allowed_topics)}")
""",
        "default_config": {"allowed_topics": []},
    },
    "language_filter": {
        "name": "Language Filter",
        "description": "Filter profanity and inappropriate language",
        "mode": "both",
        "category": "content_safety",
        "default_logic": """
profanity_list = metadata.get("blocked_words", [])
combined = " ".join(texts).lower()
found = [w for w in profanity_list if w.lower() in combined]
if found:
    result = block(f"Inappropriate language detected")
else:
    result = allow()
""",
        "default_config": {"blocked_words": []},
    },
    "token_limit": {
        "name": "Token Limit Enforcement",
        "description": "Enforce maximum token count per request",
        "mode": "pre_call",
        "category": "cost",
        "default_logic": """
max_tokens = metadata.get("max_tokens", 100000)
estimated_tokens = sum(len(t.split()) * 1.3 for t in texts)
if estimated_tokens > max_tokens:
    result = block(f"Token limit exceeded: ~{int(estimated_tokens)} > {max_tokens}")
else:
    result = allow()
""",
        "default_config": {"max_tokens": 100000},
    },
    "model_restriction": {
        "name": "Model Restriction by Role",
        "description": "Restrict which models a user role can access",
        "mode": "pre_call",
        "category": "policy",
        "default_logic": """
allowed_models = metadata.get("allowed_models", [])
if not allowed_models or not model:
    result = allow()
elif model in allowed_models:
    result = allow()
else:
    result = block(f"Model '{model}' not allowed for this role. Allowed: {', '.join(allowed_models)}")
""",
        "default_config": {"allowed_models": []},
    },
    "support_scope_only": {
        "name": "Support Scope Only",
        "description": "Keep the assistant limited to support and account-help topics",
        "mode": "pre_call",
        "category": "operations",
        "default_logic": """
allowed_topics = metadata.get("allowed_topics", ["support", "billing", "account", "refund", "order", "help"])
combined = " ".join(texts).lower()
if any(topic.lower() in combined for topic in allowed_topics):
    result = allow()
else:
    result = block("Request is outside the approved support scope")
""",
        "default_config": {
            "allowed_topics": ["support", "billing", "account", "refund", "order", "help"]
        },
    },
    "secrets_detection": {
        "name": "Secrets and Tokens Detection",
        "description": "Block requests or responses that expose API keys, bearer tokens, or private keys",
        "mode": "both",
        "category": "security",
        "default_logic": """
combined = " ".join(texts)
secret_patterns = [
    "sk-",
    "ghp_",
    "xoxb-",
    "-----BEGIN PRIVATE KEY-----",
    "-----BEGIN RSA PRIVATE KEY-----",
    "Authorization: Bearer",
]
hits = [pattern for pattern in secret_patterns if pattern in combined]
if hits:
    result = block("Potential secret or credential material detected")
else:
    result = allow()
""",
        "default_config": {},
    },
    "customer_data_export_block": {
        "name": "Customer Data Export Block",
        "description": "Prevent bulk export or dump requests for sensitive customer records",
        "mode": "pre_call",
        "category": "privacy",
        "default_logic": """
combined = " ".join(texts).lower()
blocked_phrases = [
    "export all customers",
    "dump all users",
    "download every record",
    "list every customer email",
    "send me the full database",
]
if any(phrase in combined for phrase in blocked_phrases):
    result = block("Bulk customer-data export request detected")
else:
    result = allow()
""",
        "default_config": {},
    },
    "source_code_exfiltration": {
        "name": "Source Code Exfiltration",
        "description": "Block attempts to reveal protected internal source, prompts, or implementation details",
        "mode": "both",
        "category": "security",
        "default_logic": """
combined = " ".join(texts).lower()
blocked_markers = [
    "show me the source code",
    "print the internal prompt",
    "reveal the hidden instructions",
    "dump the repository",
    "show me the private implementation",
]
if any(marker in combined for marker in blocked_markers):
    result = block("Attempt to extract protected implementation details detected")
else:
    result = allow()
""",
        "default_config": {},
    },
    "competitor_mention_redirect": {
        "name": "Competitor Mention Redirect",
        "description": "Soft-redirect competitive displacement requests into neutral comparison language",
        "mode": "pre_call",
        "category": "policy",
        "default_logic": """
competitors = metadata.get("competitors", ["openai", "anthropic", "google", "microsoft"])
combined = " ".join(texts).lower()
hits = [name for name in competitors if name.lower() in combined]
if hits:
    result = modify(texts=["Please answer with a neutral comparison and avoid displacement claims."] + texts)
else:
    result = allow()
""",
        "default_config": {"competitors": ["openai", "anthropic", "google", "microsoft"]},
    },
    "financial_account_masking": {
        "name": "Financial Account Masking",
        "description": "Mask likely bank-account and routing-number patterns instead of returning them verbatim",
        "mode": "post_call",
        "category": "privacy",
        "default_logic": """
redacted = []
changed = False
for text in texts:
    updated = re.sub(r"\\b\\d{9,17}\\b", "[REDACTED_ACCOUNT]", text)
    if updated != text:
        changed = True
    redacted.append(updated)
if changed:
    result = modify(texts=redacted)
else:
    result = allow()
""",
        "default_config": {},
    },
    "employee_hr_boundary": {
        "name": "Employee HR Boundary",
        "description": "Stop the assistant from giving HR, disciplinary, or legal-employee decisions",
        "mode": "pre_call",
        "category": "compliance",
        "default_logic": """
combined = " ".join(texts).lower()
restricted = [
    "should we fire",
    "terminate this employee",
    "disciplinary action",
    "performance improvement plan decision",
    "legal hr advice",
]
if any(marker in combined for marker in restricted):
    result = block("HR and disciplinary decisions require a human reviewer")
else:
    result = allow()
""",
        "default_config": {},
    },
    "regulated_claims_review": {
        "name": "Regulated Claims Review",
        "description": "Force review for medical, legal, or investment claims in generated responses",
        "mode": "post_call",
        "category": "compliance",
        "default_logic": """
combined = " ".join(texts).lower()
markers = [
    "guaranteed return",
    "this will cure",
    "legally guaranteed",
    "prescribe",
    "diagnose",
]
if any(marker in combined for marker in markers):
    result = block("Regulated claim detected in output; human review required")
else:
    result = allow()
""",
        "default_config": {},
    },
    "geo_fence_restriction": {
        "name": "Geo Fence Restriction",
        "description": "Block requests from regions that are not allowed for a workflow",
        "mode": "pre_call",
        "category": "policy",
        "default_logic": """
allowed_regions = metadata.get("allowed_regions", [])
request_region = metadata.get("request_region")
if not allowed_regions or not request_region:
    result = allow()
elif request_region in allowed_regions:
    result = allow()
else:
    result = block(f"Region '{request_region}' is not allowed for this workflow")
""",
        "default_config": {"allowed_regions": []},
    },
    "approved_tool_only": {
        "name": "Approved Tool Calls Only",
        "description": "Deny requests that try to invoke tools outside an approved allowlist",
        "mode": "pre_call",
        "category": "security",
        "default_logic": """
allowed_tools = metadata.get("allowed_tools", [])
requested_names = []
for tool in tools:
    if isinstance(tool, dict):
        fn = tool.get("function") or {}
        name = fn.get("name") or tool.get("name")
        if name:
            requested_names.append(str(name))
unknown = [name for name in requested_names if allowed_tools and name not in allowed_tools]
if unknown:
    result = block(f"Tool access denied: {', '.join(unknown)}")
else:
    result = allow()
""",
        "default_config": {"allowed_tools": []},
    },
    "sql_safety": {
        "name": "SQL Safety Guard",
        "description": "Block prompts that ask for destructive or obviously unsafe SQL actions",
        "mode": "pre_call",
        "category": "security",
        "default_logic": """
combined = " ".join(texts).lower()
unsafe_sql = [
    "drop table",
    "truncate table",
    "delete from",
    "grant all privileges",
    "disable row level security",
]
if any(marker in combined for marker in unsafe_sql):
    result = block("Unsafe SQL instruction detected")
else:
    result = allow()
""",
        "default_config": {},
    },
    "allowed_domain_only": {
        "name": "Allowed Domain Replies Only",
        "description": "Keep generated answers aligned to an allowed business domain vocabulary",
        "mode": "post_call",
        "category": "policy",
        "default_logic": """
required_terms = metadata.get("required_terms", [])
if not required_terms:
    result = allow()
else:
    combined = " ".join(texts).lower()
    if any(term.lower() in combined for term in required_terms):
        result = allow()
    else:
        result = block("Response does not appear to stay within the required domain")
""",
        "default_config": {"required_terms": []},
    },
    "citation_required": {
        "name": "Citation Required for Factual Claims",
        "description": "Require a response to include citations or source markers for factual content",
        "mode": "post_call",
        "category": "quality",
        "default_logic": """
combined = " ".join(texts)
markers = metadata.get("citation_markers", ["http://", "https://", "[Source]", "[1]"])
if any(marker in combined for marker in markers):
    result = allow()
else:
    result = block("Response is missing citations or source markers")
""",
        "default_config": {"citation_markers": ["http://", "https://", "[Source]", "[1]"]},
    },
    "reply_length_cap": {
        "name": "Reply Length Cap",
        "description": "Prevent excessively long responses that increase cost or leak too much detail",
        "mode": "post_call",
        "category": "cost",
        "default_logic": """
max_words = metadata.get("max_words", 400)
word_count = sum(len(text.split()) for text in texts)
if word_count > max_words:
    result = block(f"Reply length {word_count} words exceeds cap {max_words}")
else:
    result = allow()
""",
        "default_config": {"max_words": 400},
    },
    "required_metadata_presence": {
        "name": "Required Metadata Presence",
        "description": "Block requests that do not include required metadata fields",
        "mode": "pre_call",
        "category": "operations",
        "default_logic": """
required_fields = metadata.get("required_fields", [])
missing = [field for field in required_fields if not metadata.get(field)]
if missing:
    result = block(f"Missing required metadata: {', '.join(missing)}")
else:
    result = allow()
""",
        "default_config": {"required_fields": ["workflow", "environment"]},
    },
    "customer_tone_rewrite": {
        "name": "Customer Tone Rewrite",
        "description": "Rewrite hostile or abrasive answers into a calmer customer-support tone",
        "mode": "post_call",
        "category": "quality",
        "default_logic": """
combined = " ".join(texts).lower()
abrasive_terms = ["obviously", "just read", "not my problem", "you should know", "that's wrong"]
if any(term in combined for term in abrasive_terms):
    rewritten = ["Please rewrite this answer in a calm, helpful, and respectful customer-support tone."] + texts
    result = modify(texts=rewritten)
else:
    result = allow()
""",
        "default_config": {},
    },
    "refund_policy_limit": {
        "name": "Refund Policy Limit",
        "description": "Keep refund decisions inside an approved value ceiling",
        "mode": "pre_call",
        "category": "operations",
        "default_logic": """
max_refund = metadata.get("max_refund_usd", 100)
combined = " ".join(texts).lower()
numbers = re.findall(r"\\$?(\\d+(?:\\.\\d+)?)", combined)
amounts = [float(value) for value in numbers]
if amounts and max(amounts) > max_refund:
    result = block(f"Requested refund exceeds allowed ceiling ${max_refund}")
else:
    result = allow()
""",
        "default_config": {"max_refund_usd": 100},
    },
    "cost_threshold": {
        "name": "Cost Threshold Gate",
        "description": "Block requests that would exceed a cost threshold",
        "mode": "pre_call",
        "category": "cost",
        "default_logic": """
max_cost_usd = metadata.get("max_cost_usd", 1.0)
estimated_tokens = sum(len(t.split()) * 1.3 for t in texts)
cost_per_1k = metadata.get("cost_per_1k_tokens", 0.01)
estimated_cost = (estimated_tokens / 1000) * cost_per_1k
if estimated_cost > max_cost_usd:
    result = block(f"Estimated cost ${estimated_cost:.4f} exceeds threshold ${max_cost_usd}")
else:
    result = allow()
""",
        "default_config": {"max_cost_usd": 1.0, "cost_per_1k_tokens": 0.01},
    },
}


def get_templates() -> list[dict[str, Any]]:
    """Return all available guardrail templates."""
    return [
        {
            "template_id": tid,
            "name": t["name"],
            "description": t["description"],
            "mode": t["mode"],
            "default_logic": t["default_logic"],
            "default_config": t["default_config"],
            "category": t["category"],
        }
        for tid, t in GUARDRAIL_TEMPLATES.items()
    ]


# ── Evaluate all guardrails for a request ────────────────────────────────────


async def evaluate_guardrails(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    mode: str,
    texts: list[str],
    images: list[str] | None = None,
    tools: list[dict[str, Any]] | None = None,
    tool_calls: list[dict[str, Any]] | None = None,
    structured_messages: list[dict[str, Any]] | None = None,
    model: str | None = None,
    user_id: str | None = None,
    team_id: str | None = None,
    end_user_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    gateway_request_id: uuid.UUID | None = None,
    guardrail_ids: list[uuid.UUID] | None = None,
) -> tuple[str, list[dict[str, Any]], float]:
    """
    Run all active guardrails for a workspace in priority order.

    Returns (overall_decision, results_list, total_latency_ms).
    Short-circuits on first block().
    """
    stmt = (
        select(GuardrailRule)
        .where(
            GuardrailRule.workspace_id == workspace_id,
            GuardrailRule.status == "active",
            GuardrailRule.mode.in_([mode, "both"]),
        )
        .order_by(GuardrailRule.priority.asc())
    )
    if guardrail_ids:
        stmt = stmt.where(GuardrailRule.id.in_(guardrail_ids))

    result = await db.execute(stmt)
    rules = list(result.scalars().all())

    # ── Resolve Access Group Guardrail Profile if user_id is provided ───────
    if user_id:
        try:
            from runledger_api.models.access_groups import (  # noqa: PLC0415
                AccessGroup,
                AccessGroupMember,
            )

            ag_stmt = (
                select(AccessGroup.guardrail_profile)
                .join(AccessGroupMember, AccessGroupMember.group_id == AccessGroup.id)
                .where(
                    AccessGroup.workspace_id == workspace_id,
                    AccessGroup.is_active.is_(True),
                    AccessGroupMember.user_id == user_id,
                    AccessGroup.guardrail_profile.isnot(None),
                )
                .limit(1)
            )
            ag_profile = (await db.execute(ag_stmt)).scalar_one_or_none()
            if ag_profile and ag_profile.startswith("rule:"):
                target_rule_name = ag_profile.split("rule:", 1)[1].strip()
                rule_match = await db.execute(
                    select(GuardrailRule).where(
                        GuardrailRule.workspace_id == workspace_id,
                        GuardrailRule.name == target_rule_name,
                    )
                )
                found_rule = rule_match.scalar_one_or_none()
                if found_rule and found_rule not in rules:
                    rules.append(found_rule)
        except Exception as exc:
            log.warning("access_group_guardrail_resolution_failed", error=str(exc))

    results: list[dict[str, Any]] = []
    overall_decision = "allow"
    total_latency = 0.0
    _images = images or []
    _tools = tools or []
    _tool_calls = tool_calls or []
    _msgs = structured_messages or []
    _meta = metadata or {}

    for rule in rules:
        start = time.monotonic()

        eval_texts = texts
        if rule.skip_system_messages and _msgs:
            eval_texts = [
                m.get("content", "")
                for m in _msgs
                if m.get("role") != "system" and m.get("content")
            ]
            if not eval_texts:
                eval_texts = texts

        error_str: str | None = None

        if rule.rule_type == "builtin_filter":
            gr = evaluate_builtin_filter(
                rule.template_id or rule.name.lower().replace(" ", "_"),
                eval_texts,
                rule.severity,
            )
        elif (
            rule.rule_type == "custom" and rule.logic or rule.rule_type == "template" and rule.logic
        ):
            gr = execute_custom_logic(
                rule.logic,
                eval_texts,
                _images,
                _tools,
                _tool_calls,
                _msgs,
                model,
                user_id,
                team_id,
                end_user_id,
                {**_meta, **rule.config},
            )
            if gr.reason and gr.reason.startswith("Execution error:"):
                error_str = gr.reason
        else:
            gr = allow()

        elapsed = (time.monotonic() - start) * 1000
        total_latency += elapsed

        entry = {
            "guardrail_id": rule.id,
            "guardrail_name": rule.name,
            "decision": gr.decision,
            "reason": gr.reason,
            "latency_ms": round(elapsed, 2),
            "modified_texts": gr.modified_texts,
            "modified_images": gr.modified_images,
            "modified_tool_calls": gr.modified_tool_calls,
            "error": error_str,
        }
        results.append(entry)

        event = GuardrailEvent(
            workspace_id=workspace_id,
            guardrail_rule_id=rule.id,
            guardrail_name=rule.name,
            mode=mode,
            decision=gr.decision,
            reason=gr.reason,
            latency_ms=round(elapsed, 2),
            request_metadata={
                "model": model,
                "user_id": user_id,
                "end_user_id": end_user_id,
            },
            gateway_request_id=gateway_request_id,
            model=model,
            user_id=user_id or end_user_id,
            error=error_str,
        )
        db.add(event)

        if gr.decision == "block":
            overall_decision = "block"
            break
        if gr.decision == "modify":
            overall_decision = "modify"
            if gr.modified_texts:
                texts = gr.modified_texts

    await db.flush()
    return overall_decision, results, round(total_latency, 2)


# ── Guardrail alert evaluation ─────────────────────────────────────────────


async def evaluate_guardrail_alerts(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    window_hours: int = 1,
    baseline_hours: int = 24,
) -> list[dict[str, Any]]:
    """
    Check guardrail metrics against thresholds and return any triggered alerts.

    Evaluates:
    - block_rate_spike: current block rate > 2x baseline block rate
    - error_rate: guardrail execution errors > 5%
    - latency_degradation: avg latency > 2x baseline latency
    """
    from datetime import timedelta  # noqa: PLC0415

    from runledger_api.models.guardrails import GuardrailAlert  # noqa: PLC0415

    now = datetime.now(UTC)
    window_start = now - timedelta(hours=window_hours)
    baseline_start = now - timedelta(hours=baseline_hours)

    # Current window stats
    cur_total_q = await db.execute(
        select(func.count(GuardrailEvent.id)).where(
            GuardrailEvent.workspace_id == workspace_id,
            GuardrailEvent.created_at >= window_start,
        )
    )
    cur_total = int(cur_total_q.scalar() or 0)

    if cur_total < 10:
        return []

    cur_blocks_q = await db.execute(
        select(func.count(GuardrailEvent.id)).where(
            GuardrailEvent.workspace_id == workspace_id,
            GuardrailEvent.created_at >= window_start,
            GuardrailEvent.decision == "block",
        )
    )
    cur_blocks = int(cur_blocks_q.scalar() or 0)

    cur_errors_q = await db.execute(
        select(func.count(GuardrailEvent.id)).where(
            GuardrailEvent.workspace_id == workspace_id,
            GuardrailEvent.created_at >= window_start,
            GuardrailEvent.error.isnot(None),
        )
    )
    cur_errors = int(cur_errors_q.scalar() or 0)

    cur_latency_q = await db.execute(
        select(func.avg(GuardrailEvent.latency_ms)).where(
            GuardrailEvent.workspace_id == workspace_id,
            GuardrailEvent.created_at >= window_start,
        )
    )
    cur_avg_latency = float(cur_latency_q.scalar() or 0)

    # Baseline stats
    base_total_q = await db.execute(
        select(func.count(GuardrailEvent.id)).where(
            GuardrailEvent.workspace_id == workspace_id,
            GuardrailEvent.created_at >= baseline_start,
            GuardrailEvent.created_at < window_start,
        )
    )
    base_total = int(base_total_q.scalar() or 0)

    base_blocks_q = await db.execute(
        select(func.count(GuardrailEvent.id)).where(
            GuardrailEvent.workspace_id == workspace_id,
            GuardrailEvent.created_at >= baseline_start,
            GuardrailEvent.created_at < window_start,
            GuardrailEvent.decision == "block",
        )
    )
    base_blocks = int(base_blocks_q.scalar() or 0)

    base_latency_q = await db.execute(
        select(func.avg(GuardrailEvent.latency_ms)).where(
            GuardrailEvent.workspace_id == workspace_id,
            GuardrailEvent.created_at >= baseline_start,
            GuardrailEvent.created_at < window_start,
        )
    )
    base_avg_latency = float(base_latency_q.scalar() or 0)

    alerts: list[dict[str, Any]] = []

    cur_block_rate = cur_blocks / cur_total if cur_total else 0
    base_block_rate = base_blocks / base_total if base_total else 0

    if base_block_rate > 0 and cur_block_rate > base_block_rate * 2:
        severity = "critical" if cur_block_rate > base_block_rate * 5 else "warning"
        alert = GuardrailAlert(
            workspace_id=workspace_id,
            alert_type="block_rate_spike",
            severity=severity,
            title=f"Block rate spike: {cur_block_rate:.1%} vs baseline {base_block_rate:.1%}",
            description=(
                f"Guardrail block rate in the last {window_hours}h is "
                f"{cur_block_rate / base_block_rate:.1f}x the {baseline_hours}h baseline."
            ),
            metric_value=cur_block_rate,
            threshold_value=base_block_rate * 2,
        )
        db.add(alert)
        alerts.append({"type": "block_rate_spike", "severity": severity, "id": alert.id})

    error_rate = cur_errors / cur_total if cur_total else 0
    if error_rate > 0.05:
        severity = "critical" if error_rate > 0.2 else "warning"
        alert = GuardrailAlert(
            workspace_id=workspace_id,
            alert_type="error_rate",
            severity=severity,
            title=f"Guardrail error rate: {error_rate:.1%}",
            description=f"{cur_errors} of {cur_total} evaluations produced errors in the last {window_hours}h.",
            metric_value=error_rate,
            threshold_value=0.05,
        )
        db.add(alert)
        alerts.append({"type": "error_rate", "severity": severity, "id": alert.id})

    if base_avg_latency > 0 and cur_avg_latency > base_avg_latency * 2:
        severity = "critical" if cur_avg_latency > base_avg_latency * 5 else "warning"
        alert = GuardrailAlert(
            workspace_id=workspace_id,
            alert_type="latency_degradation",
            severity=severity,
            title=f"Guardrail latency spike: {cur_avg_latency:.1f}ms vs baseline {base_avg_latency:.1f}ms",
            description=(
                f"Average guardrail latency in the last {window_hours}h is "
                f"{cur_avg_latency / base_avg_latency:.1f}x the {baseline_hours}h baseline."
            ),
            metric_value=cur_avg_latency,
            threshold_value=base_avg_latency * 2,
        )
        db.add(alert)
        alerts.append({"type": "latency_degradation", "severity": severity, "id": alert.id})

    if alerts:
        await db.flush()

    return alerts
