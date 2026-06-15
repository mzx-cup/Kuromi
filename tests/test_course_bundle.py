# -*- coding: utf-8 -*-
"""Phase 2 — 9 件套课程包单测.

覆盖:
- build_outline_summary / build_bundle_context 纯函数
- generate_bundle_sync: 9 件全跑 / 单件失败不影响整体 / 全局 fallback
- generate_bundle (SSE): 9 个 component_ready 事件 + bundle_complete
- Semaphore(3) 并发上限 (通过 _run_one_component mock 验证)
- disabled component 不出现在结果中
"""
from __future__ import annotations

import asyncio
import os
import tempfile
import time
from pathlib import Path

_tmpdir = tempfile.mkdtemp(prefix="xs-audit-")
os.environ.setdefault("XINSHI_AUDIT_LOG", str(Path(_tmpdir) / "audit.log"))

import pytest  # noqa: E402

from app.services import course_bundle  # noqa: E402
from app.services.course_bundle import (  # noqa: E402
    BUNDLE_CONCURRENCY,
    build_bundle_context,
    build_outline_summary,
    generate_bundle,
    generate_bundle_sync,
)
from app.services.course_schemas import COMPONENT_NAMES  # noqa: E402


SAMPLE_OUTLINE = {
    "title": "Python 数据分析入门",
    "description": "从零到上手销售数据分析",
    "mode": "obg",
    "rationale": "用户目标为求职",
    "scenes": [
        {"id": "s1", "title": "基础语法", "description": "变量循环", "key_points": ["语法"], "type": "slide", "duration_min": 10},
        {"id": "s2", "title": "pandas 入门", "description": "DataFrame", "key_points": ["pandas"], "type": "slide", "duration_min": 15},
        {"id": "s3", "title": "实战项目", "description": "销售分析", "key_points": ["实战"], "type": "slide", "duration_min": 20},
    ],
}

SAMPLE_SLOTS = {
    "goal": "求职",
    "base": "零基础",
    "path": "案例驱动",
    "case": "电商销售",
}


# ============================================================
# 纯函数
# ============================================================

class TestBuildOutlineSummary:
    def test_basic(self):
        s = build_outline_summary(SAMPLE_OUTLINE)
        assert s["title"] == "Python 数据分析入门"
        assert s["total_scenes"] == 3
        assert s["estimated_min"] == 45
        assert s["scene_titles"] == ["基础语法", "pandas 入门", "实战项目"]

    def test_empty_outline(self):
        s = build_outline_summary({})
        assert s["title"] == ""
        assert s["total_scenes"] == 0
        assert s["estimated_min"] == 0

    def test_malformed_scenes_ignored(self):
        s = build_outline_summary({"scenes": [None, "str", {"title": "ok"}]})
        # 非 dict 场景被 _if isinstance 过滤; 第 3 个被收
        assert s["scene_titles"] == ["ok"]


class TestBuildBundleContext:
    def test_basic(self):
        ctx = build_bundle_context(SAMPLE_OUTLINE, SAMPLE_SLOTS)
        assert ctx["course_title"] == "Python 数据分析入门"
        assert ctx["slot_goal"] == "求职"
        assert ctx["slot_base"] == "零基础"
        assert ctx["slot_case"] == "电商销售"
        assert ctx["obg_pbl_mode"] == "obg"
        assert "scenes_json" in ctx
        assert "pandas" in ctx["scenes_json"]

    def test_missing_slots_filled_with_default(self):
        ctx = build_bundle_context(SAMPLE_OUTLINE, {})
        assert "未填" in ctx["slot_goal"]
        assert "未填" in ctx["slot_base"]
        assert "未填" in ctx["slot_path"]

    def test_portrait_none_safe(self):
        ctx = build_bundle_context(SAMPLE_OUTLINE, SAMPLE_SLOTS, portrait=None)
        # 默认值都到位
        assert "画像未提供" in ctx["learning_goals"]


# ============================================================
# generate_bundle_sync — 9 件全跑
# ============================================================

