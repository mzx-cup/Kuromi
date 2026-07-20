"""S7.3 — ChannelDispatcher for supervision escalation chains.

Each step of a ``SupervisionRule.escalation_chain.steps`` declares a
``channels`` list (``inapp`` / ``push`` / ``email`` / arbitrary strings
for forward compatibility) and a ``template`` string. The dispatcher
formats the template against ``{"user_id": ..., **ctx}`` and records
each delivery in an in-memory ``sent`` log. Production wiring (real
push / email providers) is deferred to a later slice — the dispatcher
focuses on the format-and-route contract.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Callable, Optional

from app.models.supervision import SupervisionEvent, SupervisionRule


_log = logging.getLogger(__name__)

# A real delivery backend: ``sender(channel, message)`` performs the actual
# send (push / email / websocket) and raises on transient failure so the
# dispatcher can retry. When ``None`` the dispatcher only formats + records.
SenderLike = Callable[[str, str], Any]


def _deliver_with_retry(
    sender: SenderLike,
    channel: str,
    message: str,
    *,
    event_id: Optional[int],
    step_idx: int,
    max_retries: int,
) -> None:
    """Call ``sender`` with exponential backoff (1s, 2s, 4s, ...).

    Re-raises the last exception after ``max_retries`` attempts.
    """
    for attempt in range(max_retries):
        try:
            sender(channel, message)
            return
        except Exception as exc:  # noqa: BLE001
            if attempt == max_retries - 1:
                _log.error(
                    "channel dispatch failed after %s retries: "
                    "event=%s step=%s channel=%s: %s",
                    max_retries, event_id, step_idx, channel, exc,
                )
                raise
            time.sleep(2 ** attempt)  # 1s, 2s, 4s


class _Delivery:
    """A single formatted channel delivery — kept in memory for tests."""

    __slots__ = ("channel", "message", "step", "rule_id", "event_id")

    def __init__(self, channel: str, message: str, step: int,
                 rule_id: Optional[str], event_id: Optional[int]) -> None:
        self.channel = channel
        self.message = message
        self.step = step
        self.rule_id = rule_id
        self.event_id = event_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel": self.channel,
            "message": self.message,
            "step": self.step,
            "rule_id": self.rule_id,
            "event_id": self.event_id,
        }


_sent: list[_Delivery] = []


def reset_sent_log() -> None:
    """Clear the in-memory send log between tests."""
    _sent.clear()


def dispatch(
    *,
    event: Optional[SupervisionEvent],
    step: dict[str, Any],
    rule: Any,
    user_id: str,
    ctx: Optional[dict[str, Any]] = None,
    sender: Optional[SenderLike] = None,
    max_retries: int = 3,
) -> list[dict[str, Any]]:
    """Format the step's template and return one record per channel.

    ``rule`` may be a ``SupervisionRule`` model **or** a plain dict
    (the seeder passes dicts in to keep insertion transactional). The
    ``id`` / ``name`` fields are read with ``getattr`` so both shapes
    work.

    When ``sender`` is provided each channel is delivered through it with
    exponential backoff (1s, 2s, 4s) up to ``max_retries`` attempts; a
    delivery is only recorded once the sender succeeds. When ``sender`` is
    ``None`` (the default) the dispatcher stays a pure format-and-route
    contract and records every channel unconditionally.
    """
    channels = step.get("channels") or []
    template = step.get("template") or ""
    step_idx = int(step.get("step", 1))
    rule_id = getattr(rule, "id", None) or rule.get("id") if isinstance(rule, dict) else getattr(rule, "id", None)
    event_id = getattr(event, "id", None)

    format_ctx: dict[str, Any] = dict(ctx or {})
    format_ctx["user_id"] = user_id
    try:
        formatted = template.format(**format_ctx)
    except (KeyError, IndexError) as exc:
        _log.warning(
            "channel_dispatch: template format failed (rule=%s step=%s exc=%s)",
            rule_id, step_idx, exc,
        )
        formatted = template

    out: list[dict[str, Any]] = []
    for channel in channels:
        if sender is not None:
            _deliver_with_retry(
                sender,
                str(channel),
                formatted,
                event_id=event_id,
                step_idx=step_idx,
                max_retries=max_retries,
            )
        delivery = _Delivery(
            channel=str(channel),
            message=formatted,
            step=step_idx,
            rule_id=rule_id,
            event_id=event_id,
        )
        _sent.append(delivery)
        out.append(delivery.to_dict())
        _log.info(
            "channel_dispatch sent (rule=%s step=%s channel=%s user=%s)",
            rule_id, step_idx, channel, user_id,
        )
    return out


def list_sent() -> list[dict[str, Any]]:
    return [d.to_dict() for d in _sent]


__all__ = ["dispatch", "reset_sent_log", "list_sent"]
