# -*- coding: utf-8 -*-
"""
MessageService — 聊天消息存储与查询服务

职责:
  - 保存用户/AI 消息到 messages 表
  - 分页加载对话历史（游标分页，支持超大对话）
  - 提取最近 N 条消息作为 AI 上下文
  - 维护会话摘要（conversation_summaries 表）

设计原则:
  - 写入路径简单直接（单次 INSERT）
  - 读取路径支持游标分页（不用 OFFSET，越往后越慢）
  - 长对话自动触发摘要生成，减少全量加载

冷热分层（未来扩展）:
  - Hot:   最近 30 天消息 → 数据库（当前实现）
  - Warm:  31~365 天     → 归档分区 / 慢磁盘
  - Cold:  1 年以上       → S3/Parquet（仅合规审计）
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import desc, select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message, ConversationSummary


class MessageService:
    """消息存储服务 — 统一入口"""

    # 长对话阈值：超过此数量触发摘要生成
    SUMMARY_THRESHOLD = 50

    # 上下文窗口：给 AI 做上下文时取最近 N 条
    CONTEXT_WINDOW = 10

    # 分页大小
    PAGE_SIZE = 50

    def __init__(self, db: AsyncSession):
        self.db = db

    # ============================================================
    # 写入
    # ============================================================

    async def save_message(
        self,
        session_id: str,
        student_id: str,
        role: str,
        content: str,
        message_type: str = "text",
        metadata: Optional[dict[str, Any]] = None,
    ) -> Message:
        """保存单条消息并更新会话摘要计数"""
        msg = Message(
            id=f"msg_{uuid.uuid4().hex[:16]}",
            session_id=session_id,
            student_id=student_id,
            role=role,
            content=content,
            message_type=message_type,
            metadata=metadata or {},
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(msg)
        await self.db.flush()

        # 异步更新摘要计数
        await self._bump_summary(session_id, student_id)

        return msg

    async def save_messages_batch(
        self,
        messages: list[dict[str, Any]],
    ) -> list[Message]:
        """批量保存消息（用于初始化/导入场景）"""
        now = datetime.now(timezone.utc)
        objs = []
        for m in messages:
            objs.append(Message(
                id=f"msg_{uuid.uuid4().hex[:16]}",
                session_id=m["session_id"],
                student_id=m["student_id"],
                role=m["role"],
                content=m["content"],
                message_type=m.get("message_type", "text"),
                metadata=m.get("metadata", {}),
                created_at=m.get("created_at", now),
            ))
        self.db.add_all(objs)
        await self.db.flush()
        return objs

    async def soft_delete_message(self, message_id: str) -> bool:
        """软删除单条消息"""
        result = await self.db.execute(
            select(Message).where(
                Message.id == message_id,
                Message.deleted_at.is_(None),
            )
        )
        msg = result.scalar_one_or_none()
        if msg:
            msg.deleted_at = datetime.now(timezone.utc)
            await self.db.flush()
            return True
        return False

    # ============================================================
    # 读取 — 对话历史（游标分页）
    # ============================================================

    async def get_conversation(
        self,
        session_id: str,
        before: Optional[str] = None,
        limit: int = 50,
        include_deleted: bool = False,
    ) -> list[Message]:
        """
        按时间倒序加载对话历史（游标分页）。

        Args:
            session_id: 会话 ID
            before:     游标 — 最后一条消息的 ID，加载此 ID 之前的消息
            limit:      每页条数
            include_deleted: 是否包含软删除消息
        """
        query = select(Message).where(
            Message.session_id == session_id,
        ).order_by(desc(Message.created_at))

        if not include_deleted:
            query = query.where(Message.deleted_at.is_(None))

        if before:
            # 用最后一条消息的时间做游标（比 OFFSET 高效得多）
            cursor_result = await self.db.execute(
                select(Message.created_at).where(Message.id == before)
            )
            cursor_time = cursor_result.scalar_one_or_none()
            if cursor_time:
                query = query.where(Message.created_at < cursor_time)

        query = query.limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_conversation_asc(
        self,
        session_id: str,
        after: Optional[str] = None,
        limit: int = 50,
    ) -> list[Message]:
        """按时间正序加载（用于前端渲染对话流）"""
        query = select(Message).where(
            Message.session_id == session_id,
            Message.deleted_at.is_(None),
        ).order_by(Message.created_at)

        if after:
            cursor_result = await self.db.execute(
                select(Message.created_at).where(Message.id == after)
            )
            cursor_time = cursor_result.scalar_one_or_none()
            if cursor_time:
                query = query.where(Message.created_at > cursor_time)

        query = query.limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ============================================================
    # 读取 — AI 上下文（最近 N 条）
    # ============================================================

    async def get_recent_context(
        self,
        session_id: str,
        n: int = 10,
    ) -> list[Message]:
        """获取最近 N 条消息作为 AI 上下文（正序）"""
        query = (
            select(Message)
            .where(
                Message.session_id == session_id,
                Message.deleted_at.is_(None),
            )
            .order_by(desc(Message.created_at))
            .limit(n)
        )
        result = await self.db.execute(query)
        msgs = list(result.scalars().all())
        msgs.reverse()  # 转为正序
        return msgs

    async def get_message_count(self, session_id: str) -> int:
        """统计会话消息数量"""
        result = await self.db.execute(
            select(func.count(Message.id))
            .where(
                Message.session_id == session_id,
                Message.deleted_at.is_(None),
            )
        )
        return result.scalar_one() or 0

    # ============================================================
    # 会话摘要管理
    # ============================================================

    async def get_or_create_summary(
        self,
        session_id: str,
        student_id: str,
    ) -> ConversationSummary:
        """获取会话摘要，不存在则创建"""
        result = await self.db.execute(
            select(ConversationSummary).where(
                ConversationSummary.session_id == session_id,
            )
        )
        summary = result.scalar_one_or_none()
        if summary is None:
            summary = ConversationSummary(
                session_id=session_id,
                student_id=student_id,
                summary_text="",
                key_facts={},
                message_count=0,
            )
            self.db.add(summary)
            await self.db.flush()
        return summary

    async def update_summary(
        self,
        session_id: str,
        summary_text: str,
        key_facts: Optional[dict[str, Any]] = None,
    ) -> ConversationSummary:
        """更新会话摘要（由 AI 服务调用生成）"""
        result = await self.db.execute(
            select(ConversationSummary).where(
                ConversationSummary.session_id == session_id,
            )
        )
        summary = result.scalar_one_or_none()
        if summary:
            summary.summary_text = summary_text
            if key_facts:
                summary.key_facts = key_facts
            summary.updated_at = datetime.now(timezone.utc)
            await self.db.flush()
        return summary

    async def get_summary_with_context(
        self,
        session_id: str,
        student_id: str,
    ) -> dict[str, Any]:
        """
        获取完整上下文包：摘要 + 最近消息

        返回:
            {
                "summary": ConversationSummary | None,
                "recent_messages": list[Message],
                "total_count": int,
            }
        """
        summary = await self.get_or_create_summary(session_id, student_id)
        recent = await self.get_recent_context(session_id, n=self.CONTEXT_WINDOW)
        total = await self.get_message_count(session_id)
        return {
            "summary": summary,
            "recent_messages": recent,
            "total_count": total,
        }

    # ============================================================
    # 统计与查询
    # ============================================================

    async def get_student_stats(
        self,
        student_id: str,
        days: int = 30,
    ) -> dict[str, Any]:
        """获取学生聊天统计数据"""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        # 总消息数
        total_result = await self.db.execute(
            select(func.count(Message.id))
            .where(
                Message.student_id == student_id,
                Message.created_at >= since,
                Message.deleted_at.is_(None),
            )
        )
        total = total_result.scalar_one() or 0

        # 按角色统计
        role_result = await self.db.execute(
            select(Message.role, func.count(Message.id))
            .where(
                Message.student_id == student_id,
                Message.created_at >= since,
                Message.deleted_at.is_(None),
            )
            .group_by(Message.role)
        )
        by_role = {r: c for r, c in role_result.all()}

        # 按类型统计
        type_result = await self.db.execute(
            select(Message.message_type, func.count(Message.id))
            .where(
                Message.student_id == student_id,
                Message.created_at >= since,
                Message.deleted_at.is_(None),
            )
            .group_by(Message.message_type)
        )
        by_type = {t: c for t, c in type_result.all()}

        # 活跃会话数
        session_result = await self.db.execute(
            select(func.count(func.distinct(Message.session_id)))
            .where(
                Message.student_id == student_id,
                Message.created_at >= since,
                Message.deleted_at.is_(None),
            )
        )
        active_sessions = session_result.scalar_one() or 0

        return {
            "total_messages": total,
            "by_role": by_role,
            "by_type": by_type,
            "active_sessions": active_sessions,
            "period_days": days,
        }

    # ============================================================
    # 冷热分层 — 归档（未来扩展）
    # ============================================================

    async def archive_old_messages(
        self,
        before: datetime,
        dry_run: bool = False,
    ) -> int:
        """
        归档/删除旧消息（后台任务调用）。

        Args:
            before:   归档截止时间
            dry_run:  True 只返回数量不实际删除

        Returns:
            受影响的消息数量
        """
        query = select(func.count(Message.id)).where(
            Message.created_at < before,
            Message.deleted_at.is_(None),
        )
        result = await self.db.execute(query)
        count = result.scalar_one() or 0

        if not dry_run and count > 0:
            # 物理删除（或者导出到 S3 后再删除）
            await self.db.execute(
                delete(Message).where(
                    Message.created_at < before,
                    Message.deleted_at.is_(None),
                )
            )
            await self.db.flush()

        return count

    # ============================================================
    # 内部辅助
    # ============================================================

    async def _bump_summary(self, session_id: str, student_id: str) -> None:
        """更新会话摘要的消息计数和时间戳"""
        result = await self.db.execute(
            select(ConversationSummary).where(
                ConversationSummary.session_id == session_id,
            )
        )
        summary = result.scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if summary:
            summary.message_count += 1
            summary.last_message_at = now
        else:
            summary = ConversationSummary(
                session_id=session_id,
                student_id=student_id,
                summary_text="",
                key_facts={},
                message_count=1,
                last_message_at=now,
            )
            self.db.add(summary)
        await self.db.flush()
