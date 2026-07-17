"""S8 — drift detection subsystem (slice-B2).

Public surface:

* ``detector.Drift``                                  — pure data class
* ``detector.detect_file_hash_drift``                 — scan KB nodes
* ``detector.detect_ttl_drift``                       — scan semantic memory
* ``adr_parser.parse_adr`` / ``iter_adrs``            — ADR frontmatter
* ``reporter.persist``                                — write DriftReport rows
* ``scheduler.start_drift_scheduler``                 — APScheduler 04:00 cron

The two ``detect_*`` functions are pure: no network, no DB, no LLM. The
reporter is the only I/O sink; it accepts an injectable repo so tests
can swap a fake.
"""
from __future__ import annotations

from app.services.drift.detector import (
    Drift,
    detect_file_hash_drift,
    detect_ttl_drift,
)
from app.services.drift.reporter import persist
from app.services.drift.scheduler import start_drift_scheduler


__all__ = [
    "Drift",
    "detect_file_hash_drift",
    "detect_ttl_drift",
    "persist",
    "start_drift_scheduler",
]
