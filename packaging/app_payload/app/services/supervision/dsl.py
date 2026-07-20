"""S7.1 — Safe trigger DSL for ``SupervisionRule.trigger_dsl``.

Self-implemented ``ast``-based sandbox. The plan recommended against
``simpleeval`` because we want stricter node-level whitelist control
to prevent rule authors from accidentally (or maliciously) pulling in
``exec``/``eval`` or hitting module imports. The allow-list is
intentionally narrow:

  - Boolean / comparison / arithmetic ops
  - Names, attribute access, subscripts
  - Function calls (caller must put the callables into ``ctx``)
  - String / numeric / bool / None literals

Everything else (imports, comprehensions, lambdas, assignments, function
definitions, generators, starred expressions, joined strings, etc.) is
rejected with ``ValueError`` before evaluation. Reference errors during
evaluation bubble up unchanged so ``rule_engine`` can log + skip.

Uppercase keywords (``AND`` / ``OR`` / ``NOT``) are translated to
lowercase before parsing because rule authors find them more
legible in JSON-stored triggers.
"""
from __future__ import annotations

import ast
import re
from typing import Any, Mapping


_ALLOWED_NODES: tuple[type[ast.AST], ...] = (
    ast.Expression,
    ast.BoolOp, ast.And, ast.Or,
    ast.Compare,
    ast.BinOp,
    ast.UnaryOp, ast.Not, ast.USub, ast.UAdd,
    ast.Name, ast.Load,
    ast.Constant,
    ast.Call,
    ast.Attribute,
    ast.Subscript,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.In, ast.NotIn, ast.Is, ast.IsNot,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod,
    ast.Tuple, ast.List,
)


_KEYWORD_TRANSLATION = re.compile(r"\b(?:AND|OR|NOT)\b")


def _lowercase_keywords(text: str) -> str:
    return _KEYWORD_TRANSLATION.sub(lambda m: m.group(0).lower(), text)


class _DotDict:
    """Read-only wrapper that turns ``a.b.c`` lookups into dict navigation.

    ``ctx`` may be either a plain dict (subscript-only) or a nested mix
    of dicts and ``_DotDict`` instances. Attribute access falls back to
    key access on dicts so expressions like ``user.state.score`` work
    without callers having to box every layer.
    """

    __slots__ = ("_data",)

    def __init__(self, data: Mapping[str, Any]) -> None:
        object.__setattr__(self, "_data", data)

    def __getattr__(self, name: str) -> Any:
        data = object.__getattribute__(self, "_data")
        try:
            value = data[name]
        except KeyError as exc:
            raise AttributeError(name) from exc
        return _box(value)

    def __getitem__(self, key: str) -> Any:
        value = object.__getattribute__(self, "_data")[key]
        return _box(value)

    def __contains__(self, key: str) -> bool:
        return key in object.__getattribute__(self, "_data")

    def __iter__(self):
        return iter(object.__getattribute__(self, "_data"))

    def get(self, key: str, default: Any = None) -> Any:
        if key in object.__getattribute__(self, "_data"):
            return _box(object.__getattribute__(self, "_data")[key])
        return default


def _box(value: Any) -> Any:
    if isinstance(value, _DotDict):
        return value
    if isinstance(value, Mapping):
        return _DotDict(value)
    if isinstance(value, list):
        return [_box(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_box(v) for v in value)
    return value


def safe_eval(dsl: str, ctx: dict[str, Any]) -> Any:
    """Evaluate a rule trigger DSL against ``ctx`` and return the result.

    ``ctx`` may contain plain Python values, dicts (auto-boxed for
    attribute access), or already-wrapped ``_DotDict`` instances.

    Raises:
        ValueError: if the expression contains a forbidden AST node.
        AttributeError, KeyError, NameError, TypeError: bubble up from
            evaluation so the caller can log and skip the rule.
    """
    if not isinstance(dsl, str) or not dsl.strip():
        raise ValueError("DSL must be a non-empty string")
    lowered = _lowercase_keywords(dsl)
    try:
        tree = ast.parse(lowered, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"DSL syntax error: {exc.msg}") from exc
    ctx_keys = set(ctx.keys())
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise ValueError(f"Forbidden DSL node: {type(node).__name__}")
        if isinstance(node, ast.Name):
            if node.id.startswith("__") or node.id in {"__import__", "eval", "exec", "compile", "open", "globals", "locals", "getattr", "setattr", "delattr", "vars", "dir", "breakpoint"}:
                raise ValueError(f"Forbidden DSL name: {node.id}")
            if isinstance(node.ctx, ast.Load) and node.id not in ctx_keys:
                pass
    boxed_ctx = {k: _box(v) for k, v in ctx.items()}
    return eval(compile(tree, "<dsl>", "eval"), {"__builtins__": {}}, boxed_ctx)


__all__ = ["safe_eval", "_DotDict"]
