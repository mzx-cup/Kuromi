"""Tests for VariantGenerator (M5.3)."""
from __future__ import annotations

import pytest


def test_generator_produces_three_variants():
    """默认 count=3 必须输出 3 个 variant，且 stem 不同、answer 不变。"""
    from app.services.exercise.variant_generator import VariantGenerator

    gen = VariantGenerator()
    base = {
        "id": "ex_1",
        "stem": "求 2 + 3 = ?",
        "answer": 5,
        "knowledge_point": "加法",
        "scenario": "水果",
    }
    variants = gen.generate(base, count=3)
    assert len(variants) == 3
    for v in variants:
        assert v["stem"] != base["stem"]
        assert v["answer"] == base["answer"]
        assert v["knowledge_point"] == base["knowledge_point"]
        assert v["is_variant"] is True
        assert v["parent_id"] == "ex_1"


def test_generator_changes_scenario_not_answer():
    """换情境不换答案。"""
    from app.services.exercise.variant_generator import VariantGenerator

    gen = VariantGenerator()
    base = {"stem": "2+3=?", "answer": 5, "scenario": "水果"}
    v = gen.generate(base, count=1)[0]
    assert v["scenario"] != base["scenario"]
    assert v["answer"] == 5


def test_generator_handles_missing_scenario():
    """base 没 scenario 时也能工作。"""
    from app.services.exercise.variant_generator import VariantGenerator

    gen = VariantGenerator()
    variants = gen.generate({"id": "ex_2", "stem": "1+1=?", "answer": 2, "knowledge_point": "加法"}, count=2)
    assert len(variants) == 2
    for v in variants:
        assert "scenario" in v


def test_generator_handles_count_one():
    """count=1 时输出 1 条。"""
    from app.services.exercise.variant_generator import VariantGenerator

    gen = VariantGenerator()
    variants = gen.generate({"id": "ex_3", "stem": "?", "answer": "x", "knowledge_point": "k"}, count=1)
    assert len(variants) == 1