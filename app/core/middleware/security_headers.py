# -*- coding: utf-8 -*-
"""SecurityHeadersMiddleware — adds browser-level security headers to every response.

Adds:
  - Fixed headers from SECURITY_HEADERS (X-Content-Type-Options, X-Frame-Options, etc.)
  - Content-Security-Policy from config
  - Strict-Transport-Security (only when enable_hsts is True, i.e., HTTPS deployments)
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.security_config import SECURITY_HEADERS, get_security_config


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to every HTTP response (success and error)."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        config = get_security_config()

        # Fixed headers — every response
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value

        # Content-Security-Policy
        response.headers["Content-Security-Policy"] = config.csp_policy

        # HSTS — only on HTTPS deployments
        if config.enable_hsts:
            response.headers["Strict-Transport-Security"] = config.hsts_value

        return response
