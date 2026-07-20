# -*- coding: utf-8 -*-
"""Phase 2 脑暴服务单测 — 3 轮状态机 + OBG/PBL 判定 + 大纲生成.

原则:
- 离线可跑 (不连真实 LLM, mock llm_json)
- 用 monkeypatch 替换 app.services.course_brainstorm.llm_json
- 跑完清空 BRAINSTORM_STORE, 不污染其他测试
"""
from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

_tmpdir = tempfile.mkdtemp(prefix="xs-audit-")
os.environ.setdefault("XINSHI_AUDIT_LOG", str(Path(_tmpdir) / "audit.log"))

import pytest  # noqa: E402

from app.services import course_brainstorm  # noqa: E402
from app.services.course_brainstorm import (  # noqa: E402
    BRAINSTORM_STORE,
    SLOT_ORDER,
    TOTAL_TURNS,
    BrainstormState,
    confirm_brainstorm,
    start_brainstorm,
    turn_brainstorm,
)


# ============================================================
# 通用 mock fixture: 替换 llm_json + capability repository
# ============================================================

MOCK_QUESTIONS = {
    "goal": {
        "question": "你的学习目标是什么?",
        "options": ["求职", "项目实战", "系统学习", "应付考试"],
    },
    "base": {
        "question": "你目前的基础如何?",
        "options": ["零基础", "写过脚本", "做过项目", "资深开发者"],
    },
    "path": {
        "question": "你希望的学习路径是?",
        "options": ["系统学", "速成", "案例驱动", "理论先行"],
    },
}

MOCK_DECISION = {
    "mode": "obg",
    "rationale": "用户选择目标为求职 + 基础写过脚本, 适合 OBG 目标驱动模式",
    "outline": {
        "title": "Python 数据分析入门",
        "description": "3 场景 OBG 课程",
        "scenes": [
            {"id": "s1", "title": "基础语法", "description": "变量/循环/函数", "key_points": ["语法"], "type": "slide", "duration_min": 10},
            {"id": "s2", "title": "pandas 入门", "description": "DataFrame/读文件/聚合", "key_points": ["pandas"], "type": "slide", "duration_min": 15},
            {"id": "s3", "title": "实战项目", "description": "销售数据分析报告", "key_points": ["实战"], "type": "slide", "duration_min": 20},
        ],
    },
}


@pytest.fixture(autouse=True)
def mock_llm(monkeypatch):
    """替换 llm_json: 出题 mock + decide mock."""
    async def fake_llm_json(prompt_id, variables, schema, **kwargs):
        if prompt_id == "brainstorm_question":
            slot = variables.get("slot") or variables.get("next_slot") or "goal"
            return schema.model_validate(MOCK_QUESTIONS.get(slot, MOCK_QUESTIONS["goal"]))
        if prompt_id == "brainstorm_decide_obg_pbl":
            return schema.model_validate(MOCK_DECISION)
        raise RuntimeError(f"unexpected prompt_id in test: {prompt_id}")
    monkeypatch.setattr(course_brainstorm, "llm_json", fake_llm_json)

    class FakeCapabilityRepository:
        async def aggregate_profile(self, user_id):
            return {
                "knowledge_base": {"Python": 0.6},
                "code_skill": {"Python": 0.6},
                "cognitive_style": {"preferred_modality": "visual"},
                "focus_level": {"avg_session_minutes": 30, "streak_days": 2},
                "learning_goals": [{"id": 1, "title": "求职"}],
                "weakness": [],
            }

    monkeypatch.setattr(
        course_brainstorm,
        "get_repository_for_user",
        lambda user_id, repository_type: FakeCapabilityRepository(),
    )

    BRAINSTORM_STORE.clear()
    yield
    BRAINSTORM_STORE.clear()


# ============================================================
# 槽位顺序 / 状态机常量
# ============================================================

class TestConstants:
    def test_slot_order(self):
        assert SLOT_ORDER == ("goal", "base", "path")

    def test_total_turns(self):
        assert TOTAL_TURNS == 3


# ============================================================
# start_brainstorm
# ============================================================