# 各 prompt_id 的 mock 返回值 — 必须符合对应 Pydantic schema
def _mock_artifact_for(prompt_id: str, scene_index: int = 0) -> dict:
    if prompt_id == "lesson_plan":
        return {
            "plans": {
                "s1": {
                    "objectives": ["理解基础"],
                    "key_points": ["A", "B"],
                    "duration_min": 10,
                    "methods": ["讲解"],
                    "blackboard": "板书 1",
                }
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
            "post_course_estimate": {
                "knowledge_mastery": 75.0,
                "code_skill": 70.0,
            },
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
def mock_llm_json(monkeypatch):
    """替换 llm_json, 9 件 prompt 各回一份合规 Pydantic 实例."""
    async def fake_llm_json(prompt_id, variables, schema, **kwargs):
        data = _mock_artifact_for(prompt_id)
        return schema.model_validate(data)
    monkeypatch.setattr(course_bundle, "llm_json", fake_llm_json)
    # exercises 内部用同一个 llm_json, 上面已经覆盖
    return fake_llm_json


class TestGenerateBundleSync:
    @pytest.mark.asyncio
    async def test_all_nine_components(self, mock_llm_json):
        bundle = await generate_bundle_sync(SAMPLE_OUTLINE, SAMPLE_SLOTS)
        assert set(bundle.components.keys()) == set(COMPONENT_NAMES)
        assert len(bundle.components) == 9

    @pytest.mark.asyncio
    async def test_outline_reuses_upstream(self, mock_llm_json):
        bundle = await generate_bundle_sync(SAMPLE_OUTLINE, SAMPLE_SLOTS)
        # outline 是上游脑暴产物, 不调 LLM, 直接透传
        assert "scenes" in bundle.components["outline"]
        assert len(bundle.components["outline"]["scenes"]) == 3

    @pytest.mark.asyncio
    async def test_ppt_reuses_upstream(self, mock_llm_json):
        bundle = await generate_bundle_sync(SAMPLE_OUTLINE, SAMPLE_SLOTS)
        # ppt 是占位 PPTArtifact(slide_count=0, slide_titles=[]), 不调 LLM
        assert bundle.components["ppt"]["slide_count"] == 0
        assert bundle.components["ppt"]["slide_titles"] == []

    @pytest.mark.asyncio
    async def test_enabled_components_subset(self, mock_llm_json):
        only = ["outline", "plan", "ppt"]
        bundle = await generate_bundle_sync(SAMPLE_OUTLINE, SAMPLE_SLOTS, enabled_components=only)
        assert set(bundle.components.keys()) == set(only)

    @pytest.mark.asyncio
    async def test_one_component_failure_others_ok(self, monkeypatch):
        async def flaky_llm(prompt_id, variables, schema, **kwargs):
            if prompt_id == "case_study":
                raise RuntimeError("mock LLM down for case")
            return schema.model_validate(_mock_artifact_for(prompt_id))
        monkeypatch.setattr(course_bundle, "llm_json", flaky_llm)
        bundle = await generate_bundle_sync(SAMPLE_OUTLINE, SAMPLE_SLOTS)
        assert "case" in bundle.components
        assert bundle.components["case"]["status"] == "fallback"
        # 其他 8 件仍然 ok
        for n in COMPONENT_NAMES:
            if n == "case": continue
            if n == "outline":
                assert "scenes" in bundle.components[n]
            elif n == "ppt":
                assert "slide_count" in bundle.components[n]
            else:
                # plan/graph/radar/project/exercises/survey 全部应该有数据
                assert bundle.components[n], f"{n} should be populated"
        assert "case" in bundle.fallback_components()

    @pytest.mark.asyncio
    async def test_obg_pbl_mode_propagated(self, mock_llm_json):
        bundle = await generate_bundle_sync(SAMPLE_OUTLINE, SAMPLE_SLOTS)
        assert bundle.obg_pbl_mode == "obg"
        # rationale 来自 SAMPLE_OUTLINE["rationale"] = "用户目标为求职"
        assert "用户目标" in bundle.obg_pbl_rationale or bundle.obg_pbl_rationale == ""

    @pytest.mark.asyncio
    async def test_outline_summary_in_bundle(self, mock_llm_json):
        bundle = await generate_bundle_sync(SAMPLE_OUTLINE, SAMPLE_SLOTS)
        assert bundle.outline_summary["total_scenes"] == 3
        assert bundle.outline_summary["estimated_min"] == 45


# ============================================================
# generate_bundle — SSE 流
# ============================================================

class TestGenerateBundleStream:
    @pytest.mark.asyncio
    async def test_yields_component_start_then_ready(self, mock_llm_json):
        events = []
        async for ev in generate_bundle(SAMPLE_OUTLINE, SAMPLE_SLOTS):
            events.append(ev)
        starts = [e for e in events if e["type"] == "component_start"]
        readys = [e for e in events if e["type"] == "component_ready"]
        assert len(starts) == 9
        assert len(readys) == 9
        names_started = set(e["name"] for e in starts)
        names_ready = set(e["name"] for e in readys)
        assert names_started == set(COMPONENT_NAMES)
        assert names_ready == set(COMPONENT_NAMES)

    @pytest.mark.asyncio
    async def test_final_bundle_complete_event(self, mock_llm_json):
        events = []
        async for ev in generate_bundle(SAMPLE_OUTLINE, SAMPLE_SLOTS):
            events.append(ev)
        completes = [e for e in events if e["type"] == "bundle_complete"]
        assert len(completes) == 1
        bundle_dict = completes[0]["bundle"]
        assert "components" in bundle_dict
        assert len(bundle_dict["components"]) == 9

    @pytest.mark.asyncio
    async def test_failure_event_has_status_fallback(self, monkeypatch):
        async def flaky(prompt_id, variables, schema, **kwargs):
            if prompt_id == "knowledge_graph":
                raise RuntimeError("mock failure")
            return schema.model_validate(_mock_artifact_for(prompt_id))
        monkeypatch.setattr(course_bundle, "llm_json", flaky)
        events = []
        async for ev in generate_bundle(SAMPLE_OUTLINE, SAMPLE_SLOTS):
            events.append(ev)
        graph_ready = [e for e in events if e["type"] == "component_ready" and e["name"] == "graph"]
        assert graph_ready
        assert graph_ready[0]["payload"]["status"] == "fallback"


# ============================================================
# Semaphore(3) 并发上限
# ============================================================

class TestConcurrency:
    @pytest.mark.asyncio
    async def test_semaphore_value_is_3(self):
        assert BUNDLE_CONCURRENCY == 3

    @pytest.mark.asyncio
    async def test_peak_concurrent_le_3(self, monkeypatch):
        """通过 mock 记录 _run_one_component 内部, 验证 sem=3 真的限制了并发."""
        from app.services import course_bundle as cb
        peak = 0
        current = 0
        lock = asyncio.Lock()

        original_run = cb._run_one_component

        async def slow_run(name, coro_factory, sem):
            nonlocal peak, current
            async with sem:
                async with lock:
                    current += 1
                    peak = max(peak, current)
                await asyncio.sleep(0.05)  # 模拟 LLM 延迟
                async with lock:
                    current -= 1
                return name, {"status": "ok", "name": name, "mock": True}

        monkeypatch.setattr(cb, "_run_one_component", slow_run)
        # 也覆盖 _run_one_component 在 generate_bundle 内引用的入口
        # 上面 _run_one_component 是同模块函数引用, 重新 monkeypatch 后会重新读取
        # 跑 sync 路径验证
        bundle = await cb.generate_bundle_sync(
            SAMPLE_OUTLINE, SAMPLE_SLOTS,
            enabled_components=["plan", "graph", "radar", "project", "case", "exercises", "survey"],
        )
        # 7 件 LLM 件, sem=3, peak 应为 3
        assert peak <= 3
        assert peak >= 2  # 至少有 2 件在跑才能验证并发
        # 7 件都应返回
        assert len(bundle.components) == 7


# ============================================================
# Disabled components 不出现
# ============================================================

class TestDisabledComponents:
    @pytest.mark.asyncio
    async def test_excludes_disabled(self, mock_llm_json):
        only_one = ["plan"]
        bundle = await generate_bundle_sync(SAMPLE_OUTLINE, SAMPLE_SLOTS, enabled_components=only_one)
        assert "plan" in bundle.components
        assert "graph" not in bundle.components
        assert "case" not in bundle.components
        assert "radar" not in bundle.components

    @pytest.mark.asyncio
    async def test_none_enabled_falls_back_to_all(self, mock_llm_json):
        # 设计选择: 空 list = None = 用全部 (与 enabled_components=None 等价)
        bundle = await generate_bundle_sync(SAMPLE_OUTLINE, SAMPLE_SLOTS, enabled_components=[])
        assert len(bundle.components) == 9


# ============================================================
# Fallback 形状
# ============================================================

class TestFallbackShape:
    def test_fallback_payload_shape(self):
        p = course_bundle._fallback_payload("plan", "LLM 暂不可用")
        assert p["status"] == "fallback"
        assert "占位生成" in p["note"]
        assert p["schema_hint"]["component"] == "plan"
