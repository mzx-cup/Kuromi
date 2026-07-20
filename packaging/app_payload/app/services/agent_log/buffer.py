"""In-memory Redis buffer (Layer 2) for ResilientBehaviorLogger.

This module exposes a module-level ``redis_push`` callable so that the
caller (``app.services.agent_log.resilient_logger``) can patch it in tests.
The real Redis client wiring is intentionally minimal here — S3 will flesh
it out when the buffer becomes hot. For S0.3 we only need the symbol to
exist and return a bool indicating success/failure.
"""
from __future__ import annotations

from typing import Any


def redis_push(payload: Any, *, key: str = "agent_behavior_logs:deferred") -> bool:
    """Push a deferred log payload onto the Redis buffer.

    Returns True on success, False on any failure (Redis down, etc.).

    NOTE: For S0.3 this is a placeholder — the real Redis client is wired
    in a later slice. Keeping the symbol at module scope so tests can
    patch ``app.services.agent_log.resilient_logger.redis_push``.
    """
    # Placeholder: real implementation arrives in a later slice.
    return False