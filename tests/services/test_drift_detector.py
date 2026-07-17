"""Tests for the S8 drift detection subsystem (slice-B2).

Four required cases per the plan:

* test_file_hash_mtime_newer_triggers_drift — detector flags KB nodes
  whose source file's mtime is newer than ``since``.
* test_ttl_drift_after_90d                  — semantic-memory entries
  older than the TTL window get flagged.
* test_adr_frontmatter_parses               — frontmatter round-trips.
* test_ci_daily_run_no_errors               — CLI script imports cleanly
  and is invocable through argparse without touching the real DB.

Pure-data tests (1, 2, 3) need no fixtures. The smoke test deliberately
avoids running the real ``main`` so it stays hermetic under the
``tests/services/`` pytest target.
"""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from app.services.drift.adr_parser import parse_adr
from app.services.drift.detector import (
    Drift,
    detect_file_hash_drift,
    detect_ttl_drift,
)


def test_file_hash_mtime_newer_triggers_drift():
    """A KB node whose source file's mtime is newer than ``since`` must
    be reported as a ``file_hash`` drift."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        src = tmp_path / "src.py"
        src.write_text("print('x')")
        # Force mtime to 1h ago, then ask the detector for a 2h lookback
        # window — the 1h-ago mtime falls inside the window and must
        # be flagged.
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        ts = one_hour_ago.timestamp()
        os.utime(src, (ts, ts))

        kb_index = {"K1": {"source_reference": f"file:{src.name}"}}
        since = datetime.utcnow() - timedelta(hours=2)

        drifts = list(detect_file_hash_drift(
            project_root=tmp,
            kb_index=kb_index,
            since=since,
        ))

    assert len(drifts) == 1
    assert isinstance(drifts[0], Drift)
    assert drifts[0].kb_node_id == "K1"
    assert drifts[0].drift_kind == "file_hash"
    assert drifts[0].source_ref.endswith("src.py")


def test_ttl_drift_after_90d():
    """A semantic row reinforced 120d ago should drift; today's row must not."""
    past = datetime.utcnow() - timedelta(days=120)
    now_iso = datetime.utcnow()

    drifts = list(detect_ttl_drift(
        semantic_index={
            "S1": {"last_reinforced_at": past, "source_ref": "x"},
            "S2": {"last_reinforced_at": now_iso, "source_ref": "y"},
        },
        now=datetime.utcnow(),
    ))

    assert len(drifts) == 1
    assert drifts[0].kb_node_id == "S1"
    assert drifts[0].drift_kind == "ttl"


def test_adr_frontmatter_parses():
    """An ADR markdown with valid frontmatter parses into AdrMeta."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "ADR-001-test.md"
        path.write_text(
            "---\n"
            "id: 001\n"
            "title: test\n"
            "date: 2026-07-15\n"
            "---\n"
            "# body\n",
            encoding="utf-8",
        )

        meta = parse_adr(path)

    assert meta is not None
    assert meta.id == "001"
    assert meta.title == "test"
    assert meta.date.year == 2026
    assert meta.date.month == 7
    assert meta.date.day == 15


def test_ci_daily_run_no_errors():
    """Smoke test: the CLI module is importable and ``main()`` accepts
    an argv list end-to-end.

    We run ``main(['--help'])`` which exits via SystemExit(0) so the
    process returns 0 without ever touching the DB — verifying the
    argparse wiring, import graph, and the module's external surface
    are healthy in CI.
    """
    # Ensure scripts/ is importable so ``from scripts.drift_detector import main``
    # works without needing ``python -m``.
    repo_root = Path(__file__).resolve().parents[2]
    scripts_dir = repo_root / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    from scripts.drift_detector import main as drift_main  # type: ignore

    try:
        drift_main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0
    else:  # pragma: no cover - argparse always exits on --help
        assert False, "argparse --help should have raised SystemExit"