class TestStartBrainstorm:
    @pytest.mark.asyncio
    async def test_first_turn_is_goal(self):
        out = await start_brainstorm("我想学 Python 数据分析", student_id="1")
        assert out["turn"] == 1
        assert out["total_turns"] == 3
        assert out["slot"] == "goal"
        assert isinstance(out["options"], list)
        assert len(out["options"]) >= 2
        assert out["allow_skip"] is True

    @pytest.mark.asyncio
    async def test_unique_id_per_call(self):
        a = await start_brainstorm("req A", "1")
        b = await start_brainstorm("req B", "1")
        assert a["brainstorm_id"] != b["brainstorm_id"]
        assert a["brainstorm_id"].startswith("bs_")

    @pytest.mark.asyncio
    async def test_stores_state(self):
        out = await start_brainstorm("test", "1")
        state = BRAINSTORM_STORE[out["brainstorm_id"]]
        assert isinstance(state, BrainstormState)
        assert state.requirement == "test"
        assert state.turn == 0  # 已记录答案数=0 (turn=1 是下一题编号)


# ============================================================
# turn_brainstorm: 3 轮全 happy path
# ============================================================

class TestTurnHappyPath:
    @pytest.mark.asyncio
    async def test_three_rounds_then_done(self):
        s = await start_brainstorm("Python", "1")
        # turn 1 → turn 2
        r1 = await turn_brainstorm(s["brainstorm_id"], user_choice="求职")
        assert r1["done"] is False
        assert r1["slot"] == "base"
        assert r1["turn"] == 2
        # turn 2 → turn 3
        r2 = await turn_brainstorm(s["brainstorm_id"], user_choice="写过脚本")
        assert r2["done"] is False
        assert r2["slot"] == "path"
        assert r2["turn"] == 3
        # turn 3 → done
        r3 = await turn_brainstorm(s["brainstorm_id"], user_choice="系统学")
        assert r3["done"] is True
        assert r3["turn"] == 3
        assert r3["obg_pbl_mode"] in ("obg", "pbl")
        assert "scenes" in r3["outline"]
        assert len(r3["outline"]["scenes"]) == 3

    @pytest.mark.asyncio
    async def test_slots_recorded(self):
        s = await start_brainstorm("Python", "1")
        await turn_brainstorm(s["brainstorm_id"], user_choice="求职")
        await turn_brainstorm(s["brainstorm_id"], user_text="写过一个爬虫")
        await turn_brainstorm(s["brainstorm_id"], user_choice="案例驱动")
        state = BRAINSTORM_STORE[s["brainstorm_id"]]
        assert state.slots["goal"] == "求职"
        assert state.slots["base"] == "写过一个爬虫"
        assert state.slots["path"] == "案例驱动"
        assert state.turn == 3


# ============================================================
# 跳过 / 自定义 / 边界
# ============================================================

class TestSkipAndEdge:
    @pytest.mark.asyncio
    async def test_skip_keeps_slot_null(self):
        s = await start_brainstorm("Python", "1")
        await turn_brainstorm(s["brainstorm_id"], skip=True)
        state = BRAINSTORM_STORE[s["brainstorm_id"]]
        assert state.slots["goal"] is None

    @pytest.mark.asyncio
    async def test_skip_all_still_done(self):
        s = await start_brainstorm("Python", "1")
        await turn_brainstorm(s["brainstorm_id"], skip=True)
        await turn_brainstorm(s["brainstorm_id"], skip=True)
        r3 = await turn_brainstorm(s["brainstorm_id"], skip=True)
        assert r3["done"] is True
        # 即便全 skip, 也得有 outline (LLM decide 走 mock)
        assert "scenes" in r3["outline"]

    @pytest.mark.asyncio
    async def test_extra_turn_raises(self):
        s = await start_brainstorm("Python", "1")
        await turn_brainstorm(s["brainstorm_id"], user_choice="A")
        await turn_brainstorm(s["brainstorm_id"], user_choice="B")
        await turn_brainstorm(s["brainstorm_id"], user_choice="C")
        with pytest.raises(ValueError, match="已收齐"):
            await turn_brainstorm(s["brainstorm_id"], user_choice="D")

    @pytest.mark.asyncio
    async def test_unknown_id_raises(self):
        with pytest.raises(KeyError):
            await turn_brainstorm("bs_does_not_exist", user_choice="A")


