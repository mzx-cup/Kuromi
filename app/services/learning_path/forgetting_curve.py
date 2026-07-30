"""SM-2 间隔重复算法（Anki 经典实现 + 个性化 stability 拟合）（M3.5）

SM-2 算法核心：
  - 答对（quality >= 3）：interval 按 [1, 3, 6, 12, ...] 规律递增，乘以 stability
  - 答错（quality < 3）：reps 重置为 0，lapses +1
  - stability 动态调整：基于答题质量，floor 1.3

被以下模块引用：
  - app/services/learning_path/review_scheduler.py（M3.6 每日复习）
  - app/api/learning_path.py（未来：学生查询下次复习时间）
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class LearningState:
    """某个 (user_id, topic_id) 的学习记忆状态。"""

    user_id: str
    topic_id: str
    stability: float = 2.5  # 个性化遗忘率参数（基于历史拟合）
    difficulty: float = 5.0  # 0-10 难度
    reps: int = 0  # 连续正确次数
    lapses: int = 0  # 失败次数
    last_review: datetime | None = None
    interval: float = 1.0  # 当前间隔（天）


class SM2Scheduler:
    """SM-2 间隔重复调度器。"""

    # SM-2 经典稳定性下限
    MIN_STABILITY = 1.3

    # SM-2 经典间隔（天）：reps==1 → 1, reps==2 → 3, reps>=3 → prev * stability
    FIRST_INTERVAL = 1.0
    SECOND_INTERVAL = 3.0

    def next_review(self, state: LearningState, now: datetime) -> datetime:
        """根据 state 计算下次复习时间。"""
        return now + timedelta(days=state.interval)

    def review(
        self,
        state: LearningState,
        quality: int,
        now: datetime,
    ) -> tuple[LearningState, datetime]:
        """根据答题质量（0-5）更新 state，返回 (新 state, 下次复习时间)。

        Args:
            state: 当前学习状态
            quality: 0-5（0=完全遗忘，5=完美回忆；<3 视为失败）
            now: 当前时间
        """
        new_state = LearningState(
            user_id=state.user_id,
            topic_id=state.topic_id,
            stability=state.stability,
            difficulty=state.difficulty,
            reps=state.reps,
            lapses=state.lapses,
            last_review=now,
            interval=state.interval,
        )

        if quality < 3:
            # 失败：重置 reps，lapses +1
            new_state.reps = 0
            new_state.lapses += 1
            new_state.interval = self.FIRST_INTERVAL
        else:
            # 成功：根据 SM-2 公式更新 interval
            new_state.reps += 1
            if new_state.reps == 1:
                new_state.interval = self.FIRST_INTERVAL
            elif new_state.reps == 2:
                new_state.interval = self.SECOND_INTERVAL
            else:
                new_state.interval = max(1.0, state.interval * state.stability)

        # 更新 stability（基于答题质量），floor MIN_STABILITY
        # 公式：S' = S + (0.1 - (5-q) * (0.08 + (5-q) * 0.02))
        new_state.stability = max(
            self.MIN_STABILITY,
            state.stability + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)),
        )

        return new_state, self.next_review(new_state, now)