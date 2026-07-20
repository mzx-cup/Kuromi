"""Drift detector — slice-B2.

Reports three drift kinds:

* ``file_hash``  — the source file's mtime is newer than ``since`` (the
  detector does not actually hash; an mtime comparison is the cheap
  proxy used during the daily cron).
* ``adr``        — handled in ``adr_parser.py`` (no detector per plan).
* ``ttl``        — a semantic-memory entry not reinforced in
  ``ttl_days`` days.

Both ``detect_*`` functions are pure data-in / data-out: they accept
plain dicts (loaded by the caller) and yield ``Drift`` dataclasses.
No file I/O on the cold path beyond ``os.path.getmtime``, no DB, no LLM.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterator, Optional


@dataclass(frozen=True)
class Drift:
    """One detected drift observation."""

    kb_node_id: str
    drift_kind: str  # file_hash | adr | ttl
    source_ref: str


def detect_file_hash_drift(
    *,
    project_root: str,
    kb_index: dict[str, dict],
    since: datetime,
) -> Iterator[Drift]:
    """Yield a ``Drift`` for each KB node whose source file's mtime is
    newer than ``since``.

    ``kb_index`` maps ``kb_node_id`` -> ``{"source_reference": str}``.
    Source references starting with ``file:`` are resolved relative to
    ``project_root``; any other scheme (e.g. ``url:``, ``qdrant:``) is
    ignored. Missing files are skipped silently.
    """
    for kb_id, meta in kb_index.items():
        src = (meta or {}).get("source_reference", "")
        if not src.startswith("file:"):
            continue
        rel = src[len("file:"):]
        if not rel:
            continue
        path = os.path.join(project_root, rel)
        if not os.path.isfile(path):
            continue
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(path))
        except OSError:
            continue
        if mtime > since:
            yield Drift(
                kb_node_id=kb_id,
                drift_kind="file_hash",
                source_ref=src,
            )


def detect_ttl_drift(
    *,
    semantic_index: dict[str, dict],
    now: datetime,
    ttl_days: int = 90,
) -> Iterator[Drift]:
    """Yield a ``Drift`` for every semantic-memory row whose
    ``last_reinforced_at`` is older than ``ttl_days``.

    Rows missing ``last_reinforced_at`` are skipped (we cannot decide
    drift without a timestamp). Aware vs naive datetimes are normalized
    to naive UTC for the comparison — match the existing
    ``KnowledgeNode.last_verified_at`` convention.
    """
    cutoff = now - timedelta(days=ttl_days)
    for sid, meta in semantic_index.items():
        last = (meta or {}).get("last_reinforced_at")
        if not isinstance(last, datetime):
            continue
        # Drop tzinfo for comparison (DB columns are naive DateTime).
        last_naive = last.replace(tzinfo=None) if last.tzinfo else last
        if last_naive < cutoff:
            yield Drift(
                kb_node_id=sid,
                drift_kind="ttl",
                source_ref=(meta or {}).get("source_ref", "") or "",
            )


__all__ = [
    "Drift",
    "detect_file_hash_drift",
    "detect_ttl_drift",
]
