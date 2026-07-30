# -*- coding: utf-8 -*-
"""Tests for variant question generator."""
from app.services.agent.variant_question_generator import (
    VariantDimension,
    VariantQuestionGenerator,
    get_variant_generator,
)


def test_surface_swap_numbers():
    gen = VariantQuestionGenerator()
    original = {"stem": "小明有 3 个苹果,妈妈又给他 2 个,现在有几个?", "answer": "5"}
    variants = gen.generate(original, n=3, dimension=VariantDimension.SURFACE)
    assert len(variants) >= 1
    # 数字应当被替换(不能都是 3 / 2)
    has_change = any("3" not in v.stem[:10] for v in variants)
    # 至少部分变式数字有变化
    assert all(v.dimension == VariantDimension.SURFACE for v in variants)


def test_scenario_swap_addition():
    gen = VariantQuestionGenerator()
    original = {"stem": "小明有 3 个苹果,妈妈又给他 2 个,现在有几个?", "answer": "5"}
    variants = gen.generate(
        original, knowledge_point="加法", n=3, dimension=VariantDimension.SCENARIO
    )
    assert len(variants) >= 1
    # 应当包含"场景"标签
    assert any("【场景" in v.stem for v in variants)


def test_scenario_swap_deduction():
    gen = VariantQuestionGenerator()
    original = {"stem": "小明有 5 个苹果,吃掉了 2 个,还剩几个?", "answer": "3"}
    variants = gen.generate(
        original, knowledge_point="减法", n=3, dimension=VariantDimension.SCENARIO
    )
    assert len(variants) >= 1


def test_constraint_adds_extra_condition():
    gen = VariantQuestionGenerator()
    original = {"stem": "小明有 3 个苹果,妈妈又给他 2 个,现在有几个?", "answer": "5"}
    variants = gen.generate(
        original, n=3, dimension=VariantDimension.CONSTRAINT
    )
    assert len(variants) == 3
    assert all("（附加:" in v.stem for v in variants)


def test_angle_uses_open_questions():
    gen = VariantQuestionGenerator()
    original = {"stem": "求 x + 2 = 5 的解", "answer": "3"}
    variants = gen.generate(
        original, knowledge_point="一元一次方程", n=3, dimension=VariantDimension.ANGLE
    )
    assert len(variants) == 3
    # angle 维度的答案是开放性的
    assert all("开放性" in v.answer for v in variants)


def test_dedup_against_original():
    gen = VariantQuestionGenerator()
    original = {"stem": "测试题目,完全没有数字 12345", "answer": "X"}
    variants = gen.generate(original, n=5, dimension=VariantDimension.SURFACE)
    # 不能有变式与原题完全一样
    assert all(v.stem != original["stem"] for v in variants)


def test_empty_stem_returns_empty():
    gen = VariantQuestionGenerator()
    variants = gen.generate({"stem": "", "answer": ""}, n=3)
    assert variants == []


def test_invalid_dimension_string_defaults_to_surface():
    gen = VariantQuestionGenerator()
    original = {"stem": "小明有 3 个苹果", "answer": "3"}
    variants = gen.generate(original, n=2, dimension="bogus_dimension")
    assert all(v.dimension == VariantDimension.SURFACE for v in variants)


def test_to_dict_format():
    gen = VariantQuestionGenerator()
    v = gen.generate(
        {"stem": "1+1=?", "answer": "2"}, n=1, dimension=VariantDimension.SURFACE
    )[0]
    d = v.to_dict()
    assert "stem" in d
    assert "answer" in d
    assert "dimension" in d
    assert "similarity" in d
    assert 0.0 <= d["similarity"] <= 1.0


def test_singleton():
    a = get_variant_generator()
    b = get_variant_generator()
    assert a is b


def test_dimension_enum_values():
    assert VariantDimension.SURFACE.value == "surface"
    assert VariantDimension.SCENARIO.value == "scenario"
    assert VariantDimension.CONSTRAINT.value == "constraint"
    assert VariantDimension.ANGLE.value == "angle"
