# -*- coding: utf-8 -*-
"""Tests for CORS strict configuration.

Verifies:
  - No wildcard origin allowed (anti-pattern fix)
  - Localhost defaults present
  - Allowed origins return correct CORS headers
  - Disallowed origins do not echo back
"""
from app.core.security_config import get_security_config, reset_security_config


class TestCORSConfiguration:
    def test_wildcard_origin_not_in_defaults(self):
        reset_security_config()
        cfg = get_security_config()
        assert "*" not in cfg.allowed_origins

    def test_localhost_in_defaults(self):
        reset_security_config()
        cfg = get_security_config()
        localhost_origins = [o for o in cfg.allowed_origins if "localhost" in o]
        assert len(localhost_origins) >= 3

    def test_env_override_replaces_defaults(self, monkeypatch):
        monkeypatch.setenv(
            "SECURITY_ALLOWED_ORIGINS",
            "https://prod.example.com"
        )
        cfg = SecurityConfig()
        assert cfg.allowed_origins == ["https://prod.example.com"]


class TestCORSPreflight:
    def test_preflight_allowed_origin_returns_acao(self, client):
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        }
        r = client.options("/api/auth/login", headers=headers)
        # CORS preflight should echo back the allowed origin
        acao = r.headers.get("access-control-allow-origin", "")
        assert acao == "http://localhost:3000"

    def test_preflight_disallowed_origin_no_acao(self, client):
        headers = {
            "Origin": "http://evil.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        }
        r = client.options("/api/auth/login", headers=headers)
        # Disallowed origin should NOT get CORS headers
        acao = r.headers.get("access-control-allow-origin", "")
        assert acao != "http://evil.com"

    def test_actual_request_allowed_origin(self, client):
        headers = {"Origin": "http://localhost:3000"}
        r = client.get("/login.html", headers=headers)
        assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"


class TestCORSCredentials:
    def test_credentials_still_allowed_for_explicit_origins(self, client):
        # Browser sends with credentials — CORS allows this when origin is in allowlist
        headers = {
            "Origin": "http://localhost:3000",
            "Cookie": "session=abc123",
        }
        r = client.get("/login.html", headers=headers)
        assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"
        assert r.headers.get("access-control-allow-credentials") == "true"
