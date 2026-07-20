"""ADR frontmatter parser — slice-B2.

Each ADR markdown file under ``docs/superpowers/specs/*`` is expected
to begin with a YAML-ish frontmatter block, e.g.::

    ---
    id: ADR-007
    title: Use APScheduler for drift cron
    date: 2026-07-15
    ---

This module extracts ``id`` / ``title`` / ``date`` / ``path`` for drift
comparison (newer ADR date vs KB node's last ADR reference). The parser
intentionally understands the small subset of keys we control — full
YAML parsing is left to PyYAML if/when the schema grows.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class AdrMeta:
    """Parsed frontmatter of one ADR file."""

    id: str
    title: str
    date: datetime
    path: str


_FM_RE = re.compile(r"^---\n(.+?)\n---", re.DOTALL)


def parse_adr(path: Path) -> Optional[AdrMeta]:
    """Return :class:`AdrMeta` if ``path`` looks like a valid ADR; else ``None``.

    Frontmatter is optional; files without it are rejected (we need the
    ``date`` field for drift comparison).
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    m = _FM_RE.search(text)
    if not m:
        return None

    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        fm[k.strip()] = v.strip()

    raw_date = fm.get("date", "").replace("/", "-")
    try:
        date = datetime.fromisoformat(raw_date)
    except ValueError:
        return None

    return AdrMeta(
        id=fm.get("id", path.stem),
        title=fm.get("title", ""),
        date=date,
        path=str(path),
    )


def iter_adrs(specs_dir: Path) -> list[AdrMeta]:
    """Walk ``specs_dir`` recursively and parse every ``*.md`` file. Files
    without parseable frontmatter are silently skipped."""
    if not specs_dir.exists():
        return []
    out: list[AdrMeta] = []
    for path in specs_dir.rglob("*.md"):
        meta = parse_adr(path)
        if meta is not None:
            out.append(meta)
    return out


__all__ = ["AdrMeta", "parse_adr", "iter_adrs"]
