"""APScheduler 接线（M4.6 / #17）

注册两个 cron 任务：
  - daily_review: 每天 00:00 触发 ReviewScheduler.run_daily_review()
  - parent_report: 每月 1 号 08:00 触发家长月报生成（M5 占位）

设计要点：
  - 与现有 app/services/drift/scheduler.py 共存（不替换）
  - 支持 dependency injection（便于测试）
  - replace_existing=True（防止重复注册累积）
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.services.learning_path.review_scheduler import ReviewScheduler

logger = logging.getLogger("starlearn.scheduler")


class SchedulerWirer:
    """APScheduler 任务注册器。"""

    DAILY_REVIEW_JOB_ID = "daily_review"
    PARENT_REPORT_JOB_ID = "parent_report"

    def __init__(self, scheduler: AsyncIOScheduler | None = None) -> None:
        self._scheduler = scheduler or AsyncIOScheduler()
        self._review = ReviewScheduler()

    def register_daily_review(self, hour: int = 0, minute: int = 0) -> None:
        """注册每日复习任务。"""
        self._scheduler.add_job(
            self._review.run_daily_review,
            "cron",
            hour=hour,
            minute=minute,
            id=self.DAILY_REVIEW_JOB_ID,
            replace_existing=True,
        )
        logger.info(f"daily_review job registered at {hour:02d}:{minute:02d}")

    def register_parent_report(self, day: int = 1, hour: int = 8) -> None:
        """注册家长月报生成任务（M5 占位）。

        实际生成逻辑由 M5 Task 25 实现，本阶段只占位。
        """

        async def _placeholder_generate():
            logger.info("[parent_report] placeholder: M5 Task 25 will implement")

        self._scheduler.add_job(
            _placeholder_generate,
            "cron",
            day=day,
            hour=hour,
            id=self.PARENT_REPORT_JOB_ID,
            replace_existing=True,
        )
        logger.info(f"parent_report job registered at day={day} {hour:02d}:00")

    def start(self) -> None:
        """启动调度器。"""
        self._scheduler.start()
        logger.info("SchedulerWirer started")

    def shutdown(self) -> None:
        """关闭调度器。"""
        try:
            self._scheduler.shutdown()
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Scheduler shutdown error: {exc}")