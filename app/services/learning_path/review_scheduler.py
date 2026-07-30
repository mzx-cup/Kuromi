"""每日复习提醒调度器（M3.6）

被 APScheduler 接线（M4.6 SchedulerWirer.register_daily_review）调用。

数据流：
  1. 从 DB 拉取所有 next_review <= now 的 LearningState
  2. 按 user_id 分组，每用户最多 max_per_user_per_day 条
  3. 调用通知通道（push / email）发送复习提醒
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime

from app.services.learning_path.forgetting_curve import LearningState, SM2Scheduler

logger = logging.getLogger("starlearn.review_scheduler")


class ReviewScheduler:
    """每日复习提醒调度器。"""

    def __init__(self, max_per_user_per_day: int = 2) -> None:
        self.max_per_user_per_day = max_per_user_per_day
        self._sm2 = SM2Scheduler()

    async def run_daily_review(self, now: datetime | None = None) -> int:
        """运行一轮每日复习提醒，返回发送的通知数。

        Args:
            now: 当前时间（便于测试；默认 datetime.utcnow()）
        """
        now = now or datetime.utcnow()
        states = await self._fetch_due_states(now)

        # 按用户分组，每个用户最多 max_per_user_per_day
        per_user: dict[str, list[LearningState]] = defaultdict(list)
        for s in states:
            if len(per_user[s.user_id]) < self.max_per_user_per_day:
                per_user[s.user_id].append(s)

        sent = 0
        for user_id, user_states in per_user.items():
            for state in user_states:
                await self._send_review_notification(
                    user_id=user_id,
                    topic_id=state.topic_id,
                )
                sent += 1

        logger.info(
            f"Daily review sent {sent} notifications to {len(per_user)} users"
        )
        return sent

    async def _fetch_due_states(self, now: datetime) -> list[LearningState]:
        """从 DB 拉取 next_review <= now 的状态。

        占位实现：返回空列表。未来接 orm_learning_state_repository。
        """
        # TODO: 接入真实 ORM 仓库（learning_state_repository.list_due(now)）
        return []

    async def _send_review_notification(
        self,
        user_id: str,
        topic_id: str,
    ) -> None:
        """发送复习提醒（push / email）。

        占位实现：只写日志。未来接 notification_service。
        """
        logger.info(f"Review notification: user={user_id}, topic={topic_id}")