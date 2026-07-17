# -*- coding: utf-8 -*-
"""W3C Trace Context (traceparent header) — lightweight implementation.

Reference: https://www.w3.org/TR/trace-context/
Format: 00-{32 hex trace_id}-{16 hex span_id}-{2 hex flags}

Uses stdlib contextvars (no opentelemetry-api dependency).
This file contains ONLY the data layer — middleware and span recorder
are added in later slices.
"""
from __future__ import annotations

import contextvars
import re
from dataclasses import dataclass
from typing import Optional

# W3C traceparent format: 00-{32 hex}-{16 hex}-{2 hex}
TRACEPARENT_RE = re.compile(
    r"^([0-9a-f]{2})-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$"
)
TRACEPARENT_VERSION = "00"
TRACEPARENT_FLAGS_SAMPLED = "01"


@dataclass(frozen=True)
class TraceContext:
    """Immutable trace context carried across the request."""
    trace_id: str  # 32 hex chars
    span_id: str   # 16 hex chars
    flags: str = TRACEPARENT_FLAGS_SAMPLED

    @property
    def traceparent(self) -> str:
        return f"{TRACEPARENT_VERSION}-{self.trace_id}-{self.span_id}-{self.flags}"


# ContextVar for downstream code to access current trace
_current_trace: contextvars.ContextVar[Optional[TraceContext]] = contextvars.ContextVar(
    "current_trace", default=None
)

# Placeholder for _current_span — full implementation in Slice 2.1.3
_current_span: contextvars.ContextVar = contextvars.ContextVar(
    "current_span", default=None
)


def generate_trace_id() -> str:
    """Generate a 32-hex-char trace ID (cryptographically random)."""
    import secrets
    return secrets.token_hex(16)


def generate_span_id() -> str:
    """Generate a 16-hex-char span ID (cryptographically random)."""
    import secrets
    return secrets.token_hex(8)


def parse_traceparent(header: str | None) -> TraceContext:
    """Parse incoming traceparent header or generate new context."""
    if header:
        match = TRACEPARENT_RE.match(header.strip())
        if match:
            return TraceContext(
                trace_id=match.group(2),
                span_id=generate_span_id(),
                flags=match.group(4),
            )
    return TraceContext(
        trace_id=generate_trace_id(),
        span_id=generate_span_id(),
    )


def get_current_trace() -> TraceContext | None:
    """Return the current request's trace context, or None."""
    return _current_trace.get()


def set_current_trace(ctx: TraceContext) -> contextvars.Token:
    """Set current trace context (returns Token for restoration)."""
    return _current_trace.set(ctx)


def reset_current_trace(token: contextvars.Token) -> None:
    """Restore previous trace context."""
    _current_trace.reset(token)