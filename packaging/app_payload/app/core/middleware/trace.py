# -*- coding: utf-8 -*-
"""TraceMiddleware — extracts/generates W3C traceparent for every request.

Adds the traceparent header to the response so clients can correlate.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.trace import (
    parse_traceparent,
    set_current_trace,
    reset_current_trace,
)


class TraceMiddleware(BaseHTTPMiddleware):
    """Extract or generate W3C traceparent, set contextvar, echo on response."""

    async def dispatch(self, request: Request, call_next):
        # Extract or generate trace context
        incoming = request.headers.get("traceparent")
        ctx = parse_traceparent(incoming)
        token = set_current_trace(ctx)

        try:
            response: Response = await call_next(request)
            # Echo traceparent on response (W3C trace context convention)
            response.headers["traceparent"] = ctx.traceparent
            return response
        finally:
            reset_current_trace(token)
