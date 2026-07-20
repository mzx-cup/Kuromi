# -*- coding: utf-8 -*-
"""Tests for persona_socratic_rules.build_socratic_rules."""

from app.services.persona_socratic_rules import build_socratic_rules


def test_intensity_zero_no_socratic():
    rules = build_socratic_rules(0.0)
    assert "不" in rules
    assert "为什么这样想" in rules  # 禁用的反问举例


def test_intensity_low_almost_no_socratic():
    rules = build_socratic_rules(0.1)
    assert "99%" in rules or "几乎" in rules


def test_intensity_mid_gentle_socratic():
    rules = build_socratic_rules(0.4)
    assert "温和" in rules or "30%" in rules


def test_intensity_high_advanced_socratic():
    rules = build_socratic_rules(0.7)
    assert "30-50%" in rules or "进阶" in rules


def test_intensity_full_pure_socratic():
    rules = build_socratic_rules(1.0)
    assert "60%" in rules
    assert "纯苏格拉底" in rules
