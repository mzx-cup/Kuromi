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
        agents = data["agents"]
        assert len(agents) == 9
        ids = {a["id"] for a in agents}
        assert ids == {
            "echo", "profiler", "planner",
            "document_generator", "exercise_generator",
            "mindmap_generator", "video_content",
            "resource_push", "evaluator",
        }

    def test_catalog_pipeline_has_stages(self, client):
        resp = client.get("/api/agents/catalog")
        pipeline = resp.json()["pipeline"]
        stages = {p["stage"] for p in pipeline}
        assert stages == {"pre", "main", "parallel", "post"}
        parallel = next(p for p in pipeline if p["stage"] == "parallel")
        assert parallel["max_concurrent"] == 4
        assert parallel["agents"] == [
            "document_generator", "exercise_generator",
            "mindmap_generator", "video_content",
        ]