# -*- coding: utf-8 -*-
"""
ContextAggregator — 上下文聚合器

并行聚合单次决策所需的全部上下文：
  - RAG 教材检索
  - Web 搜索
  - 长期记忆
  - 对话历史
  - 学习状态（SM2、截止日期、进度等）

设计原则：
  - 异步并行执行所有 IO 操作（gather）
  - 每个数据源独立失败不阻塞整体（容错）
  - 与具体数据库解耦，通过注入的 service/函数访问数据
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable, Optional

from app.services.tutor_engine.models import (
    Deadline,
    EventContext,
    LearningState,
    Memory,
    RAGResult,
    ReviewItem,
    RichContext,
    SearchResult,
    TutorEvent,
)

from app.core.repository_factory import get_repository_for_user

logger = logging.getLogger("starlearn.tutor_engine")


# ------------------------------------------------------------------
# 数据源函数类型（便于注入/ mock）
# ------------------------------------------------------------------

RetrieveKnowledgeFunc = Callable[[list[str]], tuple[str, list[str], dict[str, str]]]
"""RAG 检索函数签名: keywords -> (context_text, sources, source_links)"""

SearchWebFunc = Callable[[str], Awaitable[Optional[Any]]]
"""Web 搜索函数签名: query -> SearchResponse（或 None）"""

RetrieveMemoriesFunc = Callable[[str, str, int, float], list[dict[str, Any]]]
"""记忆检索函数签名: (user_id, input, limit, min_confidence) -> memories"""

GetRecentContextFunc = Callable[..., Awaitable[list[Any]]]
"""消息历史函数签名: (session_id, n) -> messages"""


@dataclass
class ContextAggregatorConfig:
    """聚合器配置"""
    enable_rag: bool = True
    enable_web_search: bool = True
    enable_memory: bool = True
    enable_learning_state: bool = True
    enable_sm2: bool = True
    enable_deadlines: bool = True

    rag_top_k: int = 5
    web_search_top_k: int = 5
    memory_limit: int = 6
    memory_min_confidence: float = 0.5
    context_window: int = 10

    # Web search 触发条件
    web_search_keywords: list[str] = field(default_factory=lambda: [
        "最新", "现在", "新闻", "动态", "最近", "202", "如何", "怎么"
    ])


def _default_rag_retriever(keywords: list[str]) -> tuple[str, list[str], dict[str, str]]:
    """默认 RAG 检索器 —— 调用 main.py 中的 retrieve_knowledge"""
    try:
        # main.py 在全局定义了 retrieve_knowledge
        import main as _main
        if hasattr(_main, "retrieve_knowledge"):
            return _main.retrieve_knowledge(keywords)
    except Exception as e:
        logger.warning(f"[ContextAggregator] RAG 检索失败: {e}")
    return "", [], {}


async def _default_web_search(query: str) -> Optional[Any]:
    """默认 Web 搜索 —— 调用 app.services.teacher.web_search"""
    try:
        from app.services.teacher.web_search import search_web
        return await search_web(query, max_results=5)
    except Exception as e:
        logger.warning(f"[ContextAggregator] Web 搜索失败: {e}")
        return None


def _default_memory_retriever(
    user_id: str, current_input: str, limit: int, min_confidence: float
) -> list[dict[str, Any]]:
    """默认记忆检索器"""
    try:
        from app.services.memory_retriever import retrieve_relevant_memories_sync
        return retrieve_relevant_memories_sync(user_id, current_input, limit, min_confidence)
    except Exception as e:
        logger.warning(f"[ContextAggregator] 记忆检索失败: {e}")
        return []


class ContextAggregator:
    """
    上下文聚合器 —— 并行收集决策所需的全部数据。

    使用示例:
        aggregator = ContextAggregator()
        rich_context = await aggregator.aggregate(event)
    """

    def __init__(
        self,
        config: Optional[ContextAggregatorConfig] = None,
        rag_retriever: Optional[RetrieveKnowledgeFunc] = None,
        web_search: Optional[SearchWebFunc] = None,
        memory_retriever: Optional[RetrieveMemoriesFunc] = None,
        get_recent_context: Optional[GetRecentContextFunc] = None,
    ):
        self.config = config or ContextAggregatorConfig()
        self._rag = rag_retriever or _default_rag_retriever
        self._web = web_search or _default_web_search
        self._memory = memory_retriever or _default_memory_retriever
        self._get_messages = get_recent_context

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    async def aggregate(self, event: TutorEvent) -> RichContext:
        """
        并行聚合所有上下文，返回 RichContext。

        每个数据源的失败都被捕获并记录，不会阻塞其他数据源。
        """
        rich = RichContext(event=event)
        tasks = []

        if self.config.enable_rag:
            tasks.append(self._fetch_rag(event, rich))
        if self.config.enable_web_search:
            tasks.append(self._fetch_web(event, rich))
        if self.config.enable_memory:
            tasks.append(self._fetch_memories(event, rich))
        if self.config.enable_learning_state:
            tasks.append(self._fetch_learning_state(event, rich))
        if self.config.enable_sm2:
            tasks.append(self._fetch_sm2(event, rich))
        if self.config.enable_deadlines:
            tasks.append(self._fetch_deadlines(event, rich))

        # 对话历史（同步/异步兼容）
        tasks.append(self._fetch_conversation_history(event, rich))

        # 并行执行，容错
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"[ContextAggregator] 数据源 #{i} 失败: {result}")

        return rich

    # ------------------------------------------------------------------
    # 各数据源 fetch 方法
    # ------------------------------------------------------------------

    async def _fetch_rag(self, event: TutorEvent, rich: RichContext) -> None:
        """RAG 教材检索"""
        question = event.get_question_text()
        if not question:
            return

        # 从问题提取关键词（简化版：取问题中的名词和术语）
        keywords = self._extract_keywords(question)
        if not keywords:
            keywords = [question[:20]]

        try:
            context_text, sources, source_links = await asyncio.to_thread(
                self._rag, keywords
            )
            rich.rag_context_text = context_text

            # 将 sources 转换为 RAGResult
            for src in sources:
                deep_link = source_links.get(src, "")
                rich.rag_results.append(RAGResult(
                    source_id=src,
                    content=context_text[:500] if context_text else "",
                    source_title=src,
                    deep_link=deep_link,
                    relevance_score=0.8,  # 简化评分
                ))

            logger.info(f"[ContextAggregator] RAG 检索到 {len(sources)} 条教材引用")
        except Exception as e:
            logger.warning(f"[ContextAggregator] RAG 失败: {e}")

    async def _fetch_web(self, event: TutorEvent, rich: RichContext) -> None:
        """Web 搜索 —— 只在必要时触发"""
        question = event.get_question_text()
        if not question:
            return

        # 判断是否需要 Web Search
        if not self._should_web_search(question):
            return

        try:
            resp = await self._web(question)
            if resp and hasattr(resp, "results"):
                rich.web_context_text = getattr(resp, "answer", "")
                for r in resp.results:
                    rich.web_results.append(SearchResult(
                        title=getattr(r, "title", ""),
                        url=getattr(r, "url", ""),
                        content=getattr(r, "content", ""),
                        snippet=getattr(r, "content", "")[:200],
                        score=getattr(r, "score", 0.0),
                        domain=self._extract_domain(getattr(r, "url", "")),
                    ))
                logger.info(f"[ContextAggregator] Web 搜索到 {len(rich.web_results)} 条结果")
        except Exception as e:
            logger.warning(f"[ContextAggregator] Web 搜索失败: {e}")

    async def _fetch_memories(self, event: TutorEvent, rich: RichContext) -> None:
        """长期记忆检索"""
        question = event.get_question_text()
        if not question:
            return

        try:
            mems = await asyncio.to_thread(
                self._memory,
                event.student_id,
                question,
                self.config.memory_limit,
                self.config.memory_min_confidence,
            )
            for m in mems:
                rich.memories.append(Memory(
                    id=m.get("id", ""),
                    content=m.get("content", ""),
                    memory_type=m.get("memory_type", ""),
                    confidence=m.get("confidence", 1.0),
                    access_count=m.get("access_count", 0),
                    confirmed=m.get("confirmed", False),
                ))
            logger.info(f"[ContextAggregator] 记忆检索到 {len(rich.memories)} 条")
        except Exception as e:
            logger.warning(f"[ContextAggregator] 记忆检索失败: {e}")

    async def _fetch_learning_state(self, event: TutorEvent, rich: RichContext) -> None:
        """学习状态 —— 从数据库或本地存储获取"""
        try:
            state = await self._get_learning_state(event.student_id, event.course_id)
            rich.learning_state = state
            logger.info(f"[ContextAggregator] 学习状态: 今日 {state.today_minutes}min, 进度 {state.progress_percent}%")
        except Exception as e:
            logger.warning(f"[ContextAggregator] 学习状态获取失败: {e}")

    async def _fetch_sm2(self, event: TutorEvent, rich: RichContext) -> None:
        """SM2 遗忘曲线复习项"""
        try:
            items = await self._get_sm2_due_items(event.student_id)
            rich.sm2_due_items = items
            logger.info(f"[ContextAggregator] SM2 待复习: {len(items)} 项")
        except Exception as e:
            logger.warning(f"[ContextAggregator] SM2 获取失败: {e}")

    async def _fetch_deadlines(self, event: TutorEvent, rich: RichContext) -> None:
        """课程截止日期"""
        try:
            deadlines = await self._get_upcoming_deadlines(event.student_id, days=7)
            rich.upcoming_deadlines = deadlines
            logger.info(f"[ContextAggregator] 截止日期: {len(deadlines)} 项")
        except Exception as e:
            logger.warning(f"[ContextAggregator] 截止日期获取失败: {e}")

    async def _fetch_conversation_history(self, event: TutorEvent, rich: RichContext) -> None:
        """最近对话历史"""
        if not event.context.session_id or not self._get_messages:
            return

        try:
            msgs = await self._get_messages(event.context.session_id, n=self.config.context_window)
            rich.conversation_history = [
                {"role": getattr(m, "role", "unknown"), "content": getattr(m, "content", "")}
                for m in msgs
            ]
            logger.info(f"[ContextAggregator] 对话历史: {len(rich.conversation_history)} 条")
        except Exception as e:
            logger.warning(f"[ContextAggregator] 对话历史获取失败: {e}")

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_keywords(text: str) -> list[str]:
        """从问题中提取关键词（简化版）"""
        import re
        # 提取中文字符串（2字以上）和英文单词
        chinese = re.findall(r"[一-鿿]{2,}", text)
        english = re.findall(r"[a-zA-Z_]+\w*", text)
        # 去重并限制数量
        seen = set()
        result = []
        for w in chinese + english:
            w_lower = w.lower()
            if w_lower not in seen:
                seen.add(w_lower)
                result.append(w)
        return result[:5]

    def _should_web_search(self, question: str) -> bool:
        """判断是否需要触发 Web Search"""
        q = question.lower()
        # 关键词匹配
        for kw in self.config.web_search_keywords:
            if kw in q:
                return True
        # 内容过短也触发（可能是输入不完整）
        if len(question) < 100:
            return True
        return False

    @staticmethod
    def _extract_domain(url: str) -> str:
        """从 URL 提取域名"""
        from urllib.parse import urlparse
        try:
            return urlparse(url).netloc
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # 数据源接口（可被子类覆盖或使用真实数据库实现）
    # ------------------------------------------------------------------

    async def _get_learning_state(self, student_id: str, course_id: Optional[str]) -> LearningState:
        """
        获取学生学习状态。
        默认从本地存储读取，生产环境应连接真实数据库。
        """
        try:
            from db import load_local_storage
            storage = load_local_storage()
            users = storage.get("users", [])
            user = next((u for u in users if str(u.get("id")) == student_id), {})

            # 计算今日学习时长
            today_minutes = user.get("today_study_minutes", 0)
            streak = user.get("streak_days", 0)
            last_study = user.get("last_study_date", "")

            days_since = 0
            if last_study:
                try:
                    from datetime import date
                    last = datetime.strptime(last_study, "%Y-%m-%d").date()
                    days_since = (date.today() - last).days
                except Exception:
                    pass

            return LearningState(
                current_course_id=course_id or user.get("current_course_id", ""),
                progress_percent=user.get("progress", 0.0),
                today_minutes=today_minutes,
                streak_days=streak,
                days_since_last=days_since,
                is_weekend=datetime.utcnow().weekday() >= 5,
                recent_errors=user.get("recent_errors", []),
                last_study_topic=user.get("last_study_topic", ""),
            )
        except Exception as e:
            logger.warning(f"[ContextAggregator] 默认学习状态获取失败: {e}")
            return LearningState()

    async def _get_sm2_due_items(self, student_id: str) -> list[dict]:
        """获取 SM2 到期复习项，走 KnowledgeRepository。

        Note: returns raw dicts (not ``ReviewItem`` dataclasses) — callers
        in this slice index by string keys; the dict shape matches the
        Repository contract: ``{node_id, subject, topic, interval_days}``.
        """
        try:
            repo = get_repository_for_user(student_id, repository_type="knowledge")
            return repo.get_sm2_due(student_id)
        except Exception as e:
            logger.warning(f"[ContextAggregator] SM2 Repository 获取失败 student_id={student_id}: {e}")
            return []

    async def _get_upcoming_deadlines(self, student_id: str, days: int = 7) -> list[dict]:
        """获取即将到期的任务，走 CourseProgressRepository。

        Note: returns raw dicts (not ``Deadline`` dataclasses) — callers
        in this slice index by string keys; the dict shape matches the
        Repository contract: ``{course_id, title, deadline}``.
        """
        try:
            repo = get_repository_for_user(student_id, repository_type="course_progress")
            return repo.get_upcoming_deadlines(student_id, days=days)
        except Exception as e:
            logger.warning(f"[ContextAggregator] Deadlines Repository 获取失败 student_id={student_id}: {e}")
            return []
