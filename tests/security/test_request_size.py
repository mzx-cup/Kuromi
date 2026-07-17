# -*- coding: utf-8 -*-
"""Tests for RequestSizeLimitMiddleware.

Verifies:
  - Normal requests allowed
  - Oversized requests rejected (413)
  - Streaming endpoints get higher limit
"""
import pytest


class TestRequestSizeLimit:
    def test_normal_size_allowed(self, client):
        """Small request body should pass."""
        r = client.post("/api/auth/login",
                       json={"username": "admin", "password": "123456"})
        assert r.status_code != 413

    def test_missing_content_length_allowed(self, client):
        """GET requests have no Content-Length — should pass."""
        r = client.get("/login.html")
        assert r.status_code != 413

    def test_oversized_normal_request_rejected(self, client):
        """11 MB body to non-streaming endpoint → 413."""
        big = "x" * (11 * 1024 * 1024)
        r = client.post("/api/auth/login", content=big)
        assert r.status_code == 413
        assert "too large" in r.json()["detail"].lower()

    def test_streaming_endpoint_higher_limit(self, client):
        """30 MB body to streaming endpoint should pass (50 MB limit)."""
        big = "x" * (30 * 1024 * 1024)
        # Use a streaming endpoint path
        r = client.post("/api/v2/chat/stream", content=big)
        assert r.status_code != 413

    def test_streaming_endpoint_still_has_limit(self, client):
        """60 MB body to streaming endpoint should fail (50 MB limit)."""
        big = "x" * (60 * 1024 * 1024)
        r = client.post("/api/v2/chat/stream", content=big)
        assert r.status_code == 413

    def test_invalid_content_length_rejected(self, client):
        """Malformed Content-Length header → 400."""
        r = client.post("/api/auth/login",
                       content="hello",
                       headers={"Content-Length": "not-a-number"})
        assert r.status_code in (400, 413)

    def test_size_limit_configurable_via_env(self, client, monkeypatch):
        """Custom size limit honored via env var."""
        monkeypatch.setenv("MAX_REQUEST_SIZE_MB", "5")
        from app.core.security_config import reset_security_config
        reset_security_config()

        # 6 MB should now fail
        big = "x" * (6 * 1024 * 1024)
        r = client.post("/api/auth/login", content=big)
        assert r.status_code == 413

        # Cleanup
        reset_security_config()