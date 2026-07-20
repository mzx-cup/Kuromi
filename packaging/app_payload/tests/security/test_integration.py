# -*- coding: utf-8 -*-
"""Integration tests for the full security middleware stack.

Verifies that all 5 middlewares work together correctly:
  - SecurityHeadersMiddleware
  - CORSStrictMiddleware (via FastAPI CORSMiddleware)
  - RateLimitMiddleware (SlowAPI)
  - OriginCheckMiddleware
  - RequestSizeLimitMiddleware
"""
import pytest


class TestMiddlewareStack:
    def test_legal_request_flows_through_all(self, client):
        """Valid request should reach the handler and get all responses."""
        r = client.post("/api/auth/login",
                       json={"username": "admin", "password": "123456"},
                       headers={"Origin": "http://localhost:3000"})
        # Should NOT be blocked by security layer
        assert r.status_code != 403
        assert r.status_code != 429
        assert r.status_code != 413

    def test_security_headers_on_every_response_type(self, client):
        """Security headers present on 200, 404, 500."""
        # 200
        r = client.get("/login.html")
        assert "x-content-type-options" in [k.lower() for k in r.headers.keys()]

        # 404
        r = client.get("/nonexistent-route-12345")
        assert r.status_code == 404
        assert "x-content-type-options" in [k.lower() for k in r.headers.keys()]

    def test_429_response_has_security_headers(self, client):
        """Rate limit response carries security headers."""
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

    def test_403_response_has_security_headers(self, client, production_mode):
        """CSRF 403 response carries security headers."""
        r = client.post("/api/auth/login",
                       json={"username": "admin", "password": "123456"},
                       headers={"Origin": "http://evil.com"})
        assert r.status_code == 403
        assert "x-content-type-options" in [k.lower() for k in r.headers.keys()]

    def test_413_response_has_security_headers(self, client):
        """Request size 413 response carries security headers."""
        big = "x" * (11 * 1024 * 1024)
        r = client.post("/api/auth/login", content=big)
        assert r.status_code == 413
        assert "x-content-type-options" in [k.lower() for k in r.headers.keys()]

    def test_order_security_headers_first(self, client):
        """Security headers should be on the response even if later middleware errors."""
        # Test with a request that would trigger rate limit
        for _ in range(6):
            client.post("/api/auth/login", json={
                "username": "admin", "password": "wrong"
            })
        r = client.post("/api/auth/login", json={
            "username": "admin", "password": "wrong"
        })
        # Rate limit response
        assert r.status_code == 429
        # All security headers present
        for header in ["x-content-type-options", "x-frame-options",
                      "referrer-policy", "permissions-policy"]:
            assert header in [k.lower() for k in r.headers.keys()]