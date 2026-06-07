"""Unit tests for audit_undefined_css_vars.py"""
import unittest
import tempfile
from pathlib import Path

from scripts.audit_undefined_css_vars import (
    extract_used_vars,
    extract_defined_vars,
    categorize_undefined,
    build_report,
)


class ExtractUsedVarsTest(unittest.TestCase):
    def test_returns_dict_keyed_by_filename(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            css_dir = Path(tmpdir)
            (css_dir / "a.css").write_text(
                ".x { color: var(--c1); background: var(--c2); }",
                encoding="utf-8",
            )
            (css_dir / "b.css").write_text(
                ".y { padding: var(--p1); }",
                encoding="utf-8",
            )
            result = extract_used_vars(css_dir)
            self.assertIn("a.css", result)
            self.assertIn("b.css", result)
            self.assertEqual(result["a.css"], {"c1", "c2"})
            self.assertEqual(result["b.css"], {"p1"})

    def test_empty_css_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = extract_used_vars(Path(tmpdir))
            self.assertEqual(result, {})


class ExtractDefinedVarsTest(unittest.TestCase):
    def test_reads_tokens_file(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".css", delete=False, encoding="utf-8"
        ) as f:
            f.write(":root { --c1: red; --c2: blue; }")
            f.flush()
            tokens = Path(f.name)
        try:
            result = extract_defined_vars(tokens)
            self.assertEqual(result, {"c1", "c2"})
        finally:
            tokens.unlink()

    def test_missing_tokens_file(self):
        result = extract_defined_vars(Path("/nonexistent/tokens.css"))
        self.assertEqual(result, set())


class CategorizeUndefinedTest(unittest.TestCase):
    def test_truly_undefined(self):
        used = {"__missing__"}
        defined = set()
        file_map = {"hub.css": {"__missing__"}}
        result = categorize_undefined(used, defined, file_map, Path("/n/a"))
        self.assertEqual(len(result["truly_undefined"]), 1)
        self.assertEqual(result["truly_undefined"][0]["var"], "__missing__")

    def test_should_migrate_to_tokens(self):
        used = {"__defined__"}
        defined = {"__defined__"}
        result = categorize_undefined(used, defined, {}, Path("/n/a"))
        self.assertEqual(result["should_migrate_to_tokens"], [])


class BuildReportTest(unittest.TestCase):
    def test_report_contains_required_fields(self):
        report = build_report(
            used={"v1"},
            defined={"v1"},
            undefined_items=[],
            categories={
                "tailwind_product": 0,
                "tailwind_class_as_var": 0,
                "should_migrate_to_tokens": 0,
                "truly_undefined": 0,
            },
        )
        self.assertIn("scan_date", report)
        self.assertIn("total_refs", report)
        self.assertIn("total_defs", report)
        self.assertIn("undefined_count", report)
        self.assertIn("categories", report)
        self.assertIn("items", report)


if __name__ == "__main__":
    unittest.main()
