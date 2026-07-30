"""Tests for real-time micro portrait updates (M3.7)."""
from __future__ import annotations

import pytest


def test_update_micro_portrait_increments_event_count():
    """每答一题应该让 event_count +1。"""
    from app.services.portrait_aggregator import update_micro_portrait

    delta = update_micro_portrait(
        user_id="u1",
        event_type="quiz_answer",
        event_data={"correct": True, "time_spent": 30},
    )
    assert delta["knowledge_mastery"] > 0
    assert delta["event_count_delta"] == 1
    assert delta["last_event_at"]


def test_update_micro_portrait_penalty_for_long_time():
    """超长答题时间应该惩罚 focus_level。"""
    from app.services.portrait_aggregator import update_micro_portrait

    delta = update_micro_portrait(
        user_id="u1",
        event_type="quiz_answer",
        event_data={"correct": False, "time_spent": 300},  # 5 分钟
    )
    assert delta["knowledge_mastery"] < 0
    assert delta["focus_level"] < 0  # 长时间应当扣 focus


def test_update_micro_portrait_penalty_for_too_fast():
    """过快答题（瞎猜）应该惩罚 focus_level。"""
    from app.services.portrait_aggregator import update_micro_portrait

    delta = update_micro_portrait(
        user_id="u1",
        event_type="quiz_answer",
        event_data={"correct": True, "time_spent": 2},  # 2 秒
    )
    assert delta["focus_level"] < 0


def test_update_micro_portrait_unknown_event_returns_neutral_delta():
    """未知事件类型必须返回中性 delta（不崩）。"""
    from app.services.portrait_aggregator import update_micro_portrait

    delta = update_micro_portrait(
        user_id="u1",
        event_type="unknown_event",
        event_data={},
    )
    assert delta["event_count_delta"] == 1
    assert delta["knowledge_mastery"] == 0.0
    assert delta["focus_level"] == 0.0