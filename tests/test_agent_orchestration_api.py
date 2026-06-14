# -*- coding: utf-8 -*-
"""Tests for GET /api/agents/catalog endpoint.

Catalog 返回 agent 目录与流水线定义；前端 Agent 编排控制塔据此渲染 flow-nodes。
"""

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestCatalogApi:
    def test_catalog_returns_agents(self, client):
        resp = client.get("/api/agents/catalog")
        assert resp.status_code == 200
        data = resp.json()
        assert "agents" in data
        assert "pipeline" in data
        ids = {a["id"] for a in data["agents"]}
        assert "profiler" in ids
        assert "planner" in ids

    def test_catalog_pipeline_has_stages(self, client):
        resp = client.get("/api/agents/catalog")
        stages = {p["stage"] for p in resp.json()["pipeline"]}
        assert {"pre", "main", "parallel", "post"}.issubset(stages)