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

# 学习目标评分参数
_GOAL_CURRENT_BONUS = 30.0          # 有 current 目标 +30
_GOAL_BONUS_PER_TARGET = 15.0       # 每多一个 target_position +15
_GOAL_MAX_TARGETS = 5               # 最多考虑 5 个 target_position

# 知识短板评分参数
_WEAKNESS_BONUS_PER_AREA = 25.0     # 每个薄弱点 +25
_WEAKNESS_MAX_AREAS = 4             # 最多 4 个短板, 上限 100

# 专注度遥测参数
_FOCUS_PENALTY_IDLE_MS = 5000       # 鼠标空闲 > 5s 触发扣分
_FOCUS_PENALTY_AMOUNT = 20.0        # 扣分幅度
_FOCUS_DEFAULT_SCORE = 60.0         # 未知标签的兜底分

# 情绪推导阈值
_FRUSTRATED_IDLE_MS = 8000          # 空闲 > 8s → frustrated
_ANXIOUS_SCROLL_THRESHOLD = 800     # 滚动速度 > 800 → anxious
_ENGAGED_DWELL_MS = 30000           # 区域停留 > 30s → engaged

# 情绪标签 → 强度 (1-5)
_EMOTION_INTENSITY = {
    "frustrated": 4,
    "anxious": 3,
    "engaged": 2,
    "calm": 1,
}
_DEFAULT_EMOTION_INTENSITY = 3


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
        score += _GOAL_CURRENT_BONUS
    score += min(len(portrait.learning_goal.target_positions), _GOAL_MAX_TARGETS) * _GOAL_BONUS_PER_TARGET
    return _clamp(score)


def _calc_weakness(portrait: LearningPortrait) -> float:
    """知识短板: 每识别一个薄弱点 +25, 上限 100 (短板越多越需要关注)."""
    return _clamp(
        float(min(len(portrait.weakness.areas), _WEAKNESS_MAX_AREAS) * _WEAKNESS_BONUS_PER_AREA)
    )


def _calc_focus(portrait: LearningPortrait, telemetry: Optional[dict]) -> float:
    """专注度: 基础分来自 current 标签, telemetry 中 mouse_idle > 5s 则扣 20."""
    base = _FOCUS_LABEL_SCORE.get(portrait.focus_level.current, _FOCUS_DEFAULT_SCORE)
    if telemetry:
        idle = telemetry.get("mouse_idle_ms", 0) or 0
        if idle > _FOCUS_PENALTY_IDLE_MS:
            base = max(0.0, base - _FOCUS_PENALTY_AMOUNT)
    return _clamp(round(base, 1))


def _derive_emotion(telemetry: Optional[dict]) -> str:
    """从 telemetry 推导情绪标签 (无 telemetry → calm)."""
    if not telemetry:
        return "calm"
    idle = telemetry.get("mouse_idle_ms", 0) or 0
    if idle > _FRUSTRATED_IDLE_MS:
        return "frustrated"
    if (telemetry.get("scroll_speed", 0) or 0) > _ANXIOUS_SCROLL_THRESHOLD:
        return "anxious"
    if (telemetry.get("zone_dwell_ms", 0) or 0) > _ENGAGED_DWELL_MS:
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
                "intensity": _EMOTION_INTENSITY.get(
                    _derive_emotion(telemetry), _DEFAULT_EMOTION_INTENSITY
                ),
            },
        },
        "last_synced": datetime.now(timezone.utc).isoformat(),
    }


# ── M3.7: 实时微画像事件流 ─────────────────────────────────

# 答题时间阈值（秒）
LONG_ANSWER_THRESHOLD_SECONDS = 120  # 超过 2 分钟
FAST_ANSWER_THRESHOLD_SECONDS = 10  # 小于 10 秒（可能瞎猜）


def update_micro_portrait(
    user_id: str,
    event_type: str,
    event_data: dict,
) -> dict:
    """根据实时事件微调画像权重（M3.7）。

    支持的事件类型：
      - quiz_answer: 答题事件，event_data 包含 correct / time_spent
      - video_watch / chat_message / page_view: 占位（中性 delta）

    返回 delta dict，包含：
      - knowledge_mastery: 知识掌握度变化（-1.0 ~ +1.0）
      - focus_level: 专注度变化（-1.0 ~ +1.0）
      - event_count_delta: 事件计数增量（固定为 1）
      - last_event_at: 事件时间戳
    """
    delta = {
        "knowledge_mastery": 0.0,
        "focus_level": 0.0,
        "event_count_delta": 1,
        "last_event_at": datetime.now(timezone.utc).isoformat(),
    }

    if event_type == "quiz_answer":
        is_correct = bool(event_data.get("correct"))
        time_spent = int(event_data.get("time_spent", 0))

        if is_correct:
            delta["knowledge_mastery"] = +0.05
        else:
            delta["knowledge_mastery"] = -0.03

        # focus_level 调整
        if time_spent > LONG_ANSWER_THRESHOLD_SECONDS:
            # 超长答题：分心 / 卡壳
            delta["focus_level"] = -0.05
        elif 0 < time_spent < FAST_ANSWER_THRESHOLD_SECONDS:
            # 过快答题：可能是瞎猜
            delta["focus_level"] = -0.03
        # 其他情况：focus 不变

    elif event_type in ("video_watch", "chat_message", "page_view"):
        # 中性事件：不调整 mastery / focus，仅记录
        pass

    return delta
