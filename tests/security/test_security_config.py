# -*- coding: utf-8 -*-
"""Tests for SecurityConfig dataclass.

Verifies defaults, env var override, and singleton behavior.
"""
import pytest

from app.core.security_config import (
    SECURITY_HEADERS,
    SecurityConfig,
    get_security_config,
)


class TestSecurityConfigDefaults:
    def test_default_allowed_origins(self):
        cfg = SecurityConfig()
        assert "http://localhost:3000" in cfg.allowed_origins
        assert "http://localhost:5173" in cfg.allowed_origins
        assert "http://127.0.0.1:8000" in cfg.allowed_origins

    def test_default_csp_includes_self(self):
        cfg = SecurityConfig()
        assert "'self'" in cfg.csp_policy
        assert "default-src" in cfg.csp_policy

    def test_hsts_disabled_by_default(self):
        cfg = SecurityConfig()
        assert cfg.enable_hsts is False

    def test_default_rate_limits(self):
        cfg = SecurityConfig()
        assert cfg.login_rate_per_minute == 5
        assert cfg.register_rate_per_hour == 3
        assert cfg.ai_chat_rate_per_minute == 30
        assert cfg.default_api_rate_per_minute == 60

    def test_default_size_limits(self):
        cfg = SecurityConfig()
        assert cfg.max_request_size_mb == 10
        assert cfg.max_streaming_size_mb == 50

    def test_dev_mode_enabled_by_default(self):
        cfg = SecurityConfig()
        assert cfg.dev_mode is True


class TestSecurityConfigEnvOverrides:
    def test_allowed_origins_override(self, monkeypatch):
        monkeypatch.setenv(
            "SECURITY_ALLOWED_ORIGINS",
            "https://app.example.com,https://admin.example.com"
        )
        cfg = SecurityConfig()
        assert cfg.allowed_origins == [
            "https://app.example.com", "https://admin.example.com"
        ]

    def test_csp_override(self, monkeypatch):
        monkeypatch.setenv(
            "SECURITY_CSP_POLICY",
            "default-src 'none'"
        )
        cfg = SecurityConfig()
        assert cfg.csp_policy == "default-src 'none'"

    def test_hsts_enable(self, monkeypatch):
        monkeypatch.setenv("SECURITY_ENABLE_HSTS", "true")
        cfg = SecurityConfig()
        assert cfg.enable_hsts is True

    def test_rate_limit_overrides(self, monkeypatch):
        monkeypatch.setenv("RATE_LIMIT_LOGIN", "10")
        monkeypatch.setenv("RATE_LIMIT_REGISTER", "5")
        cfg = SecurityConfig()
        assert cfg.login_rate_per_minute == 10
        assert cfg.register_rate_per_hour == 5

    def test_size_limit_overrides(self, monkeypatch):
        monkeypatch.setenv("MAX_REQUEST_SIZE_MB", "25")
        monkeypatch.setenv("MAX_STREAMING_SIZE_MB", "100")
        cfg = SecurityConfig()
        assert cfg.max_request_size_mb == 25
        assert cfg.max_streaming_size_mb == 100

    def test_dev_mode_override(self, monkeypatch):
        monkeypatch.setenv("SECURITY_DEV_MODE", "false")
        cfg = SecurityConfig()
        assert cfg.dev_mode is False

    def test_invalid_rate_limit_uses_zero(self, monkeypatch):
        monkeypatch.setenv("RATE_LIMIT_LOGIN", "not-a-number")
        cfg = SecurityConfig()
        # int("not-a-number") raises; SecurityConfig catches and uses 0
        assert cfg.login_rate_per_minute == 0


class TestSecurityHeadersConstant:
    def test_security_headers_present(self):
        assert "X-Content-Type-Options" in SECURITY_HEADERS
        assert "X-Frame-Options" in SECURITY_HEADERS
        assert "X-XSS-Protection" in SECURITY_HEADERS
        assert "Referrer-Policy" in SECURITY_HEADERS
        assert "Permissions-Policy" in SECURITY_HEADERS

    def test_security_header_values(self):
        assert SECURITY_HEADERS["X-Content-Type-Options"] == "nosniff"
        assert SECURITY_HEADERS["X-Frame-Options"] == "DENY"
        assert SECURITY_HEADERS["X-XSS-Protection"] == "1; mode=block"
        assert "strict-origin" in SECURITY_HEADERS["Referrer-Policy"]
        assert "geolocation=()" in SECURITY_HEADERS["Permissions-Policy"]


class TestGetSecurityConfig:
    def test_returns_singleton(self):
        cfg1 = get_security_config()
        cfg2 = get_security_config()
        assert cfg1 is cfg2
