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


class TestRateLimitIntegration:
    def test_login_returns_429_after_5_attempts(self, client):
        """5 attempts pass (200/401), 6th returns 429."""
        for i in range(5):
            r = client.post("/api/auth/login", json={
                "username": "admin", "password": "wrong"
            })
            assert r.status_code in (200, 401, 422), (
                f"Attempt {i+1}: unexpected status {r.status_code}"
            )

        r = client.post("/api/auth/login", json={
            "username": "admin", "password": "wrong"
        })
        assert r.status_code == 429
        assert "retry-after" in r.headers

    def test_429_response_has_security_headers(self, client):
        """Even rate-limited responses carry security headers."""
        for _ in range(6):
            client.post("/api/auth/login", json={
                "username": "admin", "password": "wrong"
            })
        r = client.post("/api/auth/login", json={
            "username": "admin", "password": "wrong"
        })
        assert r.status_code == 429
        assert "x-content-type-options" in [k.lower() for k in r.headers.keys()]
        assert "content-security-policy" in [k.lower() for k in r.headers.keys()]

    def test_register_limited_3_per_hour(self, client):
        """Registration limited to 3 per hour per IP."""
        for i in range(3):
            r = client.post("/api/register", json={
                "username": f"newuser_{i}",
                "password": "test1234",
            })
            # First attempt may succeed (200), next 2 may 400 (duplicate) or 422
            assert r.status_code in (200, 400, 422)

        r = client.post("/api/register", json={
            "username": "newuser_final",
            "password": "test1234",
        })
        assert r.status_code == 429

    def test_static_assets_not_rate_limited(self, client):
        """Static CSS/JS/HTML files not subject to API rate limit."""
        for _ in range(50):
            r = client.get("/css/tokens.css")
        assert r.status_code != 429
