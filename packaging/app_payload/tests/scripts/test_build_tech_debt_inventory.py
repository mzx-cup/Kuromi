"""Unit tests for build_tech_debt_inventory.py"""
import sys
import unittest
import tempfile
from pathlib import Path
from datetime import date

from scripts.build_tech_debt_inventory import (
    load_json,
    run_legacy_script,
    merge_findings,
    prioritize,
    render_markdown,
)


class LoadJsonTest(unittest.TestCase):
    def test_loads_valid_json(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            f.write('{"a": 1}')
            f.flush()
            data = load_json(Path(f.name))
            self.assertEqual(data, {"a": 1})

    def test_missing_file_returns_none(self):
        data = load_json(Path("/nonexistent/file.json"))
        self.assertIsNone(data)


class RunLegacyScriptTest(unittest.TestCase):
    def test_captures_stdout(self):
        # 调用 python -c 模拟一个简单脚本
        result = run_legacy_script(
            [sys.executable, "-c", "print('hello')"],
            cwd=Path.cwd(),
        )
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("hello", result["stdout"])


class MergeFindingsTest(unittest.TestCase):
    def test_merges_three_new_scripts(self):
        new_data = [
            {
                "categories": {"truly_undefined": 2, "tailwind_product": 5},
                "items": [{"var": "--x", "category": "truly_undefined"}],
            },
            {"offending_files": [{"file": "a.css", "hits": []}]},
            {"inline_styles": {"x.html": []}, "console_logs": []},
        ]
        merged = merge_findings(new_data, [])
        self.assertIn("undefined_vars", merged)
        self.assertIn("compound_selectors", merged)
        self.assertIn("smells", merged)


class PrioritizeTest(unittest.TestCase):
    def test_truly_undefined_is_p0(self):
        items = [{"category": "truly_undefined", "var": "--x"}]
        result = prioritize(items, source="undefined_vars")
        self.assertEqual(result[0]["priority"], "P0")

    def test_compound_in_non_allowed_file_is_p0(self):
        items = [{"file": "plant.css", "allowed": False, "hits": []}]
        result = prioritize(items, source="compound_selectors")
        self.assertEqual(result[0]["priority"], "P0")

    def test_console_log_is_p2(self):
        items = [{"file": "x.js", "line": 1}]
        result = prioritize(items, source="console_logs")
        self.assertEqual(result[0]["priority"], "P2")

    def test_todo_is_p3(self):
        items = [{"file": "x.js", "line": 1, "keyword": "TODO"}]
        result = prioritize(items, source="todo_comments")
        self.assertEqual(result[0]["priority"], "P3")


class RenderMarkdownTest(unittest.TestCase):
    def test_contains_overview_section(self):
        merged = {
            "undefined_vars": [],
            "compound_selectors": [],
            "smells": [],
            "totals": {"P0": 0, "P1": 0, "P2": 0, "P3": 0},
        }
        md = render_markdown(merged, date(2026, 6, 8))
        self.assertIn("# 前端技术债清单", md)
        self.assertIn("## 概览", md)
        self.assertIn("## 报告遗留问题解决状态", md)

    def test_contains_legacy_status_block(self):
        merged = {
            "undefined_vars": [],
            "compound_selectors": [],
            "smells": [],
            "totals": {"P0": 0, "P1": 0, "P2": 0, "P3": 0},
        }
        md = render_markdown(merged, date(2026, 6, 8))
        self.assertIn("[x] 报告遗留 1", md)
        self.assertIn("[x] 报告遗留 2", md)
        self.assertIn("[x] 报告遗留 3", md)


if __name__ == "__main__":
    unittest.main()
