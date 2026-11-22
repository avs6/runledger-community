"""Safe interpreter for custom guardrail logic (review S-01).

Custom and template guardrails are written in a small, Python-like language. They
used to run through ``exec()`` behind a regex denylist, which any attribute trick
could bypass (remote code execution in the API process). This module never calls
``exec``/``eval``: it parses the logic with ``ast`` and walks the tree itself,
supporting only what guardrails need.

Supported
  statements   assignment (names, tuple unpacking), ``+=`` style updates, if/elif/else,
               for (loop count capped), break, continue, pass, expression calls,
               ``import re`` (no-op; ``re`` is always available)
  expressions  literals, list/tuple/dict/set displays, comprehensions, f-strings,
               arithmetic, comparisons (incl. in / not in / is), and/or/not,
               conditional expressions, indexing and slicing
  functions    allow(), block(reason), modify(texts=…, images=…, tool_calls=…),
               len str int float bool list dict set tuple range enumerate zip any all
               min max sum abs sorted reversed isinstance round
  methods      str: lower upper strip lstrip rstrip split rsplit splitlines join replace
                    startswith endswith count find rfind isdigit isalpha isalnum title
                    casefold
               list: append extend index count     dict: get items keys values
               re: search match fullmatch findall sub split, flags IGNORECASE/I/MULTILINE/M
               match objects: group groups start end span

Anything else — other attributes, any dunder name, defining functions or classes,
lambda, while, with, try, global, del, star-args — is rejected when the rule is saved
(``validate_logic``) and again at run time.

Limits: a step budget, a wall-clock deadline (the rule's timeout), at most 10,000
loop iterations, ``range`` up to 100,000 items, strings up to 1 MB (``join`` and
``replace`` check the size before building) and collections up to 100,000 items.
Regex patterns are capped at 1,000 characters and their input at 200,000. Python's
``re`` can't be interrupted, so a pathological pattern written by a workspace admin
can still slow that workspace's own requests; it can't reach the host.
"""

from __future__ import annotations

import ast
import operator
import re
import time
from collections.abc import Callable, Iterable
from typing import Any

MAX_STEPS = 200_000
MAX_LOOP = 10_000
MAX_STR = 1_000_000
MAX_ITEMS = 100_000
MAX_REGEX_INPUT = 200_000
MAX_SOURCE = 20_000


class LogicError(Exception):
    """Invalid or unsafe guardrail logic, or a limit was exceeded."""


class _Break(Exception):
    pass


class _Continue(Exception):
    pass


_BIN_OPS: dict[type, Callable[[Any, Any], Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
}
_CMP_OPS: dict[type, Callable[[Any, Any], bool]] = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.In: lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
    ast.Is: operator.is_,
    ast.IsNot: operator.is_not,
}

_STR_METHODS = {
    "lower",
    "upper",
    "strip",
    "lstrip",
    "rstrip",
    "split",
    "rsplit",
    "splitlines",
    "join",
    "replace",
    "startswith",
    "endswith",
    "count",
    "find",
    "rfind",
    "isdigit",
    "isalpha",
    "isalnum",
    "title",
    "casefold",
}
_LIST_METHODS = {"append", "extend", "index", "count"}
_DICT_METHODS = {"get", "items", "keys", "values"}
_MATCH_METHODS = {"group", "groups", "start", "end", "span"}


def _cap_text(value: Any) -> Any:
    if isinstance(value, str) and len(value) > MAX_REGEX_INPUT:
        return value[:MAX_REGEX_INPUT]
    return value


def _re_call(fn: Callable[..., Any]) -> Callable[..., Any]:
    def wrapper(pattern: Any, *args: Any, **kwargs: Any) -> Any:
        if not isinstance(pattern, str) or len(pattern) > 1_000:
            raise LogicError("regex pattern must be a string of at most 1000 characters")
        return fn(pattern, *[_cap_text(a) for a in args], **kwargs)

    return wrapper


