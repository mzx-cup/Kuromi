"""Unit tests for audit_frontend_smells.py"""
import unittest
import tempfile
from pathlib import Path

from scripts.audit_frontend_smells import (
    detect_inline_styles,
    detect_inline_event_handlers,
    detect_oversized_files,
    detect_magic_numbers,
    detect_console_logs,
    detect_todo_comments,
    build_report,
)


class InlineStylesTest(unittest.TestCase):
    def test_detects_style_attribute(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            html_dir = Path(tmpdir)
            (html_dir / "x.html").write_text(
                '<div style="color: red">x</div>',
                encoding="utf-8",
            )
            results = detect_inline_styles(html_dir)
            self.assertIn("x.html", results)
            self.assertEqual(len(results["x.html"]), 1)
            self.assertIn('style="color: red"', results["x.html"][0]["match"])


class InlineEventHandlersTest(unittest.TestCase):
    def test_detects_onclick(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            html_dir = Path(tmpdir)
            (html_dir / "y.html").write_text(
                '<button onclick="doIt()">Click</button>',
                encoding="utf-8",
            )
            results = detect_inline_event_handlers(html_dir)
            self.assertIn("y.html", results)
            self.assertEqual(len(results["y.html"]), 1)


class OversizedFilesTest(unittest.TestCase):
    def test_detects_large_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            js_dir = Path(tmpdir)
            big = js_dir / "big.js"
            # 写入 1100 行
            big.write_text("\n".join(["// line"] * 1100), encoding="utf-8")
            results = detect_oversized_files(js_dir, threshold_lines=1000)
            # 函数返回 list[dict], 验证 big.js 出现在 results 中
            self.assertTrue(any(r["file"] == "big.js" for r in results))
            big_entry = next(r for r in results if r["file"] == "big.js")
            self.assertEqual(big_entry["lines"], 1100)


class MagicNumbersTest(unittest.TestCase):
    def test_detects_hex_color(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            css_dir = Path(tmpdir)
            (css_dir / "a.css").write_text(
                ".x { color: #a855f7; padding: 16px; }",
                encoding="utf-8",
            )
            results = detect_magic_numbers(css_dir)
            # 至少捕获到 #a855f7
            self.assertTrue(any("#a855f7" in r["match"] for r in results))


class ConsoleLogTest(unittest.TestCase):
    def test_detects_console_log(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            js_dir = Path(tmpdir)
            (js_dir / "app.js").write_text(
                "function init() {\n  console.log('debug');\n}",
                encoding="utf-8",
            )
            results = detect_console_logs(js_dir)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["file"], "app.js")
            self.assertEqual(results[0]["line"], 2)


class TodoCommentTest(unittest.TestCase):
    def test_detects_todo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "a.js").write_text(
                "// TODO: refactor this\nconst x = 1;",
                encoding="utf-8",
            )
            results = detect_todo_comments(base, base)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["keyword"], "TODO")


class BuildReportTest(unittest.TestCase):
    def test_report_structure(self):
        report = build_report(
            inline_styles={},
            inline_events={},
            oversized=[],
            magic_numbers=[],
            console_logs=[],
            todos=[],
        )
        for key in (
            "scan_date",
            "inline_styles",
            "inline_events",
            "oversized_files",
            "magic_numbers",
            "console_logs",
            "todo_comments",
        ):
            self.assertIn(key, report)


if __name__ == "__main__":
    unittest.main()
