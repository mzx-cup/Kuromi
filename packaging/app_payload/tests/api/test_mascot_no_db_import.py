"""Static check: mascot.py must not directly import db.py.

This is a quick regression guard. The actual functional tests live in
tests/api/test_mascot_endpoints.py.
"""
import subprocess
from pathlib import Path


def test_mascot_py_has_no_db_import():
    src = Path("app/api/mascot.py").read_text(encoding="utf-8")
    forbidden = ["from db import", "import db"]
    for pat in forbidden:
        assert pat not in src, f"Found forbidden pattern '{pat}' in mascot.py"


def test_grep_db_import_count_is_zero():
    """Grep the file and count occurrences."""
    result = subprocess.run(
        ["grep", "-c", "from db import", "app/api/mascot.py"],
        capture_output=True, text=True,
    )
    count = int(result.stdout.strip() or "0")
    assert count == 0, f"Expected 0 'from db import' in mascot.py, found {count}"
