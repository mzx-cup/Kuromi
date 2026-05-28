# -*- coding: utf-8 -*-
"""
StateRepository — 学生状态持久化仓库

桥接内存中的 StudentState 和数据库持久化：
  - 对话历史保存到 messages 表（逐条 INSERT）
  - 会话摘要保存到 conversation_summaries 表
  - 其他状态（profile、emotion、path）保持 JSON 存储（兼容现有机制）

用法（在 API 层中）：
    repo = StateRepository(db_session)
    state = await repo.load_state(student_id, course_id, context_id)
    # ... AI 处理 ...
    await repo.sync_messages(state)   # 把新消息写入 DB
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.message_service import MessageService
from app.models.message import ConversationSummary
from state import StudentState, ChatMessage, DialogueRole


class StateRepository:
    """StudentState 持久化仓库 — 统一出入口"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.msg_svc = MessageService(db)

    # ============================================================
    # 加载
    # ============================================================

    async def load_state(
        self,
        student_id: str,
        course_id: str,
        context_id: str,
        load_history: bool = True,
        history_limit: int = 50,
    ) -> StudentState:
        """
        加载或创建 StudentState。

        如果 context_id 对应的数据库 session 存在，从 messages 表加载最近消息；
        否则创建一个新的 StudentState（session_id 自动生成）。
        """
        # session_id 与 context_id 复用（或者可以用 "sess_{context_id}" 前缀）
        session_id = context_id or f"sess_{student_id}_{course_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        state = StudentState(
            student_id=student_id,
            course_id=course_id,
            context_id=context_id,
            session_id=session_id,
        )

        if load_history:
            # 从数据库加载最近 N 条消息
            recent = await self.msg_svc.get_recent_context(session_id, n=history_limit)
            for msg in recent:
                role = DialogueRole.STUDENT if msg.role == "user" else DialogueRole.SYSTEM
                state.dialogue_history.append(ChatMessage(
                    role=role,
                    content=msg.content,
                    timestamp=msg.created_at,
                    metadata=msg.metadata or {},
                ))

        return state

    # ============================================================
    # 同步
    # ============================================================

    async def sync_messages(self, state: StudentState) -> int:
        """
        将 StudentState.dialogue_history 中尚未持久化的消息写入数据库。

        Returns:
            写入的消息数量
        """
        if not state.session_id:
            return 0

        # 获取当前数据库中该会话的消息数量
        db_count = await self.msg_svc.get_message_count(state.session_id)

        # 内存中比数据库多的部分就是新消息
        new_messages = state.dialogue_history[db_count:]
        if not new_messages:
            return 0

        saved = 0
        for cm in new_messages:
            role = "user" if cm.role == DialogueRole.STUDENT else "assistant"
            msg_type = cm.metadata.get("message_type", "text")
            await self.msg_svc.save_message(
                session_id=state.session_id,
                student_id=state.student_id,
                role=role,
                content=cm.content,
                message_type=msg_type,
                metadata=cm.metadata,
            )
            saved += 1

        return saved

    async def save_message(
        self,
        state: StudentState,
        role: str,
        content: str,
        message_type: str = "text",
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        同时保存到内存和数据库（API 层调用，替代 state.add_message() + 手动写 DB）。

        Args:
            role: "user" | "assistant" | "system" | "tool"
        """
        # 1. 内存中追加
        dialogue_role = DialogueRole.STUDENT if role == "user" else DialogueRole.SYSTEM
        state.add_message(dialogue_role, content, metadata or {})

        # 2. 数据库持久化
        if state.session_id:
            await self.msg_svc.save_message(
                session_id=state.session_id,
                student_id=state.student_id,
                role=role,
                content=content,
                message_type=message_type,
                metadata=metadata,
            )

    # ============================================================
    # 摘要管理
    # ============================================================

    async def get_summary(self, state: StudentState) -> Optional[ConversationSummary]:
        """获取会话摘要"""
        if not state.session_id:
            return None
        return await self.msg_svc.get_or_create_summary(
            state.session_id, state.student_id
        )

    async def update_summary(
        self,
        state: StudentState,
        summary_text: str,
        key_facts: Optional[dict[str, Any]] = None,
    ) -> None:
        """更新会话摘要（AI 服务生成后调用）"""
        if not state.session_id:
            return
        await self.msg_svc.update_summary(
            state.session_id, summary_text, key_facts
        )

    # ============================================================
    # 统计
    # ============================================================

    async def get_stats(self, state: StudentState, days: int = 30) -> dict[str, Any]:
        """获取当前学生的聊天统计"""
        return await self.msg_svc.get_student_stats(state.student_id, days=days)
