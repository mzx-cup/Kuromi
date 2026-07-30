"""变式题生成器（M5.3 / #20）

同知识点不同情境 / 不同表述的变式题生成器。
注意：这是简化版（场景轮换 + 表述前缀），与 app.services.agent.variant_question_generator 并存。
"""
from __future__ import annotations

import copy

# 备选情境池（生产应接 LLM 动态生成）
SCENARIOS = ["水果", "动物", "交通工具", "文具", "食物", "玩具"]


class VariantGenerator:
    """变式题生成器。"""

    def generate(self, base: dict, count: int = 3) -> list[dict]:
        """根据 base 题目生成 count 个变式。

        Args:
            base: 原题 dict（含 id / stem / answer / knowledge_point / scenario）
            count: 生成数量

        Returns:
            list of variant dict（含 is_variant=True / parent_id=base.id）
        """
        variants: list[dict] = []
        base_scenario = base.get("scenario", "水果")
        try:
            start_idx = SCENARIOS.index(base_scenario)
        except ValueError:
            start_idx = 0

        for i in range(count):
            v = copy.deepcopy(base)
            v["scenario"] = SCENARIOS[(start_idx + i + 1) % len(SCENARIOS)]
            v["stem"] = f"如果用 {v['scenario']} 来算：{base['stem']}"
            v["is_variant"] = True
            v["parent_id"] = base.get("id")
            v["id"] = f"{base.get('id', 'ex')}_v{i + 1}"
            variants.append(v)

        return variants