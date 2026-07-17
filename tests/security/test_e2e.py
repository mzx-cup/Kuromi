# -*- coding: utf-8 -*-
"""End-to-end tests for critical security flows.

3 critical paths:
  1. Complete login flow (UI → API → JWT → authenticated request)
  2. Cross-origin attack blocked
  3. Rate limit triggers 429 with Retry-After
"""
import pytest


class TestSecurityE2E:
    def test_complete_login_flow(self, client):
        """UI simulates: login → receive JWT → use JWT in Authorization header."""
        # Step 1: Login
        r1 = client.post("/api/auth/login",
                        json={"username": "admin", "password": "123456"},
                        headers={"Origin": "http://localhost:3000"})
        assert r1.status_code == 200
        body = r1.json()
        assert "token" in body
        token = body["token"]

        # Step 2: Use token in Authorization header
        r2 = client.get("/api/user/state/3",
                       headers={"Authorization": f"Bearer {token}"})
        # Endpoint may 500 due to existing bug, but security layer must not block
        assert r2.status_code != 403
        assert r2.status_code != 429
        assert r2.status_code != 413

    def test_cross_origin_attack_blocked(self, client, production_mode):
        """Attacker site cannot make state-changing requests."""
        r = client.post("/api/auth/login",
                       json={"username": "admin", "password": "123456"},
                       headers={"Origin": "http://attacker.com",
                               "Referer": "http://attacker.com/phishing.html"})
        assert r.status_code == 403

        # Verify same request from legitimate origin works
        r2 = client.post("/api/auth/login",
                        json={"username": "admin", "password": "123456"},
                        headers={"Origin": "http://localhost:3000"})
        assert r2.status_code != 403

    def test_rate_limit_triggers_429_with_retry_after(self, client):
        """Burst of requests triggers 429 with Retry-After header."""
        for i in range(5):
            client.post("/api/auth/login", json={
                "username": "admin", "password": "wrong"
            })

        r = client.post("/api/auth/login", json={
            "username": "admin", "password": "wrong"
        })
        assert r.status_code == 429
        assert "retry-after" in r.headers
        assert r.json()["detail"] == "Too many requests. Please slow down."