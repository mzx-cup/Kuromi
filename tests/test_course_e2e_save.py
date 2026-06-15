# -*- coding: utf-8 -*-
"""Phase 2 — 课程生成端到端冒烟测试.

复现用户场景:
  OpenMAIC 输入主题 → 3 轮脑暴 → 锁定大纲 → 9 件套 SSE 流 → 落盘 → 跳到 classroom

覆盖:
  1. 5 个 Phase 2 新端点 + /api/v2/course/save + GET /api/v2/course/{id} + /api/v2/classroom/{id}
  2. bundle_complete 事件含 9 件
  3. /save 落盘后 GET /course/{id} 能拿回 9 件
  4. CourseData.outlines 字段从 outline.scenes 翻译过来 (id: int, key_points 列表)

不连真实 LLM, mock 全部 llm_json 调用; 不连真实 DB, 接受 save_classroom_record 失败兜底.
"""
from __future__ import annotations

import asyncio
import json
import os
import tempfile
from pathlib import Path

_tmpdir = tempfile.mkdtemp(prefix="xs-audit-e2e-")
os.environ.setdefault("XINSHI_AUDIT_LOG", str(Path(_tmpdir) / "audit.log"))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.services import course_brainstorm, course_bundle  # noqa: E402
from app.services.course_schemas import COMPONENT_NAMES  # noqa: E402
from main import app  # noqa: E402


# ============================================================
# 共享 mock: 脑暴 + 9 件套共用 llm_json
# ============================================================

SAMPLE_OUTLINE = {
    "title": "Python 数据分析入门",
    "description": "3 场景 OBG 课程",
    "scenes": [
        {"id": "s1", "title": "基础语法", "description": "变量/循环/函数", "key_points": ["变量", "循环"], "type": "slide", "duration_min": 10},
        {"id": "s2", "title": "pandas 入门", "description": "DataFrame/读文件/聚合", "key_points": ["pandas"], "type": "slide", "duration_min": 15},
        {"id": "s3", "title": "实战项目", "description": "销售数据分析报告", "key_points": ["分析"], "type": "slide", "duration_min": 20},
    ],
}


def _mock_artifact_for(prompt_id: str) -> dict:
    if prompt_id == "lesson_plan":
        return {
            "plans": {
                "s1": {"objectives": ["理解基础"], "key_points": ["A"], "duration_min": 10, "methods": ["讲解"], "blackboard": "板书 1"},
            },
        }
    if prompt_id == "knowledge_graph":
        return {
            "nodes": [{"id": "n1", "label": "节点1", "layer": 0}],
            "edges": [{"from": "n1", "to": "n1", "label": ""}],
        }
    if prompt_id == "radar_init":
        return {
            "knowledge_mastery": 60.0,
            "code_skill": 50.0,
            "cognitive_level": 70.0,
            "learning_goal": 80.0,
            "weakness": 40.0,
            "focus_level": 65.0,
            "post_course_estimate": {"knowledge_mastery": 75.0, "code_skill": 70.0},
        }
    if prompt_id == "project_brief":
        return {
            "title": "实战项目",
            "scenario": "场景描述",
            "background": "背景",
            "requirements": ["需求1"],
            "acceptance": ["验收1"],
            "milestones": [{"title": "M1", "description": "d", "deliverable": "v"}],
            "estimated_hours": 8,
            "difficulty": "medium",
        }
    if prompt_id == "case_study":
        return {
            "title": "案例",
            "story": "故事",
            "decision_points": ["决策1"],
            "reflection": ["反思1"],
            "takeaway": "启示",
        }
    if prompt_id == "exercises":
        return {
            "questions": [{
                "id": 1, "type": "single", "stem": "Q1",
                "options": ["A", "B"], "answer": 0, "rubric": "对",
            }],
            "by_scene": {"s1": [1]},
        }
    if prompt_id == "survey":
        return {
            "sections": [{
                "title": "前测", "description": "d",
                "questions": [{"id": 1, "type": "text", "stem": "你学过什么?", "options": [], "required": True}],
            }],
            "estimated_minutes": 5,
        }
    raise RuntimeError(f"unknown prompt_id: {prompt_id}")


@pytest.fixture
def mock_llm(monkeypatch):
    """替换脑暴 + 9 件套 共用的 llm_json."""

    async def fake_brainstorm_llm(prompt_id, variables, schema, **kwargs):
        if prompt_id == "brainstorm_question":
            slot = variables.get("slot") or variables.get("next_slot") or "goal"
            return schema.model_validate({
                "question": f"问题 {slot}",
                "options": ["A", "B", "C", "D"],
            })
        if prompt_id == "brainstorm_decide_obg_pbl":
            return schema.model_validate({
                "mode": "obg",
                "rationale": "e2e mock",
                "outline": SAMPLE_OUTLINE,
            })
        raise RuntimeError(f"unexpected prompt_id in brainstorm mock: {prompt_id}")

    monkeypatch.setattr(course_brainstorm, "llm_json", fake_brainstorm_llm)

    def fake_portrait(student_id):
        return {"learning_goal": {"current": "求职"}, "knowledge_mastery": {"level": "intermediate"}}
    monkeypatch.setattr(course_brainstorm, "get_student_portrait", fake_portrait)

    async def fake_bundle_llm(prompt_id, variables, schema, **kwargs):
        return schema.model_validate(_mock_artifact_for(prompt_id))
    monkeypatch.setattr(course_bundle, "llm_json", fake_bundle_llm)

    course_brainstorm.BRAINSTORM_STORE.clear()
    yield
    course_brainstorm.BRAINSTORM_STORE.clear()


# ============================================================
# E2E: 5 个新端点 + save + 读回
# ============================================================


def _parse_sse_events(text: str) -> list[dict]:
    """从 SSE 文本里抠出 {event, data} 事件列表."""
    events = []
    for raw in text.split("\n\n"):
        raw = raw.strip()
        if not raw:
            continue
        ev_type = None
        ev_data = None
        for line in raw.split("\n"):
            if line.startswith("event:"):
                ev_type = line[len("event:"):].strip()
            elif line.startswith("data:"):
                payload = line[len("data:"):].strip()
                try:
                    ev_data = json.loads(payload)
                except json.JSONDecodeError:
                    ev_data = payload
        if ev_type:
            events.append({"event": ev_type, "data": ev_data})
    return events


class TestEndToEndFlow:
    def test_full_happy_path(self, mock_llm):
        """复现用户场景: 输入主题 → 脑暴 → 9 件套 → 落盘 → 读回."""
        client = TestClient(app)
        student_id = "42"

        # 1. 启动脑暴
        r = client.post(
            "/api/v2/course/brainstorm/start",
            json={"requirement": "我想学 Python 数据分析", "student_id": student_id},
        )
        assert r.status_code == 200, r.text
        start = r.json()
        bsid = start["brainstorm_id"]
        assert start["slot"] == "goal"
        assert start["turn"] == 1
        assert isinstance(start["options"], list) and len(start["options"]) >= 2

        # 2. 走 3 轮
        for i, choice in enumerate(["求职", "零基础", "案例驱动"]):
            r = client.post(
                f"/api/v2/course/brainstorm/{bsid}/turn",
                json={"brainstorm_id": bsid, "user_choice": choice},
            )
            assert r.status_code == 200, r.text
            data = r.json()
            if i < 2:
                assert data["done"] is False
                assert data["turn"] == i + 2
            else:
                # 第 3 轮 done
                assert data["done"] is True
                assert "scenes" in data["outline"]

        # 3. 锁定大纲
        r = client.post(
            f"/api/v2/course/brainstorm/{bsid}/confirm",
            json={"brainstorm_id": bsid, "obg_pbl_override": "obg"},
        )
        assert r.status_code == 200, r.text
        confirm = r.json()
        assert confirm["locked"] is True
        assert confirm["obg_pbl_mode"] == "obg"

        # 4. 9 件套 SSE 流
        with client.stream(
            "POST",
            "/api/v2/course/bundle/generate/stream",
            json={
                "requirement": "我想学 Python 数据分析",
                "student_id": student_id,
                "brainstorm_id": bsid,
                "enabled_components": list(COMPONENT_NAMES),
                "obg_pbl_mode": "obg",
            },
        ) as resp:
            assert resp.status_code == 200, f"SSE 非 200: {resp.status_code}"
            text = "".join(chunk for chunk in resp.iter_text())

        events = _parse_sse_events(text)
        starts = [e for e in events if e["event"] == "component_start"]
        readys = [e for e in events if e["event"] == "component_ready"]
        completes = [e for e in events if e["event"] == "bundle_complete"]
        assert len(starts) == 9, f"期望 9 个 component_start, 实得 {len(starts)}"
        assert len(readys) == 9, f"期望 9 个 component_ready, 实得 {len(readys)}"
        assert len(completes) == 1, f"期望 1 个 bundle_complete, 实得 {len(completes)}"
        bundle = completes[0]["data"]["bundle"]
        assert set(bundle["components"].keys()) == set(COMPONENT_NAMES)

        # 5. 模拟前端 _buildCourseData: outline.scenes → CourseData.outlines
        outline = confirm["outline"]
        outlines = []
        for i, s in enumerate(outline["scenes"]):
            raw_id = s.get("id")
            int_id = i + 1
            if isinstance(raw_id, str) and raw_id.startswith("s"):
                try:
                    int_id = int(raw_id[1:])
                except ValueError:
                    int_id = i + 1
            elif isinstance(raw_id, int):
                int_id = raw_id
            outlines.append({
                "id": int_id,
                "title": s.get("title", ""),
                "type": s.get("type", "slide"),
                "points": len(s.get("key_points", []) or []),
                "key_points": list(s.get("key_points", []) or []),
                "description": s.get("description", ""),
            })
        course_data = {
            "courseId": "",
            "title": outline.get("title", ""),
            "outlines": outlines,
            "slides": [],
            "slides_v2": [],
            "agent_team": [],
            "quiz_data": [],
            "exercise_data": [],
            "interactive_data": [],
            "code_data": [],
            "tts_audio_urls": {},
            "scene_actions": [],
            "metadata": {
                "student_id": student_id,
                "requirement": "我想学 Python 数据分析",
                "brainstorm_id": bsid,
                "obg_pbl_mode": "obg",
                "generated_at": "2026-06-15T00:00:00Z",
            },
            "bundle": bundle,
        }
        # outlines 必须能塞进去 (CourseData schema 要求 int id)
        assert all(isinstance(o["id"], int) for o in course_data["outlines"])

        # 6. POST /api/v2/course/save
        r = client.post(
            "/api/v2/course/save",
            json={
                "course_data": course_data,
                "student_id": student_id,
                "ppt_pages": bundle["components"]["ppt"].get("slide_count", 0),
            },
        )
        assert r.status_code == 200, r.text
        save = r.json()
        assert save["success"] is True
        course_id = save["course_id"]
        assert course_id

        # 7. GET /api/v2/course/{id} 拿回 9 件
        r = client.get(f"/api/v2/course/{course_id}")
        assert r.status_code == 200, r.text
        loaded = r.json()
        assert loaded["courseId"] == course_id
        assert loaded["title"] == "Python 数据分析入门"
        assert loaded["bundle"] is not None
        assert set(loaded["bundle"]["components"].keys()) == set(COMPONENT_NAMES)
        # outlines 也回来了
        assert len(loaded["outlines"]) == 3
        assert loaded["outlines"][0]["id"] == 1
        assert loaded["outlines"][0]["title"] == "基础语法"
        assert loaded["outlines"][0]["key_points"] == ["变量", "循环"]

        # 8. /api/v2/classroom/{id} — DB 记录 (save_classroom_record 失败兜底不影响)
        r = client.get(f"/api/v2/classroom/{course_id}")
        if r.status_code == 200:
            rec = r.json()
            assert rec["success"] is True
            # record 里应该能找到 title
            if rec.get("record"):
                assert rec["record"]["title"] == "Python 数据分析入门"
        else:
            # DB 不可用时这是可接受的 (代码里有 try/except)
            assert r.status_code in (404, 500)

    def test_save_rejects_missing_course_data(self, mock_llm):
        client = TestClient(app)
        r = client.post("/api/v2/course/save", json={"student_id": "1"})
        assert r.status_code in (400, 422)

    def test_save_generates_id_when_blank(self, mock_llm):
        """前端不传 courseId, 后端应自己生成 course_{ts}_{hex}."""
        client = TestClient(app)
        cd = {
            "courseId": "",
            "title": "测试课",
            "outlines": [],
            "metadata": {"student_id": "1"},
        }
        r = client.post(
            "/api/v2/course/save",
            json={"course_data": cd, "student_id": "1"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["success"] is True
        assert body["course_id"].startswith("course_")
