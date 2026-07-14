"""APScheduler wiring for the daily memory-consolidation cron (slice-s6).

Core Innovation 2's last mile: a single 03:00 daily ``AsyncIOScheduler``
job iterates active users and runs ``consolidate_user`` for each. One
user's failure is caught and logged, never blocking the rest of the run.
The schedule is built but never ``start()``-ed from this module — the
caller (typically FastAPI's startup) chooses when to spin the loop.
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger


from app.services.memory.consolidator import consolidate_user


_log = logging.getLogger(__name__)


# S6.3 stub: returns a single demo user until ``CapabilityProfileRepository
# .list_active_user_ids`` lands in the cold-start slice (S11).
def _list_active_user_ids() -> list[str]:
    """Return the set of user ids the daily cron should consolidate.

    S6.3 stub: hard-coded to a single demo user. Replaced with
    ``CapabilityProfileRepository.list_active_user_ids`` in a later
    slice once the cold-start wiring is in place.
    """
    return ["u-demo-user"]


def _run_daily_consolidation() -> None:
    """Iterate active users and consolidate each, swallowing per-user errors."""
    for uid in _list_active_user_ids():
        try:
            result = consolidate_user(uid)
            _log.info("consolidator(uid=%s): %s", uid, result)
        except Exception as exc:  # noqa: BLE001
            # Per-user failure is logged but does NOT stop the iteration —
            # other users still get their consolidation pass.
            _log.exception("consolidator(uid=%s) crashed: %s", uid, exc)


def start_consolidation_scheduler() -> AsyncIOScheduler:
    """Create + configure the consolidator's AsyncIOScheduler.

    Schedules ``_run_daily_consolidation`` at 03:00 every day. The
    scheduler is **returned**, not started — callers (FastAPI startup /
    a CLI runner) decide when to invoke ``scheduler.start()``.
    """
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _run_daily_consolidation,
        CronTrigger(hour=3, minute=0),
        id="daily_memory_consolidation",
        replace_existing=True,
    )
    return scheduler


__all__ = [
    "start_consolidation_scheduler",
    "_run_daily_consolidation",
    "_list_active_user_ids",
]
