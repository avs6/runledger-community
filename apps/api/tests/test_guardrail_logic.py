"""Custom guardrail logic runs in a safe interpreter, never exec (review S-01)."""

from __future__ import annotations

import pytest
from runledger_api.services.guardrail_logic import LogicError, run_logic, validate_logic
from runledger_api.services.guardrails import (
    GUARDRAIL_TEMPLATES,
    allow,
    block,
    execute_custom_logic,
    modify,
)

HELPERS = {"allow": allow, "block": block, "modify": modify}


def _run(logic: str, texts: list[str] | None = None, **extra: object):
    return execute_custom_logic(
        logic,
        texts or [],
        [],
        [],
        [],
        [],
        "gpt-4o",
        None,
        None,
        None,
        dict(extra),
        timeout_ms=500,
    )


# ── Every built-in template is valid and runs ─────────────────────────────────


@pytest.mark.parametrize("template_id", sorted(GUARDRAIL_TEMPLATES))
def test_templates_validate_and_run(template_id: str) -> None:
    logic = GUARDRAIL_TEMPLATES[template_id]["default_logic"]
    validate_logic(logic)
    result = _run(logic, ["hello there"])
    assert result.decision in {"allow", "block", "modify"}
    assert not (result.reason or "").startswith(("Logic error", "Execution error")), result.reason


def test_pii_template_blocks_email() -> None:
    # Used "import re", which the old denylist rejected, so it never ran.
    logic = GUARDRAIL_TEMPLATES["pii_detection"]["default_logic"]
    result = _run(logic, ["mail me at jane@example.com"])
    assert result.decision == "block" and "email" in (result.reason or "")


def test_masking_template_modifies() -> None:
    logic = GUARDRAIL_TEMPLATES["financial_account_masking"]["default_logic"]
    result = _run(logic, ["account 123456789012"])
    assert result.decision == "modify"
    assert result.modified_texts == ["account [REDACTED_ACCOUNT]"]


def test_language_features() -> None:
    logic = """
words = [w.lower() for w in " ".join(texts).split() if len(w) > 2]
counts = {}
for w in words:
    counts[w] = counts.get(w, 0) + 1
top, n = sorted(counts.items(), key=None)[0] if counts else ("", 0)
score = sum(1 for w in words if w in {"refund", "cancel"})
m = re.search(r"order #(\\d+)", texts[0], re.IGNORECASE)
order = m.group(1) if m else None
msg = f"score={score} order={order}"
if score >= 2 and order:
    result = block(msg)
else:
    result = allow()
"""
    result = _run(logic, ["Please REFUND and cancel Order #42"])
    assert result.decision == "block"
    assert result.reason == "score=2 order=42"


# ── Escapes are rejected ──────────────────────────────────────────────────────

ESCAPES = [
    "().__class__.__bases__[0].__subclasses__()",
    "x = ''.__class__",
    "import os",
    "from os import system",
    "__import__('os')",
    "result = (lambda: 1)()",
    "def f():\n    pass",
    "class A:\n    pass",
    "while True:\n    pass",
    "with open('x') as f:\n    pass",
    "try:\n    pass\nexcept Exception:\n    pass",
    "texts.__len__()",
    "re.compile('x')",
    "re._compile('x', 0)",
    "getattr(texts, 'append')",
    "eval('1')",
    "global x",
    "del texts",
    "f(*texts)",
    "f(**metadata)",
    "_x = 1",
    "metadata.update({})",
    "texts.pop()",
]


@pytest.mark.parametrize("source", ESCAPES)
def test_escapes_rejected(source: str) -> None:
    with pytest.raises(LogicError):
        run_logic(source, {"texts": ["a"], "metadata": {}}, HELPERS, 500)


def test_unknown_builtins_unavailable() -> None:
    for name in ("eval", "exec", "open", "getattr", "globals", "vars", "type", "object", "print"):
        with pytest.raises(LogicError):
            run_logic(f"x = {name}", {}, HELPERS, 500)


def test_method_allowlist_is_type_specific() -> None:
    with pytest.raises(LogicError):
        run_logic("x = (1).bit_length()", {}, HELPERS, 500)
    with pytest.raises(LogicError):
        run_logic("x = metadata.items", {"metadata": 5}, HELPERS, 500)


# ── Limits ────────────────────────────────────────────────────────────────────


def test_loop_limit() -> None:
    with pytest.raises(LogicError, match="loop limit"):
        run_logic("for i in range(50000):\n    pass", {}, HELPERS, 5000)


def test_step_budget_or_timeout() -> None:
    with pytest.raises(LogicError):
        run_logic(
            "for i in range(9999):\n    for j in range(9999):\n        x = i * j",
            {},
            HELPERS,
            200,
        )


def test_memory_caps() -> None:
    with pytest.raises(LogicError, match="too large"):
        run_logic("x = 'a' * 10000000", {}, HELPERS, 500)
    with pytest.raises(LogicError, match="too large"):
        run_logic("x = [0] * 10000000", {}, HELPERS, 500)


def test_broken_rule_allows_with_reason() -> None:
    result = _run("result = block(metadata['missing'])")
    assert result.decision == "allow"
    assert (result.reason or "").startswith("Execution error")
    result = _run("import os")
    assert result.decision == "allow" and (result.reason or "").startswith("Logic error")


# ── API rejects invalid logic on save ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_rejects_unsafe_logic(authed_client) -> None:  # type: ignore[no-untyped-def]
    resp = await authed_client.post(
        "/guardrails",
        json={
            "name": "evil",
            "mode": "pre_call",
            "rule_type": "custom",
            "logic": "x = ().__class__.__bases__[0].__subclasses__()",
        },
    )
    assert resp.status_code == 422
    assert "Invalid guardrail logic" in resp.json()["detail"]


@pytest.mark.parametrize(
    "source",
    [
        "x = sum(range(10 ** 12))",
        "x = list(range(10 ** 9))",
        "x = ''.join(['a' * 900000, 'b' * 900000])",
        "x = ('a' * 900000).replace('a', 'aa')",
    ],
)
def test_builtin_work_is_bounded(source: str) -> None:
    with pytest.raises(LogicError):
        run_logic(source, {}, HELPERS, 500)


@pytest.mark.parametrize("name", ["getattr", "open", "eval", "type", "print", "vars"])
def test_forbidden_names_rejected_on_save(name: str) -> None:
    with pytest.raises(LogicError, match="not allowed"):
        validate_logic(f"x = {name}")
