"""S8 — DriftReport ORM model (slice-B2).

A DriftReport row is emitted when the daily drift sweep detects a
mismatch between a KB node and its authoritative source. There are three
``drift_kind`` values:

* ``file_hash``  — the source file's mtime/hash moved after the KB
  node's ``last_verified_at`` (detector.detect_file_hash_drift).
* ``adr``        — an ADR's ``date`` frontmatter is newer than the KB
  node's related ADR reference (parser/adr_parser.py).
* ``ttl``        — a semantic memory entry has not been reinforced in
  more than ``ttl_days`` (detector.detect_ttl_drift).

Rows are append-only at insert time. The ``resolved`` / ``resolved_at``
columns are toggled by the management UI / ops scripts; the detector
itself never resolves them.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DriftReport(Base):
    """One KB-node ↔ source-of-truth drift observation."""

    __tablename__ = "drift_reports"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True,
    )
    kb_node_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True,
    )
    drift_kind: Mapped[str] = mapped_column(
        String(32), nullable=False,
    )  # file_hash | adr | ttl
    source_ref: Mapped[str] = mapped_column(
        String(256), nullable=False,
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False,
    )
    resolved: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True,
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True,
    )


__all__ = ["DriftReport"]
