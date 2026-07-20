# -*- coding: utf-8 -*-
"""Tests for SecurityHeadersMiddleware.

Verifies every response (including errors) gets the security headers.
"""
from app.core.security_config import SECURITY_HEADERS, get_security_config


class TestSecurityHeadersAdded:
    def test_fixed_headers_present(self, client):
        r = client.get("/login.html")
        for header in SECURITY_HEADERS.keys():
            assert header.lower() in [k.lower() for k in r.headers.keys()], (
                f"Missing header: {header}"
            )

    def test_x_content_type_options_value(self, client):
        r = client.get("/login.html")
        assert r.headers["X-Content-Type-Options"] == "nosniff"

    def test_x_frame_options_value(self, client):
        r = client.get("/login.html")
        assert r.headers["X-Frame-Options"] == "DENY"

    def test_xss_protection_value(self, client):
        r = client.get("/login.html")
        assert r.headers["X-XSS-Protection"] == "1; mode=block"

    def test_referrer_policy_value(self, client):
        r = client.get("/login.html")
        assert "strict-origin" in r.headers["Referrer-Policy"]

    def test_permissions_policy_disables_sensors(self, client):
        r = client.get("/login.html")
        policy = r.headers["Permissions-Policy"]
        assert "geolocation=()" in policy
        assert "microphone=()" in policy
        assert "camera=()" in policy


class TestCSP:
    def test_csp_present(self, client):
        r = client.get("/login.html")
        assert "content-security-policy" in [k.lower() for k in r.headers.keys()]

    def test_csp_includes_self(self, client):
        r = client.get("/login.html")
        csp = r.headers["Content-Security-Policy"]
        assert "'self'" in csp
        assert "default-src" in csp

    def test_csp_customizable_via_env(self, client, monkeypatch):
        monkeypatch.setenv("SECURITY_CSP_POLICY", "default-src 'none'")
        from app.core.security_config import reset_security_config, get_security_config
        reset_security_config()
        r = client.get("/login.html")
        assert r.headers["Content-Security-Policy"] == "default-src 'none'"
        # Cleanup: reset singleton after this test
        reset_security_config()


class TestHSTS:
    def test_hsts_disabled_by_default(self, client):
        r = client.get("/login.html")
        assert "strict-transport-security" not in [k.lower() for k in r.headers.keys()]

    def test_hsts_enabled_when_configured(self, client, monkeypatch):
        monkeypatch.setenv("SECURITY_ENABLE_HSTS", "true")
        from app.core.security_config import reset_security_config
        reset_security_config()
        r = client.get("/login.html")
        assert "max-age=31536000" in r.headers["Strict-Transport-Security"]
        # Cleanup
        reset_security_config()


class TestHeadersOnErrorResponses:
    def test_404_response_has_security_headers(self, client):
        r = client.get("/nonexistent-route-12345")
        assert r.status_code == 404
        assert "x-content-type-options" in [k.lower() for k in r.headers.keys()]
        assert "x-frame-options" in [k.lower() for k in r.headers.keys()]

    def test_500_response_has_security_headers(self, client):
        # Trigger a 500 by sending invalid JSON to /api/auth/login
        r = client.post("/api/auth/login", data="not-json-at-all",
                       headers={"Content-Type": "application/json"})
        # Even errors should have security headers
        assert "x-content-type-options" in [k.lower() for k in r.headers.keys()]
