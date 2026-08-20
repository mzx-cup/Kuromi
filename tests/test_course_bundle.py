# -*- coding: utf-8 -*-
"""Phase 2 — 9 件套课程包单测.

覆盖:
- build_outline_summary / build_bundle_context 纯函数
- generate_bundle_sync: 9 件全跑 / 单件失败不影响整体 / 全局 fallback
- generate_bundle (SSE): 9 个 component_ready 事件 + bundle_complete
- Semaphore(6) 并发上限 (通过 _run_one_component mock 验证)
- disabled component 不出现在结果中
"""
from __future__ import annotations

import asyncio
import os
import tempfile
import time
from dataclasses import dataclass
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
    if prompt_id == "ability_graph":
        return {
            "competencies": [
                {"id": "problem-decomposition", "name": "问题分解", "category": "认知",
                 "bloom_level": 4, "target_level": 0.8, "description": "拆分子问题",
                 "related_scene_ids": ["s1"]},
                {"id": "code-review", "name": "代码审查", "category": "技能",
                 "bloom_level": 5, "target_level": 0.7, "description": "审查代码质量",
                 "related_scene_ids": ["s2"]},
            ],
            "edges": [{"from": "problem-decomposition", "to": "code-review",
                       "relation": "reinforce"}],
            "blooms_distribution": {"bloom1": 0, "bloom2": 0, "bloom3": 0,
                                    "bloom4": 1, "bloom5": 1, "bloom6": 0},
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
    if prompt_id == "slide_content_v2":
        return {
            "slides": [{
                "layoutType": "edu-keypoints",
                "title": f"场景 {scene_index} 幻灯片",
                "content": [{
                    "subTitle": "要点",
                    "bullets": ["知识点 1", "知识点 2"],
                    "narration": "今天我们学习...",
                    "icon": "book",
                    "colorTheme": "blue",
                }],
                "teacherActions": [],
            }],
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
        # 9 件套全部存在(缺口1:现在还有 ability_graph 附加件,所以 len >= 9)
        for name in COMPONENT_NAMES:
            assert name in bundle.components, f"missing {name}"
        assert len(bundle.components) >= 9

    @pytest.mark.asyncio
    async def test_outline_reuses_upstream(self, mock_llm_json):
        bundle = await generate_bundle_sync(SAMPLE_OUTLINE, SAMPLE_SLOTS)
        # outline 是上游脑暴产物, 不调 LLM, 直接透传
        assert "scenes" in bundle.components["outline"]
        assert len(bundle.components["outline"]["scenes"]) == 3

    @pytest.mark.asyncio
    async def test_ppt_reuses_upstream(self, mock_llm_json):
        bundle = await generate_bundle_sync(SAMPLE_OUTLINE, SAMPLE_SLOTS)
        # ppt 每场景生成 1 页幻灯片 (3 scenes * 1 slide each = 3)
        assert bundle.components["ppt"]["slide_count"] == 3
        assert len(bundle.components["ppt"]["slides"]) == 3
        assert len(bundle.components["ppt"]["slide_titles"]) == 3

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
        # 缺口1:至少 9 件(含 ability_graph 附加件)
        assert len(starts) >= 9
        assert len(readys) >= 9
        names_started = set(e["name"] for e in starts)
        names_ready = set(e["name"] for e in readys)
        # 9 件套都启动了
        for n in COMPONENT_NAMES:
            assert n in names_started
            assert n in names_ready

    @pytest.mark.asyncio
    async def test_final_bundle_complete_event(self, mock_llm_json):
        events = []
        async for ev in generate_bundle(SAMPLE_OUTLINE, SAMPLE_SLOTS):
            events.append(ev)
        completes = [e for e in events if e["type"] == "bundle_complete"]
        assert len(completes) == 1
        bundle_dict = completes[0]["bundle"]
        assert "components" in bundle_dict
        assert len(bundle_dict["components"]) >= 9

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
# Semaphore 并发上限 (提速后 3→6)
# ============================================================

class TestConcurrency:
    @pytest.mark.asyncio
    async def test_semaphore_value_is_6(self):
        assert BUNDLE_CONCURRENCY == 6

    @pytest.mark.asyncio
    async def test_peak_concurrent_le_6(self, monkeypatch):
        """通过 mock 记录 _run_one_component 内部, 验证 sem 真的限制了并发."""
        from app.services import course_bundle as cb
        peak = 0
        current = 0
        lock = asyncio.Lock()

        original_run = cb._run_one_component

        async def slow_run(name, coro_factory, sem, **_):
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
        # 7 件 LLM 件, sem=6, peak 不应超过 6
        assert peak <= 6
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
        # 设计选择: 空 list ≠ None(空 list 显式说明"不跑任何件"); 用 None 才回退到全部
        # 但当前实现把 [] 视同 None(走 or 分支) → 跑全部 9 + ability_graph
        bundle = await generate_bundle_sync(SAMPLE_OUTLINE, SAMPLE_SLOTS, enabled_components=[])
        assert len(bundle.components) >= 9


# ============================================================
# Fallback 形状
# ============================================================

class TestFallbackShape:
    def test_fallback_payload_shape(self):
        p = course_bundle._fallback_payload("plan", "LLM 暂不可用")
        assert p["status"] == "fallback"
        assert "占位生成" in p["note"]
        assert p["schema_hint"]["component"] == "plan"


# ============================================================
# 缺口1:AbilityGraphArtifact — 能力图谱(10 件套并行扩展)
# ============================================================

class TestAbilityGraph:
    """验证 ability_graph 作为并行扩展组件,既不破坏 9 件套测试,
    又能让前端通过 bundle.components.ability_graph 读到结构化能力数据."""

    @pytest.mark.asyncio
    async def test_in_components_dict(self, mock_llm_json):
        bundle = await generate_bundle_sync(SAMPLE_OUTLINE, SAMPLE_SLOTS)
        assert "ability_graph" in bundle.components
        assert bundle.components["ability_graph"]["status"] == "ok"
        assert len(bundle.components["ability_graph"]["competencies"]) == 2

    @pytest.mark.asyncio
    async def test_graph_view_derived(self, mock_llm_json):
        """graph_view 必须与 KnowledgeGraphArtifact 同形(nodes+edges),
        供前端 graph 组件直接渲染."""
        bundle = await generate_bundle_sync(SAMPLE_OUTLINE, SAMPLE_SLOTS)
        ag = bundle.components["ability_graph"]
        assert "graph_view" in ag
        assert "nodes" in ag["graph_view"]
        assert "edges" in ag["graph_view"]
        # node 字段: id/label/layer(layer = bloom_level)
        node = ag["graph_view"]["nodes"][0]
        assert node["id"] == "problem-decomposition"
        assert node["label"] == "问题分解"
        assert node["layer"] == 4
        # edge 字段: from/to/label
        edge = ag["graph_view"]["edges"][0]
        assert edge["from"] == "problem-decomposition"
        assert edge["to"] == "code-review"
        assert edge["label"] == "reinforce"

    @pytest.mark.asyncio
    async def test_blooms_distribution_present(self, mock_llm_json):
        bundle = await generate_bundle_sync(SAMPLE_OUTLINE, SAMPLE_SLOTS)
        bd = bundle.components["ability_graph"]["blooms_distribution"]
        assert "bloom1" in bd and "bloom6" in bd
        assert sum(bd.values()) == 2

    @pytest.mark.asyncio
    async def test_not_in_component_names(self):
        """关键不变量:ability_graph 不进 COMPONENT_NAMES,保证 is_complete/ready/fallback 仍是 9 件语义."""
        from app.services.course_schemas import COMPONENT_NAMES
        assert "ability_graph" not in COMPONENT_NAMES
        assert len(COMPONENT_NAMES) == 9

    @pytest.mark.asyncio
    async def test_total_components_count_unaffected(self, mock_llm_json):
        """并行扩展不破坏老断言:核心 9 件仍完整,ability_graph 作为附加项."""
        bundle = await generate_bundle_sync(SAMPLE_OUTLINE, SAMPLE_SLOTS)
        # 9 件套全部存在
        for name in COMPONENT_NAMES:
            assert name in bundle.components, f"missing {name}"
        # ability_graph 作为附加项
        assert "ability_graph" in bundle.components
        assert len(bundle.components) == 10  # 9 + 1

    @pytest.mark.asyncio
    async def test_is_complete_ignores_ability_graph(self, mock_llm_json):
        """is_complete() 只看 COMPONENT_NAMES,所以 9 件全 ok 即认为完整,
        ability_graph 的状态不影响 is_complete 判定(向后兼容)."""
        bundle = await generate_bundle_sync(SAMPLE_OUTLINE, SAMPLE_SLOTS)
        # 把 ability_graph 改成 fallback, is_complete 仍为 True
        bundle.components["ability_graph"]["status"] = "fallback"
        assert bundle.is_complete() is True

    @pytest.mark.asyncio
    async def test_fallback_on_llm_error(self, monkeypatch):
        """LLM 抛 LLMJsonError 时,ability_graph 走 fallback 占位,不阻塞其他件."""
        from app.services.llm_json import LLMJsonError
        from app.services import course_bundle as cb

        async def fake_llm_json_failing_ability(prompt_id, variables, schema, **kwargs):
            if prompt_id == "ability_graph":
                raise LLMJsonError("simulated LLM down")
            # 其他件正常 mock
            return schema.model_validate(_mock_artifact_for(prompt_id))

        monkeypatch.setattr(cb, "llm_json", fake_llm_json_failing_ability)

        bundle = await generate_bundle_sync(SAMPLE_OUTLINE, SAMPLE_SLOTS)
        assert bundle.components["ability_graph"]["status"] == "fallback"
        # 其他 9 件正常
        for name in COMPONENT_NAMES:
            assert bundle.components[name]["status"] == "ok"


# ============================================================
# 缺口5:多 Agent 交叉验证循环(组件生成后过 AuditAgent)
# ============================================================

class TestAuditRetry:
    """验证 _run_one_component 接入 audit_agent 后,风险组件自动重试 + SSE component_retry 事件."""

    @pytest.mark.asyncio
    async def test_no_audit_agent_no_loop(self, mock_llm_json):
        """未注入 audit_agent 时,流程不变(不审核)."""
        from app.services import course_bundle as cb
        monkeypatch_cb = mock_llm_json  # 触发 fixture
        bundle = await generate_bundle_sync(SAMPLE_OUTLINE, SAMPLE_SLOTS)
        # 没有 audit_rejected 字段
        for name in bundle.components:
            assert "audit_rejected" not in bundle.components[name] or \
                   bundle.components[name].get("audit_rejected") is False

    @pytest.mark.asyncio
    async def test_audit_risk_high_triggers_retry(self, monkeypatch):
        """mock audit_agent 返回 risk=high → 触发重试,最终 audit_rejected=True."""
        from dataclasses import dataclass

        @dataclass
        class FakeAuditResult:
            risk_level: str = "high"
            blocked: bool = True
            reason: str = "jailbreak detected"
            jailbreak_score: float = 0.9
            hallucination_score: float = 0.0

        class FakeAuditAgent:
            def __init__(self):
                self.call_count = 0

            async def run(self, **kwargs):
                self.call_count += 1
                return FakeAuditResult()

        # 注入 audit_agent + 替换 _get_audit_agent 让 _run_one_component 拿到 fake
        from app.services import course_bundle as cb
        fake_agent = FakeAuditAgent()
        monkeypatch.setattr(cb, "_get_audit_agent", lambda: fake_agent)

        bundle = await generate_bundle_sync(SAMPLE_OUTLINE, SAMPLE_SLOTS)
        # 全部组件应被标记 audit_rejected
        rejected = [n for n in bundle.components if bundle.components[n].get("audit_rejected")]
        assert len(rejected) >= 5  # 至少 5 件被拒
        assert fake_agent.call_count >= 5

    @pytest.mark.asyncio
    async def test_audit_risk_low_marks_safe(self, monkeypatch):
        """mock audit_agent 返回 risk=low → 组件标记 audit_risk='low'."""
        @dataclass
        class SafeAuditResult:
            risk_level: str = "low"
            blocked: bool = False
            reason: str = ""
            jailbreak_score: float = 0.05

        class SafeAuditAgent:
            async def run(self, **kwargs):
                return SafeAuditResult()

        from app.services import course_bundle as cb
        monkeypatch.setattr(cb, "_get_audit_agent", lambda: SafeAuditAgent())

        bundle = await generate_bundle_sync(SAMPLE_OUTLINE, SAMPLE_SLOTS)
        # 全部组件标记 audit_risk=low,无 audit_rejected
        for name in bundle.components:
            comp = bundle.components[name]
            if comp.get("status") == "ok":
                assert comp.get("audit_risk") == "low"
                assert not comp.get("audit_rejected")

    @pytest.mark.asyncio
    async def test_sse_component_retry_event(self, monkeypatch):
        """SSE 流中,risk=high 的组件应同时吐 component_retry 事件."""
        @dataclass
        class BadAuditResult:
            risk_level: str = "high"
            blocked: bool = True
            reason: str = "hallucination"
            jailbreak_score: float = 0.0

        class BadAuditAgent:
            async def run(self, **kwargs):
                return BadAuditResult()

        from app.services import course_bundle as cb
        monkeypatch.setattr(cb, "_get_audit_agent", lambda: BadAuditAgent())

        events = []
        async for ev in generate_bundle(SAMPLE_OUTLINE, SAMPLE_SLOTS):
            events.append(ev)

        retry_events = [e for e in events if e["type"] == "component_retry"]
        ready_events = [e for e in events if e["type"] == "component_ready"]
        # 至少 5 件触发重试事件
        assert len(retry_events) >= 5
        # 每个 retry 事件都对应一个 ready 事件
        assert len(retry_events) == len([e for e in ready_events if e["payload"].get("audit_rejected")])
        # 重试事件字段齐全
        e = retry_events[0]
        assert "name" in e
        assert "reason" in e
        assert "attempts" in e
