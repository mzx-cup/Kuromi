# -*- coding: utf-8 -*-
"""演示主链数据访问入口 (Repository 模式).

设计原则:
- 演示路由 (app/api/demo_path.py) 仅通过本类访问数据, 不直接 import db.py.
- P0 阶段: 返回静态种子数据, 确保演示主链在没有真实数据库时也能跑通.
- P1 阶段: 把 P0 占位替换为对 `app.services.demo_seeder` 或 ORM 的真实查询,
           不修改本类的对外接口.

回退策略:
- 任一方法失败 (异常) 时, 必须返回**结构上等价**的种子数据, 并打上 `fallback=True`.
  这样调用方 (前端 / 路由) 永远能拿到形状正确的 JSON, 不会因 DB 抖动空指针.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("starlearn.repository.demo")


class DemoRepository:
    """演示主链数据访问层."""

    def load_profile(self, user_id: str) -> dict[str, Any]:
        """加载学习画像 (radar + cards)."""
        try:
            return {
                "user_id": user_id,
                "radar": {
                    "concept": 0.7,
                    "logic": 0.6,
                    "computation": 0.8,
                    "application": 0.5,
                },
                "cards": {
                    "weak": ["recursion", "induction"],
                    "strong": ["arithmetic"],
                },
                "fallback": False,
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("load_profile fallback user_id=%s err=%s", user_id, exc)
            return {"user_id": user_id, "radar": {}, "cards": {}, "fallback": True}

    def load_weak_concepts(self, user_id: str) -> list[dict[str, Any]]:
        """加载弱点概念列表. 用于"诊断我的弱点"卡片."""
        return [
            {"concept": "recursion", "score": 0.4, "evidence": "missed 3/5 exercises"},
            {"concept": "induction", "score": 0.45, "evidence": "low confidence in chat"},
        ]

    def load_learning_path(self, user_id: str) -> dict[str, Any]:
        """加载学习路径节点. 每次调用返回新对象, 避免调用方误改种子."""
        return {
            "user_id": user_id,
            "nodes": [
                {"id": "n1", "title": "递归入门", "concept": "recursion", "weight": 0.8},
                {"id": "n2", "title": "数学归纳法", "concept": "induction", "weight": 0.6},
                {"id": "n3", "title": "动态规划基础", "concept": "dp", "weight": 0.4},
            ],
            "fallback": False,
        }

    def save_mastery(self, user_id: str, concept: str, score: float) -> None:
        """保存掌握度变化. P0 阶段仅记录日志, 不写库."""
        logger.info("save_mastery user_id=%s concept=%s score=%.2f", user_id, concept, score)
        return None

    def diff_mastery(self, user_id: str) -> dict[str, Any]:
        """返回本次学习前后掌握度差异. 供前端 "掌握度变化" 卡片渲染."""
        return {
            "user_id": user_id,
            "items": [
                {"concept": "recursion", "before": 0.40, "after": 0.55, "delta": 0.15},
                {"concept": "induction", "before": 0.45, "after": 0.50, "delta": 0.05},
            ],
            "fallback": False,
        }

    def load_recommendations(self, user_id: str) -> dict[str, Any]:
        """返回推荐项 + 理由. 供前端 "为什么推荐这个" 卡片."""
        return {
            "recommendations": [
                {
                    "title": "递归入门",
                    "reason": "你最近 3 次关于递归的练习正确率低于 50%",
                    "evidence": "exercises: rec_01, rec_02, rec_03 (1/3 correct)",
                },
                {
                    "title": "数学归纳法",
                    "reason": "你在对话中表现出对基础步骤不熟",
                    "evidence": "chat trace lp_xxx step=diagnose",
                },
            ],
            "fallback": False,
        }
