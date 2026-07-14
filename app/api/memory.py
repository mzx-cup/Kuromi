# -*- coding: utf-8 -*-
"""
用户记忆管理 API

GET  /api/memories/{user_id}        — 获取用户记忆列表
POST /api/memories/{memory_id}/confirm — 确认/否认记忆
DELETE /api/memories/{memory_id}    — 删除记忆
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.repository_factory import get_repository_for_user
from db import _is_sqlite, get_db

router = APIRouter(prefix="/memories", tags=["memories"])


class ConfirmMemoryRequest(BaseModel):
    confirmed: bool = True


class CreateMemoryRequest(BaseModel):
    user_id: str = Field(..., description="用户ID")
    content: str = Field(..., min_length=1, description="记忆内容")
    memory_type: str = Field(default="fact", description="记忆类型")


class UpdateMemoryRequest(BaseModel):
    content: str | None = Field(default=None, description="新的记忆内容")
    memory_type: str | None = Field(default=None, description="新的记忆类型")


def _coerce_memory_id(memory_id: str) -> int | str:
    return int(memory_id) if memory_id.isdigit() else memory_id


@router.get("/{user_id}")
def get_memories(user_id: str, memory_type: str | None = None, limit: int = 100):
    """获取用户的长期记忆列表。"""
    try:
        repository = get_repository_for_user(user_id, repository_type="chat")
        memories = repository.get_memories(
            user_id, memory_type=memory_type, limit=limit
        )
        return {
            "success": True,
            "count": len(memories),
            "memories": memories,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询记忆失败: {e}")


@router.post("")
def create_memory(request: CreateMemoryRequest):
    """手动添加一条用户记忆。"""
    try:
        repository = get_repository_for_user(
            request.user_id, repository_type="chat"
        )
        memory_id = repository.save_memory(
            request.user_id,
            {
                "memory_type": request.memory_type,
                "content": request.content,
                "source": "manual",
                "confidence": 0.95,
            },
        )
        return {
            "success": True,
            "memory_id": memory_id,
            "memory": {
                "id": memory_id,
                "user_id": request.user_id,
                "memory_type": request.memory_type,
                "content": request.content,
                "source": "manual",
                "confidence": 0.95,
                "confirmed": 0,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建记忆失败: {e}")


@router.put("/{memory_id}")
def update_memory(memory_id: str, request: UpdateMemoryRequest):
    """编辑一条记忆的内容或类型。"""
    try:
        repository = get_repository_for_user(
            memory_id, repository_type="chat"
        )
        if request.content is not None:
            repository.update_memory(
                _coerce_memory_id(memory_id), {"content": request.content}
            )
        if request.memory_type is not None:
            # ChatRepository does not expose memory-type mutation.
            with get_db() as conn:
                if conn is not None:
                    cursor = conn.cursor()
                    if _is_sqlite(conn):
                        cursor.execute(
                            "UPDATE user_memories SET memory_type=? WHERE id=?",
                            (request.memory_type, memory_id))
                    else:
                        cursor.execute(
                            "UPDATE user_memories SET memory_type=%s WHERE id=%s",
                            (request.memory_type, memory_id))
                    conn.commit()
                    cursor.close()
        return {
            "success": True,
            "memory_id": memory_id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新记忆失败: {e}")


@router.post("/{memory_id}/confirm")
def confirm_memory(memory_id: str, request: ConfirmMemoryRequest):
    """确认或否认一条记忆。"""
    try:
        repository = get_repository_for_user(
            memory_id, repository_type="chat"
        )
        repository.confirm_memory(
            _coerce_memory_id(memory_id), request.confirmed
        )
        return {
            "success": True,
            "memory_id": memory_id,
            "confirmed": request.confirmed,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"确认记忆失败: {e}")


@router.delete("/{memory_id}")
def delete_memory(memory_id: str):
    """删除一条记忆。"""
    try:
        repository = get_repository_for_user(
            memory_id, repository_type="chat"
        )
        repository.delete_memory(_coerce_memory_id(memory_id))
        return {
            "success": True,
            "memory_id": memory_id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除记忆失败: {e}")
