# -*- coding: utf-8 -*-
"""
消息存储模型 — 支持聊天记录持久化与分层存储

数据流向:
  用户/AI 消息 → MessageService.save_message() → messages 表
  会话摘要     → ConversationSummary 表（供快速恢复上下文）
  历史归档     → 超过保留期的消息 → S3/Parquet（未来扩展）
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, func, Index
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Message(Base):
    """单条聊天消息 — 独立存储，支持游标分页、全文搜索、冷热分层"""

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True,
        comment="会话/课堂 ID，关联 classroom_sessions 或独立聊天会话"
    )
    student_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True,
        comment="学生 ID"
    )

    role: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True,
        comment="消息角色: user | assistant | system | tool"
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="消息文本内容（Markdown 格式）"
    )

    # 消息类型细分 — 用于统计和筛选
    message_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="text", index=True,
        comment="消息类型: text | action | link | image | tool_call | proactive"
    )

    # 不常查询的元数据放 JSON，保持表结构稳定
    msg_metadata: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True,
        comment="扩展元数据: agent_id, links, actions, tokens_used, model, latency_ms..."
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), index=True,
        comment="消息创建时间（UTC）"
    )

    # 软删除 — 物理删除由后台归档任务异步处理
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True,
        comment="软删除时间，NULL 表示未删除"
    )

    __table_args__ = (
        # 复合索引：按会话 + 时间倒序查询对话历史（最常用）
        Index("ix_messages_session_time", "session_id", "created_at"),
        # 复合索引：按学生 + 时间查询全部历史
        Index("ix_messages_student_time", "student_id", "created_at"),
        # 复合索引：按角色 + 类型统计（如统计 AI 推荐了多少链接）
        Index("ix_messages_role_type", "role", "message_type"),
    )


class ConversationSummary(Base):
    """会话摘要 — 长对话的"记忆压缩"，避免每次加载全部消息"""

    __tablename__ = "conversation_summaries"

    session_id: Mapped[str] = mapped_column(
        String(64), primary_key=True,
        comment="关联的会话 ID"
    )
    student_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True,
        comment="学生 ID"
    )

    summary_text: Mapped[str] = mapped_column(
        Text, nullable=False, default="",
        comment="AI 生成的会话摘要（200 字以内）"
    )

    # 关键事实结构化存储 — 用于 AI 上下文恢复
    key_facts: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True,
        comment="结构化关键信息: {topic, current_chapter, difficulties, preferences}"
    )

    message_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="当前会话消息总数"
    )

    # 热度标记 — 用于冷热分层决策
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), index=True,
        comment="最后一条消息时间"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), onupdate=func.now(),
        comment="摘要最后更新时间"
    )
