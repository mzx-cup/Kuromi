"""Unit tests for audit_compound_selectors.py"""
import unittest
import tempfile
from pathlib import Path

from scripts.audit_compound_selectors import (
    find_compound_selectors,
    build_report,
)


class FindCompoundSelectorsTest(unittest.TestCase):
    def test_detects_universal_selector(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            css_dir = Path(tmpdir)
            (css_dir / "x.css").write_text(
                "* { box-sizing: border-box; }\n.leaf { color: green; }",
                encoding="utf-8",
            )
            results = find_compound_selectors(css_dir)
            self.assertIn("x.css", results)
            hits = results["x.css"]
            self.assertGreater(len(hits), 0)
            self.assertEqual(hits[0]["selector"], "*")
            self.assertEqual(hits[0]["line"], 1)

    def test_detects_compound_universal_with_pseudo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            css_dir = Path(tmpdir)
            (css_dir / "y.css").write_text(
                "*, *::before, *::after { box-sizing: inherit; }",
                encoding="utf-8",
            )
            results = find_compound_selectors(css_dir)
            hits = results["y.css"]
            self.assertGreater(len(hits), 0)
            # 至少要捕获到 * 部分
            self.assertTrue(any(h["selector"].startswith("*") for h in hits))

    def test_detects_body_selector(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            css_dir = Path(tmpdir)
            (css_dir / "z.css").write_text(
                "body { margin: 0; }",
                encoding="utf-8",
            )
            results = find_compound_selectors(css_dir)
            hits = results["z.css"]
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]["selector"], "body")

    def test_ignores_safe_selectors(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            css_dir = Path(tmpdir)
            (css_dir / "safe.css").write_text(
                ".card { padding: 16px; }\n#header { z-index: 10; }",
                encoding="utf-8",
            )
            results = find_compound_selectors(css_dir)
            self.assertEqual(results["safe.css"], [])


class BuildReportTest(unittest.TestCase):
    def test_report_structure(self):
        report = build_report(
            findings={"x.css": [{"line": 1, "selector": "*", "context": "* {}"}]},
            total_files=5,
        )
        self.assertIn("scan_date", report)
        self.assertIn("total_files", report)
        self.assertIn("offending_files", report)
        self.assertEqual(report["total_files"], 5)
        self.assertEqual(len(report["offending_files"]), 1)


if __name__ == "__main__":
    unittest.main()
