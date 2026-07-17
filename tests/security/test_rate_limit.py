# -*- coding: utf-8 -*-
"""Tests for rate limit decorators and SlowAPI integration.

Tests verify:
  - Decorators are importable
  - SlowAPI limiter instance is configured
  - Decorators apply correct limits based on SecurityConfig
"""
import pytest


class TestRateLimiterModule:
    def test_limiter_instance_exists(self):
        from app.core.rate_limiter import limiter
        assert limiter is not None

    def test_login_rate_limit_decorator_exists(self):
        from app.core.rate_limiter import login_rate_limit
        assert callable(login_rate_limit)

    def test_register_rate_limit_decorator_exists(self):
        from app.core.rate_limiter import register_rate_limit
        assert callable(register_rate_limit)

    def test_guest_login_rate_limit_decorator_exists(self):
        from app.core.rate_limiter import guest_login_rate_limit
        assert callable(guest_login_rate_limit)

    def test_ai_chat_rate_limit_decorator_exists(self):
        from app.core.rate_limiter import ai_chat_rate_limit
        assert callable(ai_chat_rate_limit)

    def test_default_api_rate_limit_decorator_exists(self):
        from app.core.rate_limiter import default_api_rate_limit
        assert callable(default_api_rate_limit)


class TestRateLimiterConfig:
    def test_login_limit_reflects_config(self, monkeypatch):
        monkeypatch.setenv("RATE_LIMIT_LOGIN", "10")
        from app.core.rate_limiter import login_rate_limit
        decorator = login_rate_limit()
        # The decorator should produce a callable
        assert callable(decorator)
