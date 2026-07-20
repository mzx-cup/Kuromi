"""Unit tests for inference_rules.py"""
import unittest

from scripts.inference_rules import (
    COLOR_NAMES,
    ROLE_COLORS,
    FALLBACK_COLOR,
    infer_value,
)


class ColorNamesTest(unittest.TestCase):
    def test_contains_common_colors(self):
        for name in ("amber", "rose", "violet", "teal", "blue"):
            self.assertIn(name, COLOR_NAMES)
            self.assertTrue(COLOR_NAMES[name].startswith("#"))

    def test_all_values_are_3_or_6_digit_hex(self):
        for k, v in COLOR_NAMES.items():
            self.assertRegex(v, r"^#[0-9a-fA-F]{6}$", f"{k}={v} not 6-digit hex")


class RoleColorsTest(unittest.TestCase):
    def test_contains_expected_roles(self):
        for role in ("agent", "moderator", "student", "teacher"):
            self.assertIn(role, ROLE_COLORS)


class FallbackColorTest(unittest.TestCase):
    def test_is_valid_hex(self):
        self.assertRegex(FALLBACK_COLOR, r"^#[0-9a-fA-F]{6}$")


class InferValueTest(unittest.TestCase):
    def test_color_token_in_name(self):
        # "accent-amber" 中含 "amber"
        value, source = infer_value("accent-amber")
        self.assertEqual(value, "#f59e0b")
        self.assertEqual(source, "mapped")

    def test_role_in_avatar_gradient(self):
        value, source = infer_value("avatar-gradient-student")
        self.assertEqual(value, "#3b82f6")
        self.assertEqual(source, "role")

    def test_unknown_returns_fallback(self):
        value, source = infer_value("totally-unknown-thing-xyz")
        self.assertEqual(value, FALLBACK_COLOR)
        self.assertEqual(source, "fallback")

    def test_multiple_tokens_first_match_wins(self):
        # "agent-color" — 没有直接 color token，但 "agent" 也不是颜色
        # 期望: 走 fallback (因为不是 avatar-gradient-)
        value, source = infer_value("agent-color")
        # 取决于优先级: 先 COLOR_NAMES 还是先 ROLE 路径
        # 实际: 拆 token 后没有匹配 color，role 路径不匹配前缀
        # 所以 fallback
        self.assertEqual(source, "fallback")

    def test_case_sensitive_tokens(self):
        # 推断按小写 token 匹配
        value, source = infer_value("accent-AMBER")
        # "AMBER" 不会匹配 (COLOR_NAMES["amber"] 小写)
        self.assertEqual(source, "fallback")


if __name__ == "__main__":
    unittest.main()
