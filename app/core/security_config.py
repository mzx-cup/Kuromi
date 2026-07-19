# -*- coding: utf-8 -*-
"""Centralized security configuration.

All security middleware read from this single source of truth.
Override defaults via environment variables.

Environment variables:
  SECURITY_ALLOWED_ORIGINS — comma-separated origin allowlist
  SECURITY_CSP_POLICY     — Content-Security-Policy value
  SECURITY_ENABLE_HSTS    — "true" to enable Strict-Transport-Security
  SECURITY_DEV_MODE       — "true" to skip CSRF Origin check (dev convenience)
  RATE_LIMIT_LOGIN        — login attempts per minute per IP (default: 5)
  RATE_LIMIT_REGISTER     — register attempts per hour per IP (default: 3)
  RATE_LIMIT_GUEST        — guest login attempts per hour per IP (default: 10)
  RATE_LIMIT_AI           — AI chat calls per minute per user (default: 30)
  RATE_LIMIT_DEFAULT      — default API calls per minute per IP (default: 60)
  MAX_REQUEST_SIZE_MB     — max request body size in MB (default: 10)
  MAX_STREAMING_SIZE_MB    — streaming endpoint max in MB (default: 50)
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger("starlearn.security.config")


def _env_list(name: str, default: str) -> list[str]:
    """Parse a comma-separated env var into a list of stripped strings."""
    raw = os.getenv(name, default)
    return [s.strip() for s in raw.split(",") if s.strip()]


def _env_int(name: str, default: int, on_error: int | None = None) -> int:
    """Parse an int env var; return default when unset.

    On parse error, return ``on_error`` when provided (e.g. 0 to disable a
    rate limit), otherwise fall back to ``default``. Errors are logged.
    """
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        fallback = on_error if on_error is not None else default
        logger.warning("[security_config] %s=%r is not an int, using %d", name, raw, fallback)
        return fallback


def _env_bool(name: str, default: bool) -> bool:
    """Parse a bool env var ('true'/'false'/'1'/'0')."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in ("true", "1", "yes", "on")


# Fixed security headers — returned by SecurityHeadersMiddleware on every response
SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}


@dataclass(frozen=True)
class SecurityConfig:
    """Immutable security configuration. Read env vars at construction."""

    # CORS / CSRF shared allowlist
    allowed_origins: list[str] = field(default_factory=lambda:
        _env_list(
            "SECURITY_ALLOWED_ORIGINS",
            "http://localhost:3000,http://localhost:5173,"
            "http://localhost:8080,http://127.0.0.1:8000"
        )
    )

    # Content Security Policy
    csp_policy: str = field(default_factory=lambda: os.getenv(
        "SECURITY_CSP_POLICY",
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com https://cdn.jsdelivr.net https://unpkg.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdnjs.cloudflare.com; "
        "img-src 'self' data: https: https://api.dicebear.com; "
        "media-src 'self' https://cdn.pixabay.com; "
        "connect-src 'self' http://localhost:* https://cdn.tailwindcss.com https://cdn.jsdelivr.net https://unpkg.com https://api.dicebear.com"
    ))

    # HSTS — only enable in HTTPS deployments
    enable_hsts: bool = field(default_factory=lambda: _env_bool("SECURITY_ENABLE_HSTS", False))
    hsts_value: str = "max-age=31536000; includeSubDomains"

    # Rate limits
    login_rate_per_minute: int = field(default_factory=lambda: _env_int("RATE_LIMIT_LOGIN", 5, on_error=0))
    register_rate_per_hour: int = field(default_factory=lambda: _env_int("RATE_LIMIT_REGISTER", 3))
    guest_login_rate_per_hour: int = field(default_factory=lambda: _env_int("RATE_LIMIT_GUEST", 10))
    ai_chat_rate_per_minute: int = field(default_factory=lambda: _env_int("RATE_LIMIT_AI", 30))
    default_api_rate_per_minute: int = field(default_factory=lambda: _env_int("RATE_LIMIT_DEFAULT", 60))

    # Request size limits (MB)
    max_request_size_mb: int = field(default_factory=lambda: _env_int("MAX_REQUEST_SIZE_MB", 10))
    max_streaming_size_mb: int = field(default_factory=lambda: _env_int("MAX_STREAMING_SIZE_MB", 50))

    # Dev mode — skip CSRF Origin check
    dev_mode: bool = field(default_factory=lambda: _env_bool("SECURITY_DEV_MODE", True))


# Singleton — initialized at first access
_security_config: SecurityConfig | None = None


def get_security_config() -> SecurityConfig:
    """Return the singleton SecurityConfig instance.

    A fresh instance is constructed at first access; env var changes after
    that point are NOT reflected (caller must restart process).
    """
    global _security_config
    if _security_config is None:
        _security_config = SecurityConfig()
    return _security_config


def reset_security_config() -> None:
    """Reset the singleton. For tests only."""
    global _security_config
    _security_config = None