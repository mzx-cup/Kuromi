"""Tests for SM-2 forgetting curve scheduler (M3.5)."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest


def test_sm2_initial_state_has_short_interval():
    """初始 state 的 interval 应为 1 天（首次复习是明天）。"""
    from app.services.learning_path.forgetting_curve import LearningState, SM2Scheduler

    scheduler = SM2Scheduler()
    state = LearningState(user_id="u1", topic_id="t1", stability=2.5, difficulty=5, reps=0)
    next_review = scheduler.next_review(state, now=datetime(2026, 7, 29))
    assert next_review == datetime(2026, 7, 29) + timedelta(days=1)


def test_sm2_after_correct_response_increases_interval():
    """答对后 reps 应该增加，interval 应该增长。"""
    from app.services.learning_path.forgetting_curve import LearningState, SM2Scheduler

    scheduler = SM2Scheduler()
    state = LearningState(
        user_id="u1",
        topic_id="t1",
        stability=2.5,
        difficulty=5,
        reps=1,
        last_review=datetime(2026, 7, 29),
        interval=1.0,
    )
    next_state, next_review = scheduler.review(state, quality=5, now=datetime(2026, 7, 29))
    assert next_state.reps == 2
    assert next_review > datetime(2026, 7, 29) + timedelta(days=1)


def test_sm2_lapse_resets_interval():
    """答错（quality<3）必须重置 reps 到 0，lapses +1。"""
    from app.services.learning_path.forgetting_curve import LearningState, SM2Scheduler

    scheduler = SM2Scheduler()
    state = LearningState(
        user_id="u1",
        topic_id="t1",
        stability=2.5,
        difficulty=5,
        reps=5,
        last_review=datetime(2026, 7, 29),
        interval=3.0,
    )
    next_state, _ = scheduler.review(state, quality=1, now=datetime(2026, 7, 29))
    assert next_state.reps == 0
    assert next_state.lapses == 1


def test_sm2_stability_floor_at_1_3():
    """stability 必须 >= 1.3（SM-2 经典下限）。"""
    from app.services.learning_path.forgetting_curve import LearningState, SM2Scheduler

    scheduler = SM2Scheduler()
    state = LearningState(user_id="u1", topic_id="t1", stability=1.3, reps=10)
    next_state, _ = scheduler.review(state, quality=0, now=datetime(2026, 7, 29))
    assert next_state.stability >= 1.3


def test_sm2_second_correct_review_uses_three_day_interval():
    """SM-2: reps==2 时 interval 应固定为 3 天。"""
    from app.services.learning_path.forgetting_curve import LearningState, SM2Scheduler

    scheduler = SM2Scheduler()
    state = LearningState(user_id="u1", topic_id="t1", stability=2.5, reps=1, interval=1.0)
    next_state, next_review = scheduler.review(state, quality=5, now=datetime(2026, 7, 29))
    # After 2nd correct answer, interval should be 3 days
    assert next_state.reps == 2
    assert next_state.interval == 3.0
    assert next_review == datetime(2026, 7, 29) + timedelta(days=3)