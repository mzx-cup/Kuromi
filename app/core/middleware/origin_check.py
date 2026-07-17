# -*- coding: utf-8 -*-
"""OriginCheckMiddleware — CSRF protection via Origin/Referer header validation.

Only enforced for state-changing methods (POST/PUT/DELETE/PATCH).
GET/HEAD/OPTIONS are exempt (safe methods per RFC 7231).
"""
from __future__ import annotations

from urllib.parse import urlparse

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.security_config import SECURITY_HEADERS, get_security_config

# Methods that change server state — require Origin/Referer check
STATE_CHANGING_METHODS = {"POST", "PUT", "DELETE", "PATCH"}


def _with_security_headers(response: JSONResponse) -> JSONResponse:
    """Attach fixed security headers to a short-circuit JSONResponse.

    Short-circuit 403 responses bypass SecurityHeadersMiddleware, so we
    apply the same fixed header set here to keep the security contract.
    """
    config = get_security_config()
    for header, value in SECURITY_HEADERS.items():
        response.headers[header] = value
    response.headers["Content-Security-Policy"] = config.csp_policy
    return response


class OriginCheckMiddleware(BaseHTTPMiddleware):
    """Reject state-changing requests from unauthorized origins."""

    async def dispatch(self, request: Request, call_next):
        config = get_security_config()

        # Dev mode bypass (developer convenience)
        if config.dev_mode:
            return await call_next(request)

        # Only check state-changing methods
        if request.method not in STATE_CHANGING_METHODS:
            return await call_next(request)

        # Extract Origin (preferred) or Referer (fallback)
        origin = request.headers.get("origin") or request.headers.get("referer", "")

        if not origin:
            return _with_security_headers(
                JSONResponse(
                    status_code=403,
                    content={"detail": "Cross-origin request rejected (no Origin/Referer header)"},
                )
            )

        # Parse origin URL
        try:
            parsed = urlparse(origin)
            origin_url = f"{parsed.scheme}://{parsed.netloc}"
        except Exception:
            return _with_security_headers(
                JSONResponse(
                    status_code=403,
                    content={"detail": "Invalid Origin/Referer header"},
                )
            )

        # Check against allowlist
        if origin_url not in config.allowed_origins:
            return _with_security_headers(
                JSONResponse(
                    status_code=403,
                    content={"detail": "Cross-origin request rejected (origin not allowed)"},
                )
            )

        return await call_next(request)
