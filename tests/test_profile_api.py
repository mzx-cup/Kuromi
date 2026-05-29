# -*- coding: utf-8 -*-
"""Tests for GET /api/profile/{user_id} endpoint."""

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestProfileApi:
    def test_get_profile_returns_aggregated_data(self, client):
        resp = client.get("/api/profile/test_user_123")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "learning_traits" in data["profile"]
        assert "personality_traits" in data["profile"]
        assert "goals_interests" in data["profile"]
        assert "last_updated" in data["profile"]

    def test_get_profile_empty_user(self, client):
        resp = client.get("/api/profile/nonexistent_user_999")
        assert resp.status_code == 200
        data = resp.json()
        assert data["profile"]["learning_traits"] == []
