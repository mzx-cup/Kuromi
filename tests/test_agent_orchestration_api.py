# -*- coding: utf-8 -*-
"""Tests for GET /api/agents/catalog endpoint.

Catalog 返回 agent 目录与流水线定义；前端 Agent 编排控制塔据此渲染 flow-nodes。
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

import app.api.agent_orchestration as ao_module
from agents import AgentStepLog
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


class TestExecuteApi:
    def test_execute_emits_agent_step_event(self, monkeypatch):
        """POST /api/agents/execute 应通过 SSE 流至少下发一个 agent_step 事件.

        用假 controller 替换真实 create_default_controller,避免真实 LLM 调用.
        """

        class FakeController:
            async def execute(self, state, on_step_complete=None):
                if on_step_complete:
                    log1 = AgentStepLog(
                        agent_name="profiler", agent_role="画像分析",
                        input_summary="in1", output_summary="out1",
                        processing_time_ms=100, status="success",
                        error_message="", timestamp=datetime.now(),
                    )
                    await on_step_complete(log1)
                # 不等真实完成,直接结束 (run_controller 的 finally 会下发 sentinel)

        monkeypatch.setattr(ao_module, "create_default_controller", FakeController)

        client = TestClient(app)
        with client.stream(
            "POST", "/api/agents/execute",
            json={"student_id": "u1", "user_input": "hi"},
        ) as r:
            assert r.status_code == 200
            seen_events = set()
            for line in r.iter_lines():
                if line.startswith("event:"):
                    seen_events.add(line.split(":", 1)[1].strip())
                if "agent_step" in seen_events:
                    break

        assert "agent_step" in seen_events
        assert "heartbeat" in seen_events