# ============================================================
# confirm_brainstorm
# ============================================================

class TestConfirm:
    @pytest.mark.asyncio
    async def test_confirm_requires_done(self):
        s = await start_brainstorm("Python", "1")
        with pytest.raises(ValueError, match="尚未完成"):
            await confirm_brainstorm(s["brainstorm_id"])

    @pytest.mark.asyncio
    async def test_confirm_locks_and_returns_summary(self):
        s = await start_brainstorm("Python", "1")
        await turn_brainstorm(s["brainstorm_id"], user_choice="求职")
        await turn_brainstorm(s["brainstorm_id"], user_choice="零基础")
        await turn_brainstorm(s["brainstorm_id"], user_choice="系统学")
        out = await confirm_brainstorm(s["brainstorm_id"])
        assert out["locked"] is True
        assert out["obg_pbl_mode"] in ("obg", "pbl")
        assert out["outline_summary"]["total_scenes"] == 3
        assert out["outline_summary"]["estimated_min"] == 45  # 10+15+20
        assert BRAINSTORM_STORE[s["brainstorm_id"]].confirmed is True

    @pytest.mark.asyncio
    async def test_confirm_obg_pbl_override(self):
        s = await start_brainstorm("Python", "1")
        await turn_brainstorm(s["brainstorm_id"], user_choice="A")
        await turn_brainstorm(s["brainstorm_id"], user_choice="B")
        await turn_brainstorm(s["brainstorm_id"], user_choice="C")
        out = await confirm_brainstorm(s["brainstorm_id"], obg_pbl_override="pbl")
        assert out["obg_pbl_mode"] == "pbl"
        # 非法 override 回退原值
        out2 = await confirm_brainstorm(
            s["brainstorm_id"], obg_pbl_override="invalid_mode"
        )
        # 二次 confirm 不抛, 但 mode 保留首次锁定
        assert out2["obg_pbl_mode"] in ("obg", "pbl")

    @pytest.mark.asyncio
    async def test_confirm_outline_edit_merges_scenes(self):
        s = await start_brainstorm("Python", "1")
        await turn_brainstorm(s["brainstorm_id"], user_choice="A")
        await turn_brainstorm(s["brainstorm_id"], user_choice="B")
        await turn_brainstorm(s["brainstorm_id"], user_choice="C")
        # 增加 1 个场景
        new_scenes = [
            {"id": "s1", "title": "新", "description": "x", "key_points": [], "type": "slide", "duration_min": 5},
            {"id": "s2", "title": "新2", "description": "x", "key_points": [], "type": "slide", "duration_min": 5},
        ]
        out = await confirm_brainstorm(
            s["brainstorm_id"],
            outline_edit={"scenes": new_scenes},
        )
        assert len(out["outline"]["scenes"]) == 2
        assert out["outline"]["scenes"][0]["title"] == "新"


# ============================================================
# 异常兜底: LLM decide 失败时, 应走 fallback 而不是抛
# ============================================================

class TestFallback:
    @pytest.mark.asyncio
    async def test_decide_llm_failure_falls_back(self, monkeypatch):
        async def boom(prompt_id, variables, schema, **kwargs):
            if prompt_id == "brainstorm_decide_obg_pbl":
                raise RuntimeError("mock LLM down")
            return schema.model_validate(MOCK_QUESTIONS.get(variables.get("slot", "goal"), MOCK_QUESTIONS["goal"]))
        monkeypatch.setattr(course_brainstorm, "llm_json", boom)
        s = await start_brainstorm("Python", "1")
        await turn_brainstorm(s["brainstorm_id"], user_choice="A")
        await turn_brainstorm(s["brainstorm_id"], user_choice="B")
        r3 = await turn_brainstorm(s["brainstorm_id"], user_choice="C")
        # 不抛, 走 fallback
        assert r3["done"] is True
        assert r3["obg_pbl_mode"] in ("obg", "pbl")
        assert len(r3["outline"]["scenes"]) >= 3
