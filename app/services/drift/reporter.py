"""Persist :class:`~app.services.drift.detector.Drift` items into the
``drift_reports`` table (slice-B2).

Designed to be DI-friendly: callers can pass their own
``OrmDriftReportRepository`` (or a fake). Without one, a module-level
default repo is constructed at call time so the daily cron stays a
one-liner.
"""
from __future__ import annotations

import logging
from typing import Iterable, Optional

from app.models.drift_report import DriftReport
from app.repositories.orm.drift_report import OrmDriftReportRepository
from app.services.drift.detector import Drift


_log = logging.getLogger(__name__)


def persist(
    drifts: Iterable[Drift],
    repo: Optional[OrmDriftReportRepository] = None,
) -> int:
    """Insert one :class:`DriftReport` row per Drift. Returns the count inserted."""
    if repo is None:
        repo = OrmDriftReportRepository()
    n = 0
    for d in drifts:
        # Defensive: any iterable of dicts / non-Drift objects is ignored.
        if not isinstance(d, Drift):
            _log.debug("persist: skipping non-Drift payload: %r", d)
            continue
        try:
            repo.insert(DriftReport(
                kb_node_id=d.kb_node_id,
                drift_kind=d.drift_kind,
                source_ref=d.source_ref,
            ))
            n += 1
        except Exception as exc:  # noqa: BLE001
            # One bad row must not poison the whole batch.
            _log.warning(
                "drift report insert failed kb=%s kind=%s: %s",
                d.kb_node_id, d.drift_kind, exc,
            )
    return n


__all__ = ["persist"]
