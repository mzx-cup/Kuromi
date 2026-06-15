# -*- coding: utf-8 -*-
"""
TutorDecisionEngine 数据模型 — 事件、上下文、响应信封

设计原则：
  - 所有模型用 dataclass / enum，轻量、可序列化
  - 与现有数据库模型解耦（不依赖 SQLAlchemy），便于独立测试
  - 保留与前端 SSE 协议的兼容性
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, IntEnum
from typing import Any, AsyncIterator, Optional


# ============================================================
# 事件类型
# ============================================================

class TutorEventType(Enum):
    """所有进入决策引擎的学生交互事件"""

    # 核心问答
    QUESTION_ASKED = "question_asked"

    # 困难与行为干预
    STRUGGLE_DETECTED = "struggle_detected"
    CODE_NOT_WRITTEN = "code_not_written"       # 只看没写代码
    CODE_NOT_RUN = "code_not_run"               # 写了没运行
    ERROR_IGNORED = "error_ignored"             # 报错后不查看
    COPY_PASTE_DETECTED = "copy_paste_detected" # 复制粘贴代码
    DEPRECATED_API_USED = "deprecated_api_used" # 使用过时API
    TAB_SWITCHING = "tab_switching"             # 频繁切换标签页
    CONSECUTIVE_WRONGS = "consecutive_wrongs"   # 连续答错

    # 复习与进度
    REVIEW_DUE = "review_due"
    DEADLINE_APPROACHING = "deadline_approaching"
    DAILY_PLAN_INCOMPLETE = "daily_plan_incomplete"
    PATH_DEVIATION = "path_deviation"
    PREREQUISITE_UNLOCKED = "prerequisite_unlocked"
    LEARNING_SLUMP = "learning_slump"

    # 时机与问候
    LOGIN_GREETING = "login_greeting"
    PROGRESS_MILESTONE = "progress_milestone"
    GOLDEN_HOUR = "golden_hour"
    FRAGMENT_TIME = "fragment_time"
    IDLE_TIMEOUT = "idle_timeout"


@dataclass
class EventContext:
    """事件发生时的环境上下文"""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    page: str = ""           # 当前页面路径，如 "index", "classroom"
    zone: str = ""           # 页面区域，如 "chat", "editor", "video"
    device_type: str = "desktop"  # desktop | tablet | mobile
    session_id: str = ""


@dataclass
class TutorEvent:
    """统一事件 —— 所有学生交互的入口"""
    type: TutorEventType
    student_id: str
    course_id: Optional[str] = None
    payload: dict[str, Any] = field(default_factory=dict)
    context: EventContext = field(default_factory=EventContext)

    def get_question_text(self) -> str:
        """快捷获取提问文本（QUESTION_ASKED 事件）"""
        return self.payload.get("question", "")

    def get_struggle_metrics(self) -> dict[str, Any]:
        """快捷获取困难指标（STRUGGLE_DETECTED 事件）"""
        return self.payload.get("struggle_metrics", {})


# ============================================================
# 优先级
# ============================================================

class MessagePriority(IntEnum):
    CRITICAL = 0   # 立即推送，可打断当前流程
    HIGH = 1       # 尽快推送
    NORMAL = 2     # 普通优先级
    LOW = 3        # 不打扰，被动展示


# ============================================================
# RichContext —— ContextAggregator 的输出
# ============================================================

@dataclass
class RAGResult:
    """教材检索结果"""
    source_id: str
    content: str
    source_title: str = ""
    chapter_id: str = ""
    node_id: str = ""
    relevance_score: float = 0.0
    has_practice_page: bool = False
    has_detail_page: bool = False
    summary: str = ""
    deep_link: str = ""


@dataclass
class SearchResult:
    """Web 搜索结果"""
    title: str
    url: str
    content: str = ""
    snippet: str = ""
    score: float = 0.0
    domain: str = ""


@dataclass
class Memory:
    """学生记忆片段"""
    id: str
    content: str
    memory_type: str = ""
    confidence: float = 1.0
    access_count: int = 0
    confirmed: bool = False


@dataclass
class LearningState:
    """学生学习状态快照"""
    current_course_id: str = ""
    current_chapter_id: str = ""
    progress_percent: float = 0.0
    today_minutes: int = 0
    weekly_minutes: int = 0
    streak_days: int = 0
    days_since_last: int = 0
    week_progress_percent: float = 0.0
    is_weekend: bool = False
    recent_errors: list[str] = field(default_factory=list)
    last_study_topic: str = ""


@dataclass
class ReviewItem:
    """SM2 遗忘曲线复习项"""
    id: str
    knowledge_point: str
    due_at: datetime = field(default_factory=datetime.utcnow)
    priority: float = 0.0
    course_id: str = ""
    node_id: str = ""

    def is_due_now(self) -> bool:
        return self.due_at <= datetime.utcnow()


@dataclass
class Deadline:
    """课程/作业截止日期"""
    task_id: str
    task_name: str
    due_at: datetime = field(default_factory=datetime.utcnow)
    course_id: str = ""
    days_left: int = 0


@dataclass
class RichContext:
    event: TutorEvent

    # 知识层
    rag_results: list[RAGResult] = field(default_factory=list)
    web_results: list[SearchResult] = field(default_factory=list)
    memories: list[Memory] = field(default_factory=list)

    # 学习状态层
    learning_state: LearningState = field(default_factory=LearningState)
    sm2_due_items: list[ReviewItem] = field(default_factory=list)
    upcoming_deadlines: list[Deadline] = field(default_factory=list)

    # 对话层
    conversation_history: list[dict[str, Any]] = field(default_factory=list)

    # 原始检索文本（供 LLM prompt 使用）
    rag_context_text: str = ""
    web_context_text: str = ""
    memory_context_text: str = ""


# ============================================================
# ResponseEnvelope —— 统一响应信封
# ============================================================

@dataclass
class Citation:
    """教材引用 —— 防幻觉 + 前端"参考来源"卡片"""
    source_id: str
    source_title: str
    quoted_text: str = ""
    chapter_url: str = ""
    confidence: float = 1.0
    validated: bool = True  # HallucinationGuard 校验结果

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_title": self.source_title,
            "quoted_text": self.quoted_text,
            "chapter_url": self.chapter_url,
            "confidence": self.confidence,
            "validated": self.validated,
        }


@dataclass
class Link:
    """学习链接 —— 内部/外部"""
    type: str  # "internal" | "external"
    title: str
    url: str
    description: str = ""
    icon: str = ""
    badge: str = ""       # 如 "🔥 今日待复习", "⏰ 即将截止"
    source: str = ""      # "rag" | "web_search" | "sm2" | "deadline"
    relevance: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "title": self.title,
            "url": self.url,
            "description": self.description,
            "icon": self.icon,
            "badge": self.badge,
            "source": self.source,
            "relevance": self.relevance,
            "metadata": self.metadata,
        }


class ActionType(Enum):
    """主动推送动作类型"""
    STRUGGLE_IDLE = "struggle_idle"
    STRUGGLE_ERROR = "struggle_error"
    ERROR_IGNORED = "error_ignored"
    CONSECUTIVE_WRONGS = "consecutive_wrongs"

    REVIEW_REMINDER = "review_reminder"
    PRACTICE_PROMPT = "practice_prompt"
    DEADLINE_URGENT = "deadline_urgent"
    DEADLINE_WARNING = "deadline_warning"

    HEALTH_REMINDER = "health_reminder"
    FORCED_BREAK = "forced_break"

    DAILY_PLAN_INCOMPLETE = "daily_plan_incomplete"
    PROGRESS_WARNING = "progress_warning"
    PATH_DEVIATION = "path_deviation"
    PREREQUISITE_UNLOCKED = "prerequisite_unlocked"
    LEARNING_SLUMP_RECALL = "learning_slump_recall"

    CODE_NOT_WRITTEN = "code_not_written"
    CODE_NOT_RUN = "code_not_run"
    COPY_PASTE_DETECTED = "copy_paste_detected"
    DEPRECATED_API_USED = "deprecated_api_used"
    TAB_SWITCHING = "tab_switching"
    REPEATED_ERROR_PATTERN = "repeated_error_pattern"
    STUCK_RECOMMEND_EASIER = "stuck_recommend_easier"
    PREREQUISITE_MISSING = "prerequisite_missing"

    DAILY_GREETING = "daily_greeting"
    RETURN_RECALL = "return_recall"
    MILESTONE_CELEBRATION = "milestone_celebration"

    GOLDEN_HOUR = "golden_hour"
    FRAGMENT_TIME = "fragment_time"


@dataclass
class ProactiveAction:
    """主动推送动作 —— 由 ProactiveAdvisor 生成"""
    action_type: ActionType
    priority: MessagePriority
    delay_seconds: int = 0
    content: str = ""
    title: str = ""
    attached_link: Optional[Link] = None
    action_label: str = ""       # 按钮文案，如 "去做练习"
    action_payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_sse_data(self) -> dict[str, Any]:
        """转换为前端 SSE 可消费的格式（与现有 proactive_tutor.py 兼容）"""
        return {
            "envelope": {
                "type": "proactive",
                "msg_type": self.action_type.value,
                "priority": self.priority.value,
                "action_type": self.action_type.value,
            },
            "payload": {
                "title": self.title,
                "content": self.content,
                "action_label": self.action_label,
                "action_payload": self.action_payload,
                "link": {
                    "title": self.attached_link.title,
                    "url": self.attached_link.url,
                    "type": self.attached_link.type,
                } if self.attached_link else None,
            },
        }


@dataclass
class ConfidenceReport:
    """防幻觉报告 —— 调试用"""
    citation_count: int = 0
    citation_validated: bool = False
    web_search_used: bool = False
    web_consistency: float = 0.0
    code_verified: bool = False
    code_execution_result: str = ""
    rag_relevance_max: float = 0.0
    final_confidence: float = 0.0
    uncertainty_note: str = ""
    blocked: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "citation_count": self.citation_count,
            "citation_validated": self.citation_validated,
            "web_search_used": self.web_search_used,
            "web_consistency": self.web_consistency,
            "code_verified": self.code_verified,
            "code_execution_result": self.code_execution_result,
            "rag_relevance_max": self.rag_relevance_max,
            "final_confidence": self.final_confidence,
            "uncertainty_note": self.uncertainty_note,
            "blocked": self.blocked,
        }


@dataclass
class ResponseEnvelope:
    """统一响应信封 —— 引擎的最终输出"""
    # 核心回答（SSE 流）
    answer_stream: Optional[AsyncIterator[str]] = None
    answer_text: str = ""  # 非流式场景的完整文本

    # 教材引用（防幻觉 + 前端"参考来源"）
    citations: list[Citation] = field(default_factory=list)

    # 学习链接
    links: list[Link] = field(default_factory=list)

    # 主动推送决策
    proactive_actions: list[ProactiveAction] = field(default_factory=list)

    # 防幻觉报告
    confidence_report: ConfidenceReport = field(default_factory=ConfidenceReport)

    # 调试信息
    engine_trace: list[str] = field(default_factory=list)

    def to_sse_complete_event(self) -> dict[str, Any]:
        """
        转换为 SSE complete 事件数据。
        前端现有代码在 `complete` 事件中读取 `links` 字段。
        """
        return {
            "type": "complete",
            "citations": [
                {
                    "source_id": c.source_id,
                    "source_title": c.source_title,
                    "quoted_text": c.quoted_text,
                    "chapter_url": c.chapter_url,
                    "validated": c.validated,
                }
                for c in self.citations
            ],
            "links": [
                {
                    "type": l.type,
                    "title": l.title,
                    "url": l.url,
                    "description": l.description,
                    "icon": l.icon,
                    "badge": l.badge,
                    "source": l.source,
                }
                for l in self.links
            ],
            "confidence_report": {
                "final_confidence": self.confidence_report.final_confidence,
                "blocked": self.confidence_report.blocked,
            } if self.confidence_report else None,
            "proactive_actions": [
                {
                    "action_type": a.action_type.value,
                    "priority": a.priority.value,
                    "delay_seconds": a.delay_seconds,
                    "content": a.content,
                }
                for a in self.proactive_actions
            ],
        }
