"""APScheduler wiring for the daily 04:00 drift cron (slice-B2).

Mirrors the consolidator scheduler at
``app/services/memory/scheduler.py`` — the scheduler is constructed and
configured but never ``start()``-ed here. FastAPI's startup owns the
start lifecycle.
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger


_log = logging.getLogger(__name__)


def _run_daily() -> None:
    """Hook entry point invoked at 04:00 local server time.

    Imported lazily to keep the scheduler module I/O-free at import.
    Per-call exceptions are caught so a transient failure doesn't take
    down the scheduler (mirrors the consolidator's per-user swallow).
    """
    try:
        from scripts.drift_detector import main as drift_main  # type: ignore
        drift_main()
    except Exception as exc:  # noqa: BLE001
        _log.exception("daily drift scan failed: %s", exc)


def start_drift_scheduler() -> AsyncIOScheduler:
    """Build an AsyncIOScheduler pinned to ``hour=4 minute=0`` daily.

    Returns the constructed scheduler so callers can ``scheduler.start()``
    it at FastAPI startup. Callers can also pre-register additional jobs
    on the returned object before starting the event loop.
    """
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _run_daily,
        CronTrigger(hour=4, minute=0),
        id="daily_drift",
        replace_existing=True,
    )
    return scheduler


__all__ = ["start_drift_scheduler"]