class _Re:
    """The only module guardrail logic can reach."""

    search = staticmethod(_re_call(re.search))
    match = staticmethod(_re_call(re.match))
    fullmatch = staticmethod(_re_call(re.fullmatch))
    findall = staticmethod(_re_call(re.findall))
    sub = staticmethod(_re_call(re.sub))
    split = staticmethod(_re_call(re.split))
    IGNORECASE = I = re.IGNORECASE  # noqa: E741 - mirrors re.I
    MULTILINE = M = re.MULTILINE


_RE = _Re()
_RE_ATTRS = {
    "search",
    "match",
    "fullmatch",
    "findall",
    "sub",
    "split",
    "IGNORECASE",
    "I",
    "MULTILINE",
    "M",
}


def _safe_range(*args: int) -> range:
    r = range(*args)
    if len(r) > MAX_ITEMS:
        raise LogicError(f"range is limited to {MAX_ITEMS} items")
    return r


def _safe_join(sep: str) -> Callable[[Iterable[Any]], str]:
    def join(items: Iterable[Any]) -> str:
        parts = list(items)
        if len(parts) > MAX_ITEMS:
            raise LogicError("join input too large")
        size = sum(len(p) for p in parts if isinstance(p, str)) + len(sep) * max(len(parts) - 1, 0)
        if size > MAX_STR:
            raise LogicError("string too large")
        return sep.join(parts)

    return join


def _safe_replace(text: str) -> Callable[..., str]:
    def replace(old: str, new: str, count: int = -1) -> str:
        n = text.count(old) if old else len(text) + 1
        if count >= 0:
            n = min(n, count)
        if len(text) + n * max(len(new) - len(old), 0) > MAX_STR:
            raise LogicError("string too large")
        return text.replace(old, new, count)

    return replace


_BUILTINS: dict[str, Any] = {
    "len": len,
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
    "set": set,
    "tuple": tuple,
    "range": _safe_range,
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
    "round": round,
    "True": True,
    "False": False,
    "None": None,
}

_ALLOWED_NODES: tuple[type, ...] = (
    ast.Module,
    ast.Expr,
    ast.Assign,
    ast.AugAssign,
    ast.If,
    ast.For,
    ast.Break,
    ast.Continue,
    ast.Pass,
    ast.Import,
    ast.alias,
    ast.Constant,
    ast.Name,
    ast.Load,
    ast.Store,
    ast.List,
    ast.Tuple,
    ast.Dict,
    ast.Set,
    ast.BinOp,
    ast.UnaryOp,
    ast.BoolOp,
    ast.Compare,
    ast.IfExp,
    ast.Call,
    ast.keyword,
    ast.Attribute,
    ast.Subscript,
    ast.Slice,
    ast.JoinedStr,
    ast.FormattedValue,
    ast.ListComp,
    ast.SetComp,
    ast.DictComp,
    ast.GeneratorExp,
    ast.comprehension,
    ast.And,
    ast.Or,
    ast.Not,
    ast.USub,
    ast.UAdd,
    *_BIN_OPS.keys(),
    *_CMP_OPS.keys(),
)
_ALLOWED_ATTRS = _STR_METHODS | _LIST_METHODS | _DICT_METHODS | _MATCH_METHODS | _RE_ATTRS


# Built-ins that are never available; refused at save time with a clear message.
_FORBIDDEN_NAMES = {
    "getattr",
    "setattr",
    "delattr",
    "hasattr",
    "eval",
    "exec",
    "compile",
    "open",
    "globals",
    "locals",
    "vars",
    "dir",
    "type",
    "object",
    "input",
    "print",
    "help",
    "breakpoint",
    "memoryview",
    "id",
    "super",
    "classmethod",
    "staticmethod",
    "property",
    "issubclass",
    "callable",
    "iter",
    "next",
    "format",
    "repr",
    "ascii",
    "bytes",
    "bytearray",
    "frozenset",
    "exit",
    "quit",
}


