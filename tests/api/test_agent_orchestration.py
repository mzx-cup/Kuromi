# -*- coding: utf-8 -*-
"""Tests for app/api/agent_orchestration.py - profile_updated payload builder.

M1.1 / Task #7: 修复 agent_orchestration.py:103 传空 LearningPortrait() 的 bug.
原代码 aggregate_portrait_snapshot(LearningPortrait()) 传空对象, 导致 radar 数据全 0,
渲染出空白雷达图. 修复后应传入真实 LearningPortrait, radar/panel 反映学生实际状态.

注意:
- LearningPortrait 的实际 schema 是嵌套模型 (KnowledgeMasteryPortrait /
  CodeSkillPortrait / ...), 不是 plan 中假设的扁平字段. 测试 + 辅助函数
  都按实际 schema 对齐.
- 6 维分数由 aggregate_portrait_snapshot() 计算, 验证时使用确定值.
"""

from __future__ import annotations

from state import (
    LearningPortrait,
    KnowledgeMasteryPortrait,
    TopicMastery,
    CodeSkillPortrait,
    CognitiveStylePortrait,
    LearningGoalPortrait,
    WeaknessPortrait,
    FocusLevelPortrait,
)

from app.api.agent_orchestration import _build_profile_updated_payload


def _real_portrait() -> LearningPortrait:
    """构造一个真实（非空）的 LearningPortrait, 6 维均含确定值."""
    return LearningPortrait(
        knowledge_mastery=KnowledgeMasteryPortrait(
            topics=[TopicMastery(name="Python 基础", level=0.7)],
            overall=0.7,  # → radar.knowledge_mastery = 70.0
        ),
        code_skill=CodeSkillPortrait(level="intermediate"),  # → 60.0
        cognitive_style=CognitiveStylePortrait(
            type="视觉型", confidence=0.5,  # → 50.0
        ),
        learning_goal=LearningGoalPortrait(current="学会 Python"),  # → +30 = 30.0
        weakness=WeaknessPortrait(areas=["递归", "动态规划"]),  # → 2 × 25 = 50.0
        focus_level=FocusLevelPortrait(current="中等专注"),  # → 60.0
    )


def test_profile_updated_uses_real_portrait_not_empty():
    """_build_profile_updated_payload 必须使用传入的真实 portrait,
    不能像 line 103 原代码那样隐式传 LearningPortrait() 导致 radar 全 0."""
    real_portrait = _real_portrait()
    payload = _build_profile_updated_payload(user_id="u1", portrait=real_portrait)

    # radar 各维度分数必须是真实值, 反映传入 portrait 的数据
    assert payload["radar"]["knowledge_mastery"] == 70.0  # 0.7 × 100
    assert payload["radar"]["code_skill"] == 60.0         # intermediate → 60.0
    assert payload["radar"]["cognitive_style"] == 50.0     # 0.5 × 100
    assert payload["radar"]["learning_goal"] == 30.0       # 有 current → +30
    assert payload["radar"]["weakness"] == 50.0           # 2 areas × 25
    assert payload["radar"]["focus_level"] == 60.0        # 中等专注 → 60.0

    # user_id 必须正确传递
    assert payload["user_id"] == "u1"


def test_profile_updated_payload_has_required_fields():
    """payload 必须包含 user_id / radar / panel / timestamp 四个字段."""
    payload = _build_profile_updated_payload(user_id="u2", portrait=_real_portrait())
    assert "user_id" in payload
    assert "radar" in payload
    assert "panel" in payload
    assert "timestamp" in payload


def test_profile_updated_empty_portrait_yields_valid_payload():
    """对照组: 空 LearningPortrait() 仍能产生有效 payload（fallback 行为）.

    注意: LearningPortrait() 的默认值并非全 0 — code_skill.level="beginner" 映射为 25.0,
    focus_level.current="中等专注" 映射为 60.0. 这里只验证 fallback 不会崩溃, 且
    payload 结构完整（radar 6 维 + panel 4 卡 + user_id + timestamp 都在）.
    """
    payload = _build_profile_updated_payload(user_id="u3", portrait=LearningPortrait())
    assert set(payload["radar"].keys()) == {
        "knowledge_mastery", "code_skill", "cognitive_style",
        "learning_goal", "weakness", "focus_level",
    }
    assert set(payload["panel"].keys()) == {
        "learning_style", "cognitive_level", "current_goal", "emotion_state",
    }
    # 所有 radar 分数必须在 [0, 100] 范围内（aggregator 已 clamp）
    for v in payload["radar"].values():
        assert 0.0 <= v <= 100.0


def test_profile_updated_payload_is_json_serializable():
    """payload 必须可 JSON 序列化（前端 agent-sse-client 通过 JSON 解析）."""
    import json
    payload = _build_profile_updated_payload(user_id="u4", portrait=_real_portrait())
    # 不抛异常即通过
    json.dumps(payload, ensure_ascii=False, default=str)