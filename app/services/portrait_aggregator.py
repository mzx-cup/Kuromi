# -*- coding: utf-8 -*-
"""
Portrait Aggregator — 6 维雷达 + 4 卡画像统一快照

输入: LearningPortrait (state.py 中的 6 维学生画像)
输出: {
    "radar": { 6 维得分 0-100 },
    "panel": { 4 张画像卡片 },
    "last_synced": ISO 时间戳,
}

设计说明 (相对于 plan 的适配):
1. plan 中写 state.profile 实际上是 LearningProfile (legacy, StudentState.profile),
   真正的 6 维 LearningPortrait 是独立模型, 不在 StudentState 上.
   改为直接接受 LearningPortrait 参数.
2. plan 中 _calc_goal 读 state.profile.learning_goals (legacy LearningProfile 的字段),
   实际 6 维模型中学习目标在 LearningGoalPortrait.current (单字符串).
3. plan 中 _calc_focus 读 focus_level.score (实际模型无此字段),
   改为将 current 字符串 (高专注/中等专注/需要引导) 映射为数值.
4. CodeSkillPortrait.level 在 state.py 中只列举了 3 档 (beginner/intermediate/advanced),
   兼容 4 档 (含 basic) 以保持向后兼容.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from state import LearningPortrait


# 编程能力等级 → 0-100 分数
_CODE_LEVEL_SCORE = {
    "beginner": 25.0,
    "basic": 40.0,
    "intermediate": 60.0,
    "advanced": 85.0,
}

# 专注度标签 → 基础分 (高=90, 中=60, 引导=30)
_FOCUS_LABEL_SCORE = {
    "高专注": 90.0,
    "中等专注": 60.0,
    "需要引导": 30.0,
}


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    """限制数值范围到 [lo, hi]."""
    return max(lo, min(hi, value))


def _calc_knowledge(portrait: LearningPortrait) -> float:
    """知识掌握: topics 平均 level × 100, 优先使用 overall 字段 (若已计算)."""
    overall = portrait.knowledge_mastery.overall
    if overall > 0.0:
        return _clamp(round(overall * 100, 1))
    items = portrait.knowledge_mastery.topics
    if not items:
        return 0.0
    avg = sum(t.level for t in items) / len(items)
    return _clamp(round(avg * 100, 1))


def _calc_code(portrait: LearningPortrait) -> float:
    """编程能力: 等级字符串映射."""
    return _CODE_LEVEL_SCORE.get(portrait.code_skill.level, 50.0)


def _calc_style(portrait: LearningPortrait) -> float:
    """认知风格: 置信度 × 100."""
    return _clamp(round(portrait.cognitive_style.confidence * 100, 1))


def _calc_goal(portrait: LearningPortrait) -> float:
    """学习目标: 有 current 目标 +30, 每多一个 target_position +15, 上限 100."""
    score = 0.0
    if portrait.learning_goal.current:
        score += 30.0
    score += min(len(portrait.learning_goal.target_positions), 5) * 15.0
    return _clamp(score)


def _calc_weakness(portrait: LearningPortrait) -> float:
    """知识短板: 每识别一个薄弱点 +25, 上限 100 (短板越多越需要关注)."""
    return _clamp(float(min(len(portrait.weakness.areas), 4) * 25))


def _calc_focus(portrait: LearningPortrait, telemetry: Optional[dict]) -> float:
    """专注度: 基础分来自 current 标签, telemetry 中 mouse_idle > 5s 则扣 20."""
    base = _FOCUS_LABEL_SCORE.get(portrait.focus_level.current, 60.0)
    if telemetry:
        idle = telemetry.get("mouse_idle_ms", 0) or 0
        if idle > 5000:
            base = max(0.0, base - 20.0)
    return _clamp(round(base, 1))


def _derive_emotion(telemetry: Optional[dict]) -> str:
    """从 telemetry 推导情绪标签 (无 telemetry → calm)."""
    if not telemetry:
        return "calm"
    idle = telemetry.get("mouse_idle_ms", 0) or 0
    if idle > 8000:
        return "frustrated"
    if (telemetry.get("scroll_speed", 0) or 0) > 800:
        return "anxious"
    if (telemetry.get("zone_dwell_ms", 0) or 0) > 30000:
        return "engaged"
    return "calm"


def aggregate_portrait_snapshot(
    portrait: LearningPortrait,
    telemetry: Optional[dict] = None,
) -> dict[str, Any]:
    """生成 6 维雷达 + 4 卡画像的统一快照.

    Args:
        portrait: 6 维学生画像 (LearningPortrait).
        telemetry: 前端遥测 (mouse_idle_ms / scroll_speed / zone_dwell_ms).

    Returns:
        {
            "radar": { 6 维 0-100 分 },
            "panel": { 4 张画像卡片 },
            "last_synced": ISO 8601 with timezone,
        }
    """
    return {
        "radar": {
            "knowledge_mastery": _calc_knowledge(portrait),
            "code_skill": _calc_code(portrait),
            "cognitive_style": _calc_style(portrait),
            "learning_goal": _calc_goal(portrait),
            "weakness": _calc_weakness(portrait),
            "focus_level": _calc_focus(portrait, telemetry),
        },
        "panel": {
            "learning_style": {
                "label": portrait.cognitive_style.type,
                "confidence": portrait.cognitive_style.confidence,
            },
            "cognitive_level": {
                "label": portrait.code_skill.level,
                "score": _calc_code(portrait),
            },
            "current_goal": {
                "label": portrait.learning_goal.current or "—",
                "progress_pct": _calc_goal(portrait),
            },
            "emotion_state": {
                "label": _derive_emotion(telemetry),
                "intensity": 3,
            },
        },
        "last_synced": datetime.now(timezone.utc).isoformat(),
    }
