# -*- coding: utf-8 -*-
"""
Profile Aggregator — 将分散的 user_memories 聚合成"AI眼中的你"画像数据

Usage:
    from app.services.profile_aggregator import aggregate_profile
    from db import get_user_memories

    profile = aggregate_profile(get_user_memories(user_id))
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

# 记忆类型 → 画像类别映射
MEMORY_TYPE_TO_CATEGORY = {
    "learning_trait": "learning_traits",
    "knowledge": "learning_traits",
    "personality": "personality_traits",
    "emotion": "personality_traits",
    "interaction": "personality_traits",
    "background": "goals_interests",
    "preference": "goals_interests",
    "interest": "goals_interests",
    "goal": "goals_interests",
}


def _calculate_score(confidence: float, access_count: int, confirmed: int) -> float:
    """计算画像特质的得分。

    公式: confidence * 0.6 + min(access_count / 10, 0.3) + confirmed_bonus(0.1)
    """
    access_score = min(access_count / 10, 0.3)
    confirmed_bonus = 0.1 if confirmed else 0.0
    return confidence * 0.6 + access_score + confirmed_bonus


def aggregate_profile(
    memories: list[dict[str, Any]],
    max_per_category: int = 5,
) -> dict[str, Any]:
    """将 user_memories 聚合成画像数据。

    Args:
        memories: get_user_memories() 返回的记忆列表
        max_per_category: 每个类别的最大特质数量（默认5）

    Returns:
        {
            "last_updated": "2026-05-29T10:30:00Z",
            "learning_traits": [
                {
                    "label": "...",
                    "score": 0.95,
                    "memory_id": "...",
                    "memory_type": "...",
                    "confidence": 0.9,
                    "access_count": 5,
                }
            ],
            "personality_traits": [...],
            "goals_interests": [...],
        }
    """
    # 按类别分组
    categorized: dict[str, list[dict[str, Any]]] = {
        "learning_traits": [],
        "personality_traits": [],
        "goals_interests": [],
    }

    for mem in memories:
        memory_type = mem.get("memory_type", "")
        category = MEMORY_TYPE_TO_CATEGORY.get(memory_type)
        if not category:
            continue

        confidence = float(mem.get("confidence", 0.8))
        access_count = int(mem.get("access_count", 0) or 0)
        confirmed = int(mem.get("confirmed", 0) or 0)
        score = _calculate_score(confidence, access_count, confirmed)

        categorized[category].append({
            "label": mem.get("content", ""),
            "score": round(score, 4),
            "memory_id": mem.get("id", ""),
            "memory_type": memory_type,
            "confidence": confidence,
            "access_count": access_count,
        })

    # 对每个类别按分数降序排序，取前 N 个
    result: dict[str, Any] = {
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "learning_traits": [],
        "personality_traits": [],
        "goals_interests": [],
    }

    for category, traits in categorized.items():
        traits.sort(key=lambda x: x["score"], reverse=True)
        result[category] = traits[:max_per_category]

    return result