def validate_logic(source: str) -> None:
    """Raise LogicError if ``source`` uses anything outside the supported language."""
    if len(source) > MAX_SOURCE:
        raise LogicError(f"logic is longer than {MAX_SOURCE} characters")
    try:
        tree = ast.parse(source, mode="exec")
    except SyntaxError as exc:
        raise LogicError(f"syntax error on line {exc.lineno}: {exc.msg}") from exc
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise LogicError(f"{type(node).__name__} is not allowed in guardrail logic")
        if isinstance(node, ast.Name) and (node.id.startswith("_") or node.id in _FORBIDDEN_NAMES):
            raise LogicError(f"name {node.id!r} is not allowed")
        if isinstance(node, ast.Attribute) and (
            node.attr.startswith("_") or node.attr not in _ALLOWED_ATTRS
        ):
            raise LogicError(f"attribute .{node.attr} is not allowed")
        if isinstance(node, ast.Import) and any(a.name != "re" for a in node.names):
            raise LogicError("only 'import re' is allowed")
        if isinstance(node, ast.Call) and any(isinstance(a, ast.Starred) for a in node.args):
            raise LogicError("star arguments are not allowed")
        if isinstance(node, ast.keyword) and node.arg is None:
            raise LogicError("** arguments are not allowed")


