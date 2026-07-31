# -*- coding: utf-8 -*-
"""用户画像 API — GET /api/profile/{user_id}

返回聚合后的用户画像数据（"AI眼中的你"）。
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.api.auth import require_user_or_teacher
from app.core.repository_factory import get_repository_for_user
from app.services.profile_aggregator import aggregate_profile
from app.services.repository import DemoRepository

router = APIRouter(prefix="/profile", tags=["profile"])

# 单一 Repository 实例 (P0 阶段无状态; P1 阶段会注入 session).
_demo_repo = DemoRepository()


@router.get("/{user_id}")
async def get_profile(user_id: str):
    """获取用户的聚合画像（AI眼中的你）。"""
    try:
        repository = get_repository_for_user(user_id, repository_type="chat")
        memories = repository.get_memories(user_id, limit=200)
        profile = aggregate_profile(memories)
        return {
            "success": True,
            "user_id": user_id,
            "profile": profile,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取画像失败: {e}")


# ============================================================
# P0 比赛模式: 掌握度变化 + 推荐理由 卡片 (Task 16)
# P1 Task 21: 加 require_user_or_teacher 守卫, 学生只能读自己.
# 路径: GET /api/profile/{user_id}/mastery-diff
#       GET /api/profile/{user_id}/recommendations
# 设计: 走 DemoRepository, 失败 fallback 永远结构正确.
# ============================================================


@router.get("/{user_id}/mastery-diff")
async def get_mastery_diff(user_id: str, request: Request) -> dict:
    """返回本次学习前后掌握度差异, 供前端"掌握度变化"卡片渲染.

    P1 Task 21: 仅本人或教师/管理员可访问.
    """
    # 守卫: 越权直接 raise 401/403
    require_user_or_teacher(user_id, request)
    try:
        return _demo_repo.diff_mastery(user_id)
    except Exception as exc:  # noqa: BLE001
        return {
            "user_id": user_id,
            "items": [],
            "fallback": True,
            "error": str(exc),
        }


@router.get("/{user_id}/recommendations")
async def get_recommendations(user_id: str, request: Request) -> dict:
    """返回推荐项 + 理由, 供前端"为什么推荐这个"卡片.

    P1 Task 21: 仅本人或教师/管理员可访问.
    """
    require_user_or_teacher(user_id, request)
    try:
        return _demo_repo.load_recommendations(user_id)
    except Exception as exc:  # noqa: BLE001
        return {
            "recommendations": [],
            "fallback": True,
            "error": str(exc),
        }
