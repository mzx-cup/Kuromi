# -*- coding: utf-8 -*-
"""Rate limiter using SlowAPI.

Single-process in-memory backend. State lost on restart (acceptable for dev/demo).
For production multi-process deployments, configure SlowAPI to use Redis.
"""
from __future__ import annotations

import logging

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.auth_utils import decode_jwt_no_verify
from app.core.security_config import get_security_config

logger = logging.getLogger("starlearn.rate_limiter")


def _user_or_ip_key(request: Request) -> str:
    """Extract user_id from JWT if present, else fall back to IP.

    Returns: "user:<uid>" for authenticated requests, "ip:<addr>" otherwise.
    """
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        claims = decode_jwt_no_verify(token)
        if claims and claims.get("uid"):
            return f"user:{claims['uid']}"
    return f"ip:{get_remote_address(request)}"


# Initialize with per-IP key (default for unauthenticated endpoints)
config = get_security_config()
limiter = Limiter(key_func=get_remote_address)


def login_rate_limit():
    """5/min/IP for login attempts."""
    return limiter.limit(f"{config.login_rate_per_minute}/minute")


def register_rate_limit():
    """3/hour/IP for register attempts."""
    return limiter.limit(f"{config.register_rate_per_hour}/hour")


def guest_login_rate_limit():
    """10/hour/IP for guest login attempts."""
    return limiter.limit(f"{config.guest_login_rate_per_hour}/hour")


def ai_chat_rate_limit():
    """30/min per-user for AI chat endpoints."""
    return limiter.limit(f"{config.ai_chat_rate_per_minute}/minute", key_func=_user_or_ip_key)


def default_api_rate_limit():
    """60/min/IP default rate limit."""
    return limiter.limit(f"{config.default_api_rate_per_minute}/minute")
