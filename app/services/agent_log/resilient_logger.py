"""3-layer ResilientBehaviorLogger (DB -> Redis -> Disk).

Layered write strategy: a log entry is always written to the first layer
that accepts it. Order of preference:

    1. PostgreSQL (``db_insert``) — the canonical store.
    2. Redis buffer (``redis_push``) — fast retry buffer if DB is unhealthy.
    3. Disk spool (``disk_append``) — durable last-resort buffer.

If all three layers fail, the entry is rejected and the caller receives
a ``LogResult(status="rejected")`` so it can decide how to react (raise,
retry later, drop, etc).

Each layer is a module-level callable so tests can patch
``app.services.agent_log.resilient_logger.<name>`` directly.

NOTE: ``db_insert`` is intentionally a stub that returns False for now
so the fallthrough path (Redis -> Disk) is exercised cleanly during the
gap before S3.2 lands. The real implementation is wired in S3 task S3.2.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.models.agent_behavior_log import AgentBehaviorLog
from app.services.agent_log.buffer import redis_push
from app.services.agent_log.disk_spool import disk_append


def db_insert(log: AgentBehaviorLog) -> bool:
    """Insert ``log`` into the canonical store (PostgreSQL).

    Real DB insert — implemented in S3 task S3.2.
    """
    return False


@dataclass
class LogResult:
    """Outcome of a ``ResilientBehaviorLogger.log`` call."""
    status: str  # one of: "ok", "deferred", "deferred_disk", "rejected"
    layer: str = ""  # which layer accepted the write: "db" / "redis" / "disk" / ""
    error: str = ""


class ResilientBehaviorLogger:
    """3-layer fail-open logger. Always tries DB first; on failure falls
    through to Redis, then to disk. Never raises on layer failures — the
    caller decides what to do with a rejected entry.
    """

    def log(self, log: AgentBehaviorLog) -> LogResult:
        # Layer 1: DB.
        try:
            if db_insert(log):
                return LogResult(status="ok", layer="db")
        except Exception as exc:  # noqa: BLE001 - fail-open contract.
            # If db_insert raises, treat as DB-failed so we fall through
            # to Redis/disk. The S0.3 stub returns False directly, so this
            # branch only fires once S3.2 wires the real DB layer and a
            # transient error escapes (e.g. connection drop).
            db_error = str(exc)
        else:
            db_error = ""

        # Layer 2: Redis buffer.
        try:
            if redis_push(_payload(log)):
                return LogResult(status="deferred", layer="redis", error=db_error)
        except Exception as exc:  # noqa: BLE001
            redis_error = str(exc)
        else:
            redis_error = ""

        # Layer 3: Disk spool (last resort, durable).
        try:
            if disk_append(_payload(log)):
                return LogResult(
                    status="deferred_disk",
                    layer="disk",
                    error=db_error or redis_error,
                )
        except Exception as exc:  # noqa: BLE001
            disk_error = str(exc)
        else:
            disk_error = ""

        return LogResult(status="rejected", error=db_error or redis_error or disk_error)


def _payload(log: AgentBehaviorLog) -> dict[str, Any]:
    """Serialize an AgentBehaviorLog to a plain dict for Redis/disk layers."""
    return {
        "agent_id": log.agent_id,
        "user_id": log.user_id,
        "action_type": log.action_type,
        "input_summary": log.input_summary,
        "output_text": log.output_text,
        "citations": log.citations,
    }