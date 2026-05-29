# -*- coding: utf-8 -*-
"""用户画像 API — GET /api/profile/{user_id}

返回聚合后的用户画像数据（"AI眼中的你"）。
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services.profile_aggregator import aggregate_profile

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/{user_id}")
def get_profile(user_id: str):
    """获取用户的聚合画像（AI眼中的你）。"""
    try:
        from db import get_user_memories
        memories = get_user_memories(user_id, limit=200)
        profile = aggregate_profile(memories)
        return {
            "success": True,
            "user_id": user_id,
            "profile": profile,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取画像失败: {e}")
