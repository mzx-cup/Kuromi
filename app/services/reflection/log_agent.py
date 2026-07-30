"""反思日志 Agent（M5.4 / #21）

每次学习结束弹出 3 个元认知问题；每周聚合成教研数据。

与 app.services.agent.reflection_agent 并存：本模块提供极简 API（generate_questions + aggregate_weekly），
供前端直接调用；agent.reflection_agent 提供更复杂的触发 / 提示工程逻辑。
"""
from __future__ import annotations

from collections import defaultdict


class ReflectionLogAgent:
    """反思日志 Agent（极简版）。"""

    # 三个元认知问题模板
    QUESTIONS: list[str] = [
        "刚才卡在哪一步？为什么？",
        "如果换一种条件，你会怎么做？",
        "怎么用自己的话给别人讲一遍？",
    ]

    async def generate_questions(self, topic: str) -> list[str]:
        """生成 3 个针对 topic 的元认知问题。"""
        return [q + f"（针对：{topic}）" for q in self.QUESTIONS]

    async def aggregate_weekly(self, reflections: list[dict]) -> dict:
        """按 topic 分组聚合反思记录。

        Args:
            reflections: [{user_id, topic, answer, ...}, ...]

        Returns:
            {
              "<topic>": {"count": int, "samples": [<answer>, ...up to 3]}
            }
        """
        grouped: dict[str, list[dict]] = defaultdict(list)
        for r in reflections:
            topic = r.get("topic", "未分类")
            grouped[topic].append(r)

        return {
            topic: {
                "count": len(items),
                "samples": [item.get("answer", "") for item in items[:3]],
            }
            for topic, items in grouped.items()
        }