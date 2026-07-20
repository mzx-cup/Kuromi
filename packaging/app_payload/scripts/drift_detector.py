"""CLI: scan for drift between KB nodes and their sources.

Run with::

    PYTHONPATH=. python scripts/drift_detector.py [--root .] [--since-hours 24]

The script walks two drift kinds:

* ``file_hash``  — every KB node whose ``source_reference`` starts with
  ``file:`` and whose underlying file's mtime is newer than ``since``.
* ``ttl``        — every semantic-memory row not reinforced in >90d.

Detected drifts are persisted via :func:`app.services.drift.persist`,
which writes one row per drift into the ``drift_reports`` table. The
script exits 0 even when no drifts are found — failure modes are
surfaced to stderr with an exit code of 1.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

from app.repositories.orm.knowledge_node import SessionFactory
from app.services.drift.detector import (
    Drift,
    detect_file_hash_drift,
    detect_ttl_drift,
)
from app.services.drift.reporter import persist


def _load_kb_index() -> dict[str, dict]:
    """Pull every KnowledgeNode and shape the data for the detector.

    Imports the model lazily so this module stays import-safe even when
    the L1 sync DB is not provisioned (tests / cold-start scenarios).
    Returns ``{}`` if the table is empty or unavailable.
    """
    try:
        from app.models.knowledge_node import KnowledgeNode
    except Exception as exc:  # noqa: BLE001
        print(f"[drift] knowledge_node model unavailable: {exc}", file=sys.stderr)
        return {}

    try:
        with SessionFactory() as s:
            rows = s.query(KnowledgeNode).all()
    except Exception as exc:  # noqa: BLE001
        print(f"[drift] KB query failed: {exc}", file=sys.stderr)
        return {}

    return {
        r.id: {"source_reference": getattr(r, "source_reference", "")}
        for r in rows
        if getattr(r, "id", None)
    }


def _load_semantic_index() -> dict[str, dict]:
    """Best-effort fetch of semantic-memory rows for TTL drift.

    The semantic layer may not yet be wired into this CLI in dev /
    test environments; return ``{}`` rather than raising so callers can
    still detect file_hash drift without a perfect DB.
    """
    try:
        from app.models.semantic_memory import SemanticMemory
    except Exception:
        return {}

    try:
        with SessionFactory() as s:
            rows = s.query(SemanticMemory).all()
    except Exception as exc:  # noqa: BLE001
        print(f"[drift] semantic query failed: {exc}", file=sys.stderr)
        return {}

    return {
        getattr(r, "id", str(i)): {
            "last_reinforced_at": getattr(r, "last_reinforced_at", None),
            "source_ref": getattr(r, "source_ref", ""),
        }
        for i, r in enumerate(rows)
    }


def _collect_drifts(*, root: str, since_hours: int) -> Iterable[Drift]:
    kb_index = _load_kb_index()
    semantic_index = _load_semantic_index()
    since = datetime.utcnow() - timedelta(hours=max(1, since_hours))
    now = datetime.utcnow()

    yield from detect_file_hash_drift(
        project_root=root,
        kb_index=kb_index,
        since=since,
    )
    yield from detect_ttl_drift(
        semantic_index=semantic_index,
        now=now,
    )


def main(argv: Any = None) -> int:
    parser = argparse.ArgumentParser(description="Scan for KB drift.")
    parser.add_argument(
        "--root",
        default=".",
        help="Project root used to resolve file: source references.",
    )
    parser.add_argument(
        "--since-hours",
        type=int,
        default=24,
        help="Look back window for file_hash drift (default: 24).",
    )
    args = parser.parse_args(argv)

    root = str(Path(args.root).resolve())
    drifts = list(_collect_drifts(root=root, since_hours=args.since_hours))
    n = persist(drifts)
    print(f"Drift scan: {n} new reports")
    return 0


if __name__ == "__main__":
    sys.exit(main())
