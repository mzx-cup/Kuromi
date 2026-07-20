"""S8 — DriftReport ORM repository (slice-B2).

Follows the no-arg ``SessionFactory`` pattern shared with
``app.repositories.orm.supervision``. The detector / reporter instantiates
this without any session argument so the daily cron can stay I/O-light.

Methods:
* ``insert(report)``             — append a row
* ``get(report_id)``             — fetch by primary key
* ``list_unresolved(limit=20)``  — newest unresolved first (cold-start card)
* ``list_recent(limit=50)``      — newest first (ops / debugging)
* ``mark_resolved(report_id)``   — toggle resolved=True + stamp resolved_at
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.models.drift_report import DriftReport  # noqa: F401  (register table)
from app.repositories.orm.knowledge_node import SessionFactory, reset_session_factory


__all__ = [
    "OrmDriftReportRepository",
    "SessionFactory",
    "reset_session_factory",
]


class OrmDriftReportRepository:
    """Sync SQLAlchemy repository for ``drift_reports`` rows."""

    def __init__(self) -> None:
        self._sf = SessionFactory

    def insert(self, report: DriftReport) -> int:
        with self._sf() as s:
            s.add(report)
            s.commit()
            return int(report.id or 0)

    def get(self, report_id: int) -> Optional[DriftReport]:
        with self._sf() as s:
            return s.get(DriftReport, report_id)

    def list_unresolved(self, *, limit: int = 20) -> list[DriftReport]:
        with self._sf() as s:
            rows = (
                s.query(DriftReport)
                .filter_by(resolved=False)
                .order_by(DriftReport.detected_at.desc())
                .limit(limit)
                .all()
            )
            return list(rows)

    def list_recent(self, *, limit: int = 50) -> list[DriftReport]:
        with self._sf() as s:
            rows = (
                s.query(DriftReport)
                .order_by(DriftReport.detected_at.desc())
                .limit(limit)
                .all()
            )
            return list(rows)

    def mark_resolved(self, report_id: int, *, when: Optional[datetime] = None) -> int:
        ts = when or datetime.utcnow()
        with self._sf() as s:
            updated = (
                s.query(DriftReport)
                .filter_by(id=report_id)
                .update(
                    {"resolved": True, "resolved_at": ts},
                    synchronize_session=False,
                )
            )
            s.commit()
            return int(updated or 0)
