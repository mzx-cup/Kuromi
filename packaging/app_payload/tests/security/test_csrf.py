# -*- coding: utf-8 -*-
"""Tests for OriginCheckMiddleware (CSRF protection).

Verifies:
  - GET/HEAD/OPTIONS skip Origin check
  - POST/PUT/DELETE/PATCH require valid Origin or Referer
  - dev_mode bypasses check entirely
  - production mode rejects unauthorized origins
"""
import pytest


class TestOriginCheckDevMode:
    def test_dev_mode_post_without_origin_allowed(self, client):
        """In dev mode (default), CSRF check is skipped."""
        r = client.post("/api/auth/login", json={
            "username": "admin", "password": "123456"
        })
        assert r.status_code != 403

    def test_dev_mode_post_with_any_origin_allowed(self, client):
        r = client.post("/api/auth/login",
                       json={"username": "admin", "password": "123456"},
                       headers={"Origin": "http://random.com"})
        assert r.status_code != 403


class TestOriginCheckProductionMode:
    def test_get_skips_check_in_production(self, client, production_mode):
        r = client.get("/login.html")
        assert r.status_code != 403

    def test_post_without_origin_rejected(self, client, production_mode):
        r = client.post("/api/auth/login", json={
            "username": "admin", "password": "123456"
        })
        assert r.status_code == 403
        assert "Cross-origin" in r.json()["detail"] or "Origin" in r.json()["detail"]

    def test_post_with_valid_origin_allowed(self, client, production_mode):
        headers = {"Origin": "http://localhost:3000"}
        r = client.post("/api/auth/login",
                       json={"username": "admin", "password": "123456"},
                       headers=headers)
        assert r.status_code != 403

    def test_post_with_invalid_origin_rejected(self, client, production_mode):
        headers = {"Origin": "http://evil.com"}
        r = client.post("/api/auth/login",
                       json={"username": "admin", "password": "123456"},
                       headers=headers)
        assert r.status_code == 403

    def test_post_with_referer_fallback(self, client, production_mode):
        """If Origin missing, Referer is checked."""
        headers = {"Referer": "http://localhost:3000/login.html"}
        r = client.post("/api/auth/login",
                       json={"username": "admin", "password": "123456"},
                       headers=headers)
        assert r.status_code != 403

    def test_post_with_invalid_referer_rejected(self, client, production_mode):
        headers = {"Referer": "http://evil.com/page"}
        r = client.post("/api/auth/login",
                       json={"username": "admin", "password": "123456"},
                       headers=headers)
        assert r.status_code == 403

    def test_put_requires_valid_origin(self, client, production_mode):
        """PUT is a state-changing method."""
        headers = {"Origin": "http://evil.com"}
        r = client.put("/api/user/state/3",
                      json={"preferred_language": "en-US"},
                      headers=headers)
        assert r.status_code == 403

    def test_delete_requires_valid_origin(self, client, production_mode):
        """DELETE is a state-changing method."""
        headers = {"Origin": "http://evil.com"}
        r = client.delete("/api/weather/clear/3", headers=headers)
        assert r.status_code == 403
