"""Unit tests for fix_p0_tech_debt.py"""
import json
import unittest
import tempfile
from pathlib import Path

from scripts.fix_p0_tech_debt import (
    extract_p0_vars,
    extract_overflow_files,
    build_tokens_appendix,
    delete_overflow_rules,
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


class DeleteOverflowRulesTest(unittest.TestCase):
    def test_removes_named_lines(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            css_file = Path(tmpdir) / "x.css"
            css_file.write_text(
                "* { box-sizing: border-box; }\n"
                ".card { padding: 16px; }\n"
                "html { font-size: 16px; }\n",
                encoding="utf-8",
            )
            # 删除第 1 行 (* rule) 和第 3 行 (html rule)
            delete_overflow_rules(css_file, {1, 3})
            content = css_file.read_text(encoding="utf-8")
            self.assertNotIn("box-sizing", content)
            self.assertIn(".card", content)
            self.assertNotIn("font-size", content)

    def test_empty_hits_no_change(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            css_file = Path(tmpdir) / "x.css"
            original = ".card { padding: 16px; }\n"
            css_file.write_text(original, encoding="utf-8")
            delete_overflow_rules(css_file, set())
            self.assertEqual(css_file.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
