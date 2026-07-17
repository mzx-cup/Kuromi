# -*- coding: utf-8 -*-
"""RequestSizeLimitMiddleware — prevents DoS via large request bodies.

Rejects requests with Content-Length exceeding the configured limit.
Streaming endpoints (AI chat, SSE) get a higher limit.
"""
from __future__ import annotations

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.security_config import SECURITY_HEADERS, get_security_config

# Endpoints that legitimately handle large payloads (AI streaming, file upload, etc.)
STREAMING_ENDPOINTS = {
    "/api/v2/chat/stream",
    "/api/v2/chat/onboard/stream",
    "/api/v2/classroom/stream",
    "/api/v2/course/bundle/generate/stream",
    "/api/v2/debate/stream",
    "/api/v2/code/review/stream",
    "/api/v2/course/chat/stream",
    "/api/v2/course/discussion/stream",
}


def _with_security_headers(response: JSONResponse) -> JSONResponse:
    """Attach fixed security headers to a short-circuit JSONResponse.

    Because this middleware is added LAST it sits at the OUTERMOST position
    in the ASGI stack. When it returns a JSONResponse directly (short-circuit),
    inner middlewares like SecurityHeadersMiddleware are NEVER invoked for
    the response. To keep the security header contract intact we apply the
    fixed headers here.
    """
    config = get_security_config()
    for header, value in SECURITY_HEADERS.items():
        response.headers[header] = value
    response.headers["Content-Security-Policy"] = config.csp_policy
    return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests with oversized bodies."""

    async def dispatch(self, request: Request, call_next):
        config = get_security_config()

        content_length = request.headers.get("content-length")
        if not content_length:
            # GET requests or chunked uploads — let them through
            return await call_next(request)

        # Parse Content-Length
        try:
            size = int(content_length)
        except ValueError:
            return _with_security_headers(
                JSONResponse(
                    status_code=400,
                    content={"detail": "Invalid Content-Length header"},
                )
            )

        # Determine limit based on endpoint
        if request.url.path in STREAMING_ENDPOINTS:
            limit_mb = config.max_streaming_size_mb
        else:
            limit_mb = config.max_request_size_mb

        limit_bytes = limit_mb * 1024 * 1024

        if size > limit_bytes:
            return _with_security_headers(
                JSONResponse(
                    status_code=413,
                    content={"detail": f"Request body too large (max {limit_mb}MB)"},
                )
            )

        return await call_next(request)