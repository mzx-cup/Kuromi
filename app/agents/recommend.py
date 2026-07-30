"""RecommendAgent: 基于学习画像 + 目标差距，生成可解释的推荐（M2.1）

命名实体化的推荐 Agent（替代隐式的 PlannerAgent 推荐逻辑）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class RecommendationResult:
    user_id: str
    recommendation: dict[str, Any]  # {"node_id": ..., "title": ..., "scenario": ...}
    reasoning: str  # 为什么推荐这个（人类可读）
    goal_evidence: str  # 目标差距的具体证据
    capability_rationale: str  # 能力倾向的解释
    confidence: float  # 0.0-1.0

    @property
    def node_id(self) -> str:
        return str(self.recommendation.get("node_id", ""))


class RecommendAgent:
    """命名实体化的推荐 Agent。

    设计要点：
      - 不依赖外部 LLM/数据库，可以离线工作（用于测试 + 教学场景）
      - 基于画像字段：knowledge_mastery / weakness / cognitive_style / goal
      - 返回结构化 RecommendationResult，前端可直接渲染"为什么推这个"卡片
    """

    name = "recommend_agent"

    # 知识点推荐表（按画像薄弱点 → 推荐节点 ID）
    _KNOWLEDGE_MAP: dict[str, dict[str, str]] = {
        "recursion": {
            "node_id": "node_python_recursion_basics",
            "title": "递归基础：从阶乘到斐波那契",
            "scenario": "用递归重写循环逻辑，配套练习",
        },
        "loop": {
            "node_id": "node_python_loop_patterns",
            "title": "循环模式：for / while / enumerate",
            "scenario": "对比 5 种循环写法的适用场景",
        },
        "oop": {
            "node_id": "node_python_oop_pillars",
            "title": "OOP 三大特性：封装 / 继承 / 多态",
            "scenario": "用银行卡类理解封装",
        },
        "default": {
            "node_id": "node_python_basics",
            "title": "Python 入门：变量、类型、控制流",
            "scenario": "从 Hello World 到第一个小游戏",
        },
    }

    def __init__(self) -> None:
        # 留口子：未来可注入 LearningPathAnalyzer
        pass

    async def run(
        self,
        user_id: str,
        current_portrait: dict[str, Any],
        goal: str,
    ) -> RecommendationResult:
        weakness = current_portrait.get("weakness", "")
        mastery = current_portrait.get("knowledge_mastery", 0.0)
        style = current_portrait.get("cognitive_style", "visual")

        # 选择推荐节点
        rec = self._KNOWLEDGE_MAP.get(weakness, self._KNOWLEDGE_MAP["default"])

        # 推理字段（人类可读）
        if weakness:
            reasoning = (
                f"你的画像显示薄弱点是「{weakness}」（掌握度 {mastery:.0%}）。"
                f"先打通这一关，再进入下一个主题。"
            )
        else:
            reasoning = "尚未识别到具体薄弱点，先按通用路径推进基础知识点。"

        goal_evidence = (
            f"目标「{goal}」距离达成仍有差距，"
            f"建议先解决「{rec['title']}」这个前置节点。"
        )

        capability_rationale = (
            f"你的认知风格为「{style}」，本节点配图 + 代码 + 讲解，"
            f"适合{self._style_label(style)}学习者。"
        )

        # confidence 与 mastery 正相关 + 目标明确度
        confidence = min(1.0, 0.5 + mastery * 0.4 + (0.1 if goal else 0.0))

        return RecommendationResult(
            user_id=user_id,
            recommendation={
                "node_id": rec["node_id"],
                "title": rec["title"],
                "scenario": rec["scenario"],
            },
            reasoning=reasoning,
            goal_evidence=goal_evidence,
            capability_rationale=capability_rationale,
            confidence=round(confidence, 2),
        )

    @staticmethod
    def _style_label(style: str) -> str:
        return {
            "visual": "视觉型",
            "auditory": "听觉型",
            "kinesthetic": "动觉型",
        }.get(style, "通用型")