# -*- coding: utf-8 -*-
"""Tests for GET /api/profile/portrait/{user_id} endpoint.

注意：历史版本曾提供 /api/profile/{user_id}，现已迁移到 /api/profile/portrait/{user_id}。
响应字段也从 `profile` 改为 `portrait`（portrait 内部仍含 learning_traits / personality_traits / goals_interests / last_updated）。
"""

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestProfileApi:
    def test_get_profile_returns_aggregated_data(self, client):
        resp = client.get("/api/profile/portrait/test_user_123")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        # 真实字段是 portrait（不是 profile）
        assert "portrait" in data
        # portrait 可能为 None（该用户没有画像），但不能是 profile 字段
        assert "profile" not in data

    def test_get_profile_empty_user(self, client):
        resp = client.get("/api/profile/portrait/nonexistent_user_999")
        assert resp.status_code == 200
        data = resp.json()
        # 不存在的用户：portrait 为 None
        assert data["portrait"] is None
