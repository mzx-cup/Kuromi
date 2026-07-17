"""S7.1 — safe DSL parser tests (L3 supervision layer).

The DSL parser is a self-implemented ``ast``-based sandbox that lets
ops authors write rule triggers like:
    user.state.weakness.score < 0.4 AND NOT cooldown_active("SUP-014")

Only safe AST nodes are allowed; anything else (imports, lambdas,
comprehensions, function defs) raises ``ValueError``. Unknown attribute
or name references raise the natural ``AttributeError`` /
``KeyError`` — the caller catches and skips the rule.
"""
from __future__ import annotations

import pytest

from app.services.supervision import dsl


def test_dsl_simple_comparison():
    ctx = {"user": {"state": {"weakness": {"score": 0.3}}}}
    assert dsl.safe_eval("user.state.weakness.score < 0.4", ctx) is True
    assert dsl.safe_eval("user.state.weakness.score < 0.2", ctx) is False


def test_dsl_and_or_not():
    ctx = {"A": True, "B": True, "C": False}
    assert dsl.safe_eval("A AND B AND NOT C", ctx) is True
    assert dsl.safe_eval("A AND B AND C", ctx) is False
    assert dsl.safe_eval("A OR C", ctx) is True
    assert dsl.safe_eval("(A OR B) AND NOT C", ctx) is True


def test_dsl_unknown_field_raises_safe_skip():
    """Unknown attribute / name references must raise so caller can skip."""
    ctx = {"user": {"state": {}}}
    with pytest.raises(AttributeError):
        dsl.safe_eval("user.state.missing_field > 0", ctx)
    with pytest.raises(NameError):
        dsl.safe_eval("nonexistent_var > 0", ctx)


def test_dsl_arithmetic_in_field_path():
    assert dsl.safe_eval("x + 1 == 5", {"x": 4}) is True
    assert dsl.safe_eval("x * 2 + 1", {"x": 3}) == 7
    assert dsl.safe_eval("(x - 3) * 2 == 4", {"x": 5}) is True


def test_dsl_string_literal_match():
    assert dsl.safe_eval('name == "alice"', {"name": "alice"}) is True
    assert dsl.safe_eval('name != "bob"', {"name": "alice"}) is True


def test_dsl_forbidden_node_raises():
    """``__import__`` and other non-allowed nodes must raise ValueError."""
    with pytest.raises(ValueError):
        dsl.safe_eval('__import__("os")', {})
    # Comprehensions are not in the allowed set:
    with pytest.raises(ValueError):
        dsl.safe_eval("[x for x in [1,2,3]]", {})
    # Function definitions are not allowed:
    with pytest.raises(ValueError):
        dsl.safe_eval("def f(): return 1", {})


def test_dsl_nested_call():
    """Call is allowed so cooldown_active(...) style works."""
    calls = []

    def cooldown_active(rule_id):
        calls.append(rule_id)
        return True

    ctx = {"cooldown_active": cooldown_active, "rule_id_var": "SUP-014"}
    assert dsl.safe_eval('cooldown_active(rule_id_var)', ctx) is True
    assert calls == ["SUP-014"]
    assert dsl.safe_eval('cooldown_active("SUP-001")', ctx) is True
    assert calls == ["SUP-014", "SUP-001"]
