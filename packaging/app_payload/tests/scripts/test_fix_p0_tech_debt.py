"""Unit tests for fix_p0_tech_debt.py"""
import json
import unittest
import tempfile
from pathlib import Path

from scripts.fix_p0_tech_debt import (
    extract_p0_vars,
    extract_overflow_files,
    build_tokens_appendix,
    delete_overflow_rule,
)


class ExtractP0VarsTest(unittest.TestCase):
    def test_filters_truly_undefined(self):
        data = {
            "items": [
                {"var": "a", "category": "truly_undefined"},
                {"var": "b", "category": "tailwind_product"},
                {"var": "c", "category": "truly_undefined"},
            ]
        }
        result = extract_p0_vars(data)
        self.assertEqual(result, ["a", "c"])

    def test_empty(self):
        self.assertEqual(extract_p0_vars({}), [])
        self.assertEqual(extract_p0_vars({"items": []}), [])


class ExtractOverflowFilesTest(unittest.TestCase):
    def test_filters_non_allowed(self):
        data = {
            "offending_files": [
                {"file": "app-base.css", "allowed": True, "hits": []},
                {"file": "hub.css", "allowed": False, "hits": [{"line": 1}]},
            ]
        }
        result = extract_overflow_files(data)
        self.assertEqual(result, {"hub.css": [{"line": 1}]})


class BuildTokensAppendixTest(unittest.TestCase):
    def test_generates_sorted_var_definitions(self):
        vars_list = ["zeta-color", "alpha-color"]
        appendix = build_tokens_appendix(vars_list)
        # alpha 应在 zeta 之前 (按字母)
        self.assertLess(
            appendix.index("--alpha-color"),
            appendix.index("--zeta-color"),
        )

    def test_includes_p0_marker_comment(self):
        appendix = build_tokens_appendix(["test-var"])
        self.assertIn("P0 fix", appendix)
        self.assertIn(":root", appendix)
        self.assertIn("--test-var:", appendix)

    def test_fallback_var_gets_todo_comment(self):
        # "unknown-xyz-thing" 是 fallback
        appendix = build_tokens_appendix(["unknown-xyz-thing"])
        self.assertIn("TODO: refine color", appendix)


class DeleteOverflowRuleTest(unittest.TestCase):
    def test_deletes_single_line_rule(self):
        """单行选择器规则完整删除（选择器+body+闭合大括号）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            css_file = Path(tmpdir) / "x.css"
            css_file.write_text(
                "* { box-sizing: border-box; }\n"
                ".card { padding: 16px; }\n",
                encoding="utf-8",
            )
            n = delete_overflow_rule(css_file, 1, "*")
            self.assertEqual(n, 1)
            content = css_file.read_text(encoding="utf-8")
            self.assertNotIn("box-sizing", content)
            self.assertIn(".card", content)
            self.assertEqual(content.count("{"), content.count("}"))

    def test_deletes_multi_line_selector_with_body(self):
        """多行选择器 '*::before,\n  *::after' 整块删除（包括 @media 内的 body 和 }）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            css_file = Path(tmpdir) / "x.css"
            css_file.write_text(
                "@media (prefers-reduced-motion: reduce) {\n"
                "  *::before,\n"
                "  *::after {\n"
                "    animation-duration: 0.01ms !important;\n"
                "    transition-duration: 0.01ms !important;\n"
                "  }\n"
                "  .other { display: none; }\n"
                "}\n",
                encoding="utf-8",
            )
            # 选择器在 line 2 (1-indexed)，跨 2 行
            n = delete_overflow_rule(css_file, 2, "*::before,\n  *::after")
            self.assertEqual(n, 5)  # lines 2-6 (selector+body+})
            content = css_file.read_text(encoding="utf-8")
            self.assertNotIn("animation-duration", content)
            self.assertNotIn("*::before", content)
            self.assertIn(".other", content)
            self.assertIn("@media", content)
            self.assertEqual(content.count("{"), content.count("}"))

    def test_brace_count_stays_balanced(self):
        """删除 html, body 规则后 brace count 仍平衡"""
        with tempfile.TemporaryDirectory() as tmpdir:
            css_file = Path(tmpdir) / "x.css"
            css_file.write_text(
                "html, body {\n"
                "    height: 100%;\n"
                "    margin: 0;\n"
                "    overflow: hidden;\n"
                "}\n",
                encoding="utf-8",
            )
            n = delete_overflow_rule(css_file, 1, "html, body")
            self.assertEqual(n, 5)
            content = css_file.read_text(encoding="utf-8")
            self.assertEqual(content.count("{"), content.count("}"))
            self.assertEqual(content.count("{"), 0)
            self.assertEqual(content, "")

    def test_invalid_line_returns_zero(self):
        """越界行号返回 0，文件不变"""
        with tempfile.TemporaryDirectory() as tmpdir:
            css_file = Path(tmpdir) / "x.css"
            original = ".card { padding: 16px; }\n"
            css_file.write_text(original, encoding="utf-8")
            n = delete_overflow_rule(css_file, 99, "nonexistent")
            self.assertEqual(n, 0)
            self.assertEqual(css_file.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
