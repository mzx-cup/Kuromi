# -*- coding: utf-8 -*-
"""
ActionLedger — 动作账本

防止 LinkRecommender 和 ProactiveAdvisor 的内容重复/冲突。
记录"最近向学生暴露过什么知识点/动作"，用于去重和冷却。

设计原则：
  - 轻量：默认用内存 dict，生产环境可替换为 Redis
  - 按学生 ID 隔离
  - 不同动作类型有不同的冷却 TTL
"""

from __future__ import annotations

import time
import threading
from datetime import timedelta
from typing import Optional


class ActionLedger:
    """
    动作账本 —— 记录学生最近接触过的知识点和动作。

    使用示例:
        ledger = ActionLedger()
        if not ledger.recently_exposed(student_id, "递归", minutes=10):
            # 发送推送或展示链接
            ledger.record_exposure(student_id, "递归", "proactive_push")
    """

    # 默认冷却时间配置（秒）
    DEFAULT_TTL_MAP: dict[str, int] = {
        "link_click": 2 * 3600,           # 点了链接，2 小时内不再重复推
        "proactive_push": 1 * 3600,       # 推送过的，1 小时内不再重复推
        "practice_complete": 24 * 3600,   # 做完练习的，1 天内不再推同样练习
        "deadline_warning": 24 * 3600,    # 截止提醒，每天最多一次
        "health_break": 2 * 3600,         # 休息提醒，2 小时一次
        "error_pattern": 4 * 3600,        # 错误模式提醒，4 小时一次
        "review_reminder": 30 * 60,       # 复习提醒，30 分钟冷却
        "struggle_intervention": 10 * 60, # 困难干预，10 分钟冷却
        "code_not_written": 20 * 60,      # 只看不练提醒，20 分钟冷却
        "tab_switching": 15 * 60,         # 标签切换提醒，15 分钟冷却
    }

    def __init__(self, ttl_map: Optional[dict[str, int]] = None):
        """
        Args:
            ttl_map: 自定义冷却时间配置（秒），覆盖默认值
        """
        self._ttl_map = {**self.DEFAULT_TTL_MAP, **(ttl_map or {})}
        # 内存存储: {student_id: {topic: timestamp}}
        self._store: dict[str, dict[str, float]] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # 核心 API
    # ------------------------------------------------------------------

    def recently_exposed(
        self,
        student_id: str,
        topic: str,
        minutes: int = 10,
    ) -> bool:
        """
        检查某 topic 是否在指定时间内已向学生暴露过。

        Args:
            student_id: 学生 ID
            topic: 知识点/动作标识，如 "递归", "deadline:task_123", "health_break"
            minutes: 冷却时间（分钟），优先级高于 TTL map

        Returns:
            True 如果仍在冷却期内
        """
        if not student_id or not topic:
            return False

        with self._lock:
            student_store = self._store.get(student_id, {})
            last_time = student_store.get(topic)
            if last_time is None:
                return False

            elapsed = time.time() - last_time
            return elapsed < (minutes * 60)

    def record_exposure(
        self,
        student_id: str,
        topic: str,
        action_type: str = "generic",
    ) -> None:
        """
        记录一次暴露事件。

        Args:
            student_id: 学生 ID
            topic: 知识点/动作标识
            action_type: 动作类型，用于查找对应的 TTL
        """
        if not student_id or not topic:
            return

        with self._lock:
            if student_id not in self._store:
                self._store[student_id] = {}
            self._store[student_id][topic] = time.time()

    def get_cooldown_seconds(
        self,
        student_id: str,
        topic: str,
        action_type: str = "generic",
    ) -> int:
        """
        获取某 topic 的剩余冷却时间（秒），0 表示已冷却完毕。
        """
        if not student_id or not topic:
            return 0

        with self._lock:
            student_store = self._store.get(student_id, {})
            last_time = student_store.get(topic)
            if last_time is None:
                return 0

            ttl = self._ttl_map.get(action_type, 30 * 60)
            elapsed = time.time() - last_time
            remaining = max(0, int(ttl - elapsed))
            return remaining

    # ------------------------------------------------------------------
    # 批量操作
    # ------------------------------------------------------------------

    def record_link_exposure(
        self,
        student_id: str,
        link_topics: list[str],
    ) -> None:
        """记录一组链接知识点已被暴露（通常由 LinkRecommender 调用）"""
        for topic in link_topics:
            self.record_exposure(student_id, topic, "link_click")

    def filter_exposed(
        self,
        student_id: str,
        topics: list[str],
        minutes: int = 30,
    ) -> list[str]:
        """
        从 topic 列表中过滤掉仍在冷却期内的。

        Returns:
            未被暴露过的 topic 列表
        """
        return [
            t for t in topics
            if not self.recently_exposed(student_id, t, minutes)
        ]

    # ------------------------------------------------------------------
    # 清理
    # ------------------------------------------------------------------

    def clear_student(self, student_id: str) -> None:
        """清空某学生的全部记录（用于测试或注销）"""
        with self._lock:
            self._store.pop(student_id, None)

    def clear_all(self) -> None:
        """清空全部记录（谨慎使用）"""
        with self._lock:
            self._store.clear()

    def cleanup_expired(self, max_age_hours: int = 48) -> int:
        """
        清理过期的记录，返回清理的数量。
        建议由后台定时任务调用。
        """
        cutoff = time.time() - (max_age_hours * 3600)
        cleaned = 0

        with self._lock:
            for student_id in list(self._store.keys()):
                student_store = self._store[student_id]
                expired_topics = [
                    t for t, ts in student_store.items()
                    if ts < cutoff
                ]
                for t in expired_topics:
                    del student_store[t]
                    cleaned += 1
                if not student_store:
                    del self._store[student_id]

        return cleaned
