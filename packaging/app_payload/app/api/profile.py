# -*- coding: utf-8 -*-
"""用户画像 API — GET /api/profile/{user_id}

返回聚合后的用户画像数据（"AI眼中的你"）。
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.repository_factory import get_repository_for_user
from app.services.profile_aggregator import aggregate_profile

router = APIRouter(prefix="/profile", tags=["profile"])


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