class _Interpreter:
    def __init__(self, env: dict[str, Any], deadline: float) -> None:
        self.env = env
        self.deadline = deadline
        self.steps = 0

    # ── budget ──
    def _tick(self) -> None:
        self.steps += 1
        if self.steps > MAX_STEPS:
            raise LogicError("step budget exceeded")
        if self.steps % 256 == 0 and time.monotonic() > self.deadline:
            raise LogicError("timeout")

    @staticmethod
    def _check_size(value: Any) -> Any:
        if isinstance(value, str) and len(value) > MAX_STR:
            raise LogicError("string too large")
        if isinstance(value, list | tuple | set | dict) and len(value) > MAX_ITEMS:
            raise LogicError("collection too large")
        return value

    # ── statements ──
    def run(self, tree: ast.Module) -> None:
        self._block(tree.body)

    def _block(self, body: list[ast.stmt]) -> None:
        for stmt in body:
            self._stmt(stmt)

    def _stmt(self, node: ast.stmt) -> None:
        self._tick()
        if isinstance(node, ast.Expr):
            self._expr(node.value)
        elif isinstance(node, ast.Assign):
            value = self._expr(node.value)
            for target in node.targets:
                self._assign(target, value)
        elif isinstance(node, ast.AugAssign):
            if not isinstance(node.target, ast.Name):
                raise LogicError("only simple names can be updated in place")
            op = _BIN_OPS.get(type(node.op))
            if op is None:
                raise LogicError("operator not allowed")
            current = self._lookup(node.target.id)
            self.env[node.target.id] = self._check_size(op(current, self._expr(node.value)))
        elif isinstance(node, ast.If):
            self._block(node.body if self._expr(node.test) else node.orelse)
        elif isinstance(node, ast.For):
            iterable = self._iter(self._expr(node.iter))
            for i, item in enumerate(iterable):
                if i >= MAX_LOOP:
                    raise LogicError("loop limit exceeded")
                self._assign(node.target, item)
                try:
                    self._block(node.body)
                except _Break:
                    break
                except _Continue:
                    continue
            else:
                self._block(node.orelse)
        elif isinstance(node, ast.Break):
            raise _Break
        elif isinstance(node, ast.Continue):
            raise _Continue
        elif isinstance(node, ast.Pass | ast.Import):
            return
        else:
            raise LogicError(f"{type(node).__name__} is not allowed")

    def _assign(self, target: ast.expr, value: Any) -> None:
        if isinstance(target, ast.Name):
            if target.id.startswith("_"):
                raise LogicError("names starting with _ are not allowed")
            self.env[target.id] = value
        elif isinstance(target, ast.Tuple | ast.List):
            values = list(self._iter(value))
            if len(values) != len(target.elts):
                raise LogicError("unpacking length mismatch")
            for t, v in zip(target.elts, values, strict=True):
                self._assign(t, v)
        elif isinstance(target, ast.Subscript):
            container = self._expr(target.value)
            if not isinstance(container, list | dict):
                raise LogicError("only lists and dicts support item assignment")
            container[self._expr(target.slice)] = value
            self._check_size(container)
        else:
            raise LogicError("unsupported assignment target")

    def _iter(self, value: Any) -> Iterable[Any]:
        if isinstance(value, str | list | tuple | set | dict | range | enumerate | zip | reversed):
            return value  # type: ignore[return-value]
        if hasattr(value, "__iter__") and type(value).__name__ in {
            "dict_items",
            "dict_keys",
            "dict_values",
        }:
            return value  # type: ignore[no-any-return]
        raise LogicError(f"cannot iterate over {type(value).__name__}")

    def _lookup(self, name: str) -> Any:
        if name in self.env:
            return self.env[name]
        if name in _BUILTINS:
            return _BUILTINS[name]
        raise LogicError(f"name {name!r} is not defined")

    # ── expressions ──
    def _expr(self, node: ast.expr) -> Any:
        self._tick()
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return self._lookup(node.id)
        if isinstance(node, ast.List):
            return self._check_size([self._expr(e) for e in node.elts])
        if isinstance(node, ast.Tuple):
            return tuple(self._expr(e) for e in node.elts)
        if isinstance(node, ast.Set):
            return self._check_size({self._expr(e) for e in node.elts})
        if isinstance(node, ast.Dict):
            return self._check_size(
                {
                    self._expr(k): self._expr(v)
                    for k, v in zip(node.keys, node.values, strict=True)
                    if k is not None
                }
            )
        if isinstance(node, ast.BinOp):
            op = _BIN_OPS.get(type(node.op))
            if op is None:
                raise LogicError("operator not allowed")
            left, right = self._expr(node.left), self._expr(node.right)
            if isinstance(node.op, ast.Mult) and (
                isinstance(left, str | list | tuple) or isinstance(right, str | list | tuple)
            ):
                size = len(left) if isinstance(left, str | list | tuple) else len(right)
                factor = right if isinstance(right, int) else left
                if isinstance(factor, int) and size * max(factor, 0) > MAX_STR:
                    raise LogicError("result too large")
            return self._check_size(op(left, right))
        if isinstance(node, ast.UnaryOp):
            value = self._expr(node.operand)
            if isinstance(node.op, ast.Not):
                return not value
            if isinstance(node.op, ast.USub):
                return -value
            if isinstance(node.op, ast.UAdd):
                return +value
            raise LogicError("operator not allowed")
        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                result: Any = True
                for v in node.values:
                    result = self._expr(v)
                    if not result:
                        return result
                return result
            result = False
            for v in node.values:
                result = self._expr(v)
                if result:
                    return result
            return result
        if isinstance(node, ast.Compare):
            left = self._expr(node.left)
            for op_node, comp in zip(node.ops, node.comparators, strict=True):
                right = self._expr(comp)
                fn = _CMP_OPS.get(type(op_node))
                if fn is None:
                    raise LogicError("comparison not allowed")
                if not fn(left, right):
                    return False
                left = right
            return True
        if isinstance(node, ast.IfExp):
            return self._expr(node.body) if self._expr(node.test) else self._expr(node.orelse)
        if isinstance(node, ast.Subscript):
            container = self._expr(node.value)
            if not isinstance(container, str | list | tuple | dict):
                raise LogicError(f"cannot index {type(container).__name__}")
            if isinstance(node.slice, ast.Slice):
                sl = slice(
                    self._expr(node.slice.lower) if node.slice.lower else None,
                    self._expr(node.slice.upper) if node.slice.upper else None,
                    self._expr(node.slice.step) if node.slice.step else None,
                )
                return container[sl]  # type: ignore[index]
            return container[self._expr(node.slice)]
        if isinstance(node, ast.JoinedStr):
            parts = []
            for v in node.values:
                if isinstance(v, ast.Constant):
                    parts.append(str(v.value))
                elif isinstance(v, ast.FormattedValue):
                    value = self._expr(v.value)
                    spec = self._expr(v.format_spec) if v.format_spec else ""
                    parts.append(format(value, spec))
            return self._check_size("".join(parts))
        if isinstance(node, ast.Attribute):
            return self._attribute(self._expr(node.value), node.attr)
        if isinstance(node, ast.Call):
            fn = self._expr(node.func)
            args = [self._expr(a) for a in node.args]
            kwargs = {k.arg: self._expr(k.value) for k in node.keywords if k.arg}
            if not callable(fn):
                raise LogicError("not callable")
            return self._check_size(fn(*args, **kwargs))
        if isinstance(node, ast.ListComp | ast.SetComp | ast.GeneratorExp):
            items = list(self._comprehension(node.generators, lambda: self._expr(node.elt)))
            if isinstance(node, ast.SetComp):
                return self._check_size(set(items))
            return self._check_size(items)
        if isinstance(node, ast.DictComp):
            pairs = list(
                self._comprehension(
                    node.generators, lambda: (self._expr(node.key), self._expr(node.value))
                )
            )
            return self._check_size(dict(pairs))
        raise LogicError(f"{type(node).__name__} is not allowed")

    def _comprehension(
        self, generators: list[ast.comprehension], produce: Callable[[], Any]
    ) -> Iterable[Any]:
        saved = dict(self.env)
        out: list[Any] = []

        def loop(i: int) -> None:
            if i == len(generators):
                out.append(produce())
                if len(out) > MAX_ITEMS:
                    raise LogicError("comprehension too large")
                return
            gen = generators[i]
            for n, item in enumerate(self._iter(self._expr(gen.iter))):
                if n >= MAX_LOOP:
                    raise LogicError("loop limit exceeded")
                self._assign(gen.target, item)
                if all(self._expr(cond) for cond in gen.ifs):
                    loop(i + 1)

        try:
            loop(0)
        finally:
            # comprehension variables don't leak (as in Python 3)
            for k in list(self.env):
                if k not in saved:
                    del self.env[k]
            self.env.update({k: v for k, v in saved.items()})
        return out

    @staticmethod
    def _attribute(obj: Any, name: str) -> Any:
        if name.startswith("_"):
            raise LogicError("attribute not allowed")
        if obj is _RE and name in _RE_ATTRS:
            return getattr(_RE, name)
        if isinstance(obj, str) and name in _STR_METHODS:
            if name == "join":
                return _safe_join(obj)
            if name == "replace":
                return _safe_replace(obj)
            return getattr(obj, name)
        if isinstance(obj, list) and name in _LIST_METHODS:
            return getattr(obj, name)
        if isinstance(obj, dict) and name in _DICT_METHODS:
            return getattr(obj, name)
        if isinstance(obj, re.Match) and name in _MATCH_METHODS:
            return getattr(obj, name)
        raise LogicError(f".{name} is not allowed on {type(obj).__name__}")


def run_logic(
    source: str, inputs: dict[str, Any], helpers: dict[str, Any], timeout_ms: float
) -> Any:
    """Run guardrail logic and return the value it assigned to ``result``."""
    validate_logic(source)
    env: dict[str, Any] = {**helpers, **inputs, "re": _RE}
    interp = _Interpreter(env, deadline=time.monotonic() + max(timeout_ms, 1) / 1000)
    interp.run(ast.parse(source, mode="exec"))
    return env.get("result")
