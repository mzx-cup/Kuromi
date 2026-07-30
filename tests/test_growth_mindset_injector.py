# -*- coding: utf-8 -*-
"""Tests for growth mindset prompt injector."""
from app.services.persona_growth_mindset import (
    inject_growth_mindset,
    has_growth_mindset_marker,
)


def test_inject_adds_rules_to_basic_prompt():
    base = "你是星识的 AI 导师。"
    out = inject_growth_mindset(base)
    assert "成长型思维" in out
    assert "夸努力" in out or "process" in out.lower()
    assert base in out  # 原 prompt 内容保留


def test_inject_grading_scene_adds_extra():
    out = inject_growth_mindset("x", scene="grading")
    assert "评分场景额外约束" in out
    assert "下一步建议" in out


def test_inject_socratic_scene_anti_demeaning():
    out = inject_growth_mindset("x", scene="socratic")
    assert "苏格拉底追问场景额外约束" in out
    assert "你怎么没想到" in out  # 反例


def test_inject_evaluation_scene_uses_neutral_label():
    out = inject_growth_mindset("x", scene="evaluation")
    assert "待提升点" in out
    assert "差" in out or "弱" in out  # 反例中提到


def test_inject_idempotent_marker():
    out = inject_growth_mindset("x")
    assert has_growth_mindset_marker(out) is True


def test_inject_with_full_reference_includes_md_content():
    out = inject_growth_mindset("x", include_full_reference=True)
    # 完整参考包含 Dweck
    assert "Dweck" in out or "成长型思维" in out


def test_marker_detection_negative():
    assert has_growth_mindset_marker("普通 prompt") is False
