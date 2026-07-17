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
from dataclasses import dataclass, field
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

@dataclass
class SpanRecorder:
    """Records attributes for the current root span.

    Used by engine.decide() and its sub-modules to record timing,
    counts, and status without producing child spans (per design).
    """
    attributes: dict[str, str | int | float] = field(default_factory=dict)
    status: str = "ok"
    start_time: float = 0.0

    def set_attribute(self, key: str, value: str | int | float) -> None:
        self.attributes[key] = value

    def set_status(self, status: str) -> None:
        self.status = status


# ContextVar for current span (separate from trace_id)
_current_span: contextvars.ContextVar[Optional[SpanRecorder]] = contextvars.ContextVar(
    "current_span", default=None
)


def get_current_span() -> SpanRecorder | None:
    """Return the current span recorder, or None if no span active."""
    return _current_span.get()


def start_span(name: str) -> tuple[SpanRecorder, contextvars.Token]:
    """Start a new root span and bind to context.

    Returns (span, token). Caller is responsible for finish_span(token).
    """
    import time
    span = SpanRecorder(start_time=time.perf_counter())
    span.set_attribute("span.name", name)
    token = _current_span.set(span)
    return span, token


def finish_span(span: SpanRecorder, token) -> None:
    """Finish span — emit attributes to structured log.

    Output format (single line, space-separated key=value pairs):
      span_end name={span.name} trace_id={trace_id} span_id={span_id}
      status={status} duration_ms={ms} {all_attributes}
    """
    import logging
    import time
    elapsed_ms = (time.perf_counter() - span.start_time) * 1000
    span.set_attribute("span.duration_ms", elapsed_ms)
    trace = get_current_trace()
    logger = logging.getLogger("starlearn.trace")
    # Build structured log line: key=value pairs space-separated
    attrs_str = " ".join(f"{k}={v}" for k, v in sorted(span.attributes.items()))
    logger.info(
        f"span_end name={span.attributes.get('span.name', 'unknown')} "
        f"trace_id={trace.trace_id if trace else 'none'} "
        f"span_id={trace.span_id if trace else 'none'} "
        f"status={span.status} duration_ms={elapsed_ms:.1f} {attrs_str}"
    )
    _current_span.reset(token)


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