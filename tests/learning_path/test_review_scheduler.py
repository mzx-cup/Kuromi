"""Tests for ReviewScheduler (M3.6)."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_scheduler_picks_due_topics():
    """scheduler 必须拉取所有 due 状态并发送通知。"""
    from app.services.learning_path.forgetting_curve import LearningState
    from app.services.learning_path.review_scheduler import ReviewScheduler

    scheduler = ReviewScheduler()
    with patch.object(scheduler, "_fetch_due_states", new_callable=AsyncMock) as mock:
        mock.return_value = [
            LearningState(user_id="u1", topic_id="t1", reps=2, interval=3.0),
            LearningState(user_id="u2", topic_id="t2", reps=1, interval=1.0),
        ]
        with patch.object(
            scheduler, "_send_review_notification", new_callable=AsyncMock
        ) as notify_mock:
            count = await scheduler.run_daily_review(now=datetime(2026, 7, 29))
            assert count == 2
            assert notify_mock.call_count == 2


@pytest.mark.asyncio
async def test_scheduler_respects_max_daily_reviews():
    """每个用户每天最多 max_per_user_per_day 条。"""
    from app.services.learning_path.forgetting_curve import LearningState
    from app.services.learning_path.review_scheduler import ReviewScheduler

    scheduler = ReviewScheduler(max_per_user_per_day=2)
    with patch.object(scheduler, "_fetch_due_states", new_callable=AsyncMock) as mock:
        # 同用户 3 个待复习
        mock.return_value = [
            LearningState(user_id="u1", topic_id="t1"),
            LearningState(user_id="u1", topic_id="t2"),
            LearningState(user_id="u1", topic_id="t3"),
        ]
        with patch.object(
            scheduler, "_send_review_notification", new_callable=AsyncMock
        ) as notify_mock:
            count = await scheduler.run_daily_review()
            assert count == 2  # max 限额


@pytest.mark.asyncio
async def test_scheduler_returns_zero_when_no_due():
    """没有 due topic 时返回 0。"""
    from app.services.learning_path.review_scheduler import ReviewScheduler

    scheduler = ReviewScheduler()
    with patch.object(scheduler, "_fetch_due_states", new_callable=AsyncMock) as mock:
        mock.return_value = []
        count = await scheduler.run_daily_review()
        assert count == 0