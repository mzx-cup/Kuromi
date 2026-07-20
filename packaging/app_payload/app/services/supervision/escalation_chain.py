"""Supervision escalation chain (slice-B1 step2/step3 scheduler).

Schedules step 2 (+24h) and step 3 (+72h) when an event fires.
On ``user_responded()`` cancels any pending steps for that event.

Both the scheduler and canceller are injectable callables so unit tests
can observe behaviour without APScheduler. Production wiring lives in the
startup path and passes real ``add_job`` / ``remove_job`` bound callables.
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from app.models.supervision import SupervisionEvent

_log = logging.getLogger(__name__)

SchedulerLike = Callable[[int, int, int], Any]
Canceller = Callable[[int, int], Any]


class EscalationChain:
    def __init__(
        self,
        *,
        scheduler: Optional[SchedulerLike] = None,
        canceller: Optional[Canceller] = None,
        step_delays_h: tuple[int, int] = (24, 72),
    ) -> None:
        self._schedule = scheduler or self._default_schedule
        self._cancel = canceller or self._default_cancel
        self._delays = step_delays_h

    def schedule_steps(self, event: SupervisionEvent) -> None:
        self._schedule(event.id, 2, self._delays[0])
        self._schedule(event.id, 3, self._delays[1])

    def user_responded(self, event_id: int) -> int:
        """Cancel all pending steps >= 2 for the event. Returns count cancelled."""
        cancelled = 0
        for step in (2, 3):
            try:
                self._cancel(event_id, step)
                cancelled += 1
            except Exception as exc:  # noqa: BLE001
                _log.warning(
                    "cancel step=%s event_id=%s failed: %s",
                    step, event_id, exc,
                )
        return cancelled

    @staticmethod
    def _default_schedule(event_id: int, step: int, hours: int) -> None:
        # Production wiring: APScheduler.add_job(...) lives in startup.
        # For unit tests we no-op.
        pass

    @staticmethod
    def _default_cancel(event_id: int, step: int) -> None:
        # Production wiring: APScheduler.remove_job(...)
        pass


__all__ = ["EscalationChain"]
