# -*- coding: utf-8 -*-
"""
TutorDecisionEngine — 统一智能导师决策引擎主入口

职责：
  1. 接收 TutorEvent（学生交互事件）
  2. 调用 ContextAggregator 并行聚合上下文
  3. 调用 LLM 生成回答
  4. 调用 HallucinationGuard 校验回答（防幻觉）
  5. 调用 LinkRecommender 生成学习链接
  6. 调用 ProactiveAdvisor 决策主动推送
  7. 组装 ResponseEnvelope 返回

使用示例:
    engine = TutorDecisionEngine()
    envelope = await engine.decide(event)
    # envelope.answer_stream -> SSE 推送给前端
    # envelope.links -> 学习链接
    # envelope.proactive_actions -> 主动推送队列
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncIterator, Optional

from app.services.tutor_engine.action_ledger import ActionLedger
from app.services.tutor_engine.context_aggregator import ContextAggregator
from app.services.tutor_engine.models import (
    ConfidenceReport,
    EventContext,
    Link,
    ResponseEnvelope,
    RichContext,
    TutorEvent,
    TutorEventType,
)

logger = logging.getLogger("starlearn.tutor_engine")


class TutorDecisionEngine:
    """
    统一决策引擎。

    所有学生交互的中央处理管道。不直接处理 HTTP/SSE，
    只负责决策逻辑；调用方（main.py 端点）负责 SSE 推送。
    """

    def __init__(
        self,
        context_aggregator: Optional[ContextAggregator] = None,
        action_ledger: Optional[ActionLedger] = None,
    ):
        self.aggregator = context_aggregator or ContextAggregator()
        self.ledger = action_ledger or ActionLedger()

        # 各子引擎（懒加载/可注入）
        self._hallucination_guard: Optional[Any] = None
        self._link_recommender: Optional[Any] = None
        self._proactive_advisor: Optional[Any] = None
        self._response_composer: Optional[Any] = None

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    async def decide(self, event: TutorEvent) -> ResponseEnvelope:
        """
        核心决策方法。

        返回 ResponseEnvelope，包含 answer_stream、links、
        proactive_actions、confidence_report。
        """
        trace: list[str] = [f"🚀 TutorDecisionEngine 开始处理: {event.type.value}"]
        envelope = ResponseEnvelope(engine_trace=trace)

        try:
            # === Step 1: 聚合上下文 ===
            trace.append("📚 ContextAggregator 并行聚合...")
            rich_context = await self.aggregator.aggregate(event)
            trace.append(f"   RAG: {len(rich_context.rag_results)} 条, "
                        f"Web: {len(rich_context.web_results)} 条, "
                        f"Memories: {len(rich_context.memories)} 条")

            # === Step 2: 生成回答 + 校验 ===
            trace.append("🧠 生成回答并校验...")
            answer_stream, answer_text, citations, confidence = await self._generate_and_guard(
                event, rich_context
            )
            envelope.answer_stream = answer_stream
            envelope.answer_text = answer_text
            envelope.citations = citations
            envelope.confidence_report = confidence
            trace.append(f"   置信度: {confidence.final_confidence:.2f}, "
                        f"引用: {len(citations)} 条, "
                        f"blocked: {confidence.blocked}")

            # === Step 3: 生成学习链接 ===
            trace.append("🔗 生成学习链接...")
            links = await self._generate_links(event, rich_context)
            envelope.links = links
            trace.append(f"   链接: {len(links)} 条")

            # 记录链接暴露（用于后续去重）
            for link in links:
                topic = link.metadata.get("topic", link.title)
                self.ledger.record_exposure(event.student_id, topic, "link_click")

            # === Step 4: 决策主动推送 ===
            trace.append("📢 决策主动推送...")
            actions = await self._advise_proactive(event, rich_context, envelope)
            envelope.proactive_actions = actions
            trace.append(f"   推送: {len(actions)} 条")

            # 记录推送暴露
            for action in actions:
                topic = action.metadata.get("topic", action.action_type.value)
                self.ledger.record_exposure(
                    event.student_id, topic, action.action_type.value
                )

            trace.append("✅ 决策完成")

        except Exception as e:
            logger.exception(f"[TutorDecisionEngine] 决策失败: {e}")
            trace.append(f"❌ 错误: {e}")
            # 返回降级响应：空 envelope，让调用方回退到旧逻辑
            envelope.answer_text = "[系统处理中，请稍后再试]"

        return envelope

    # ------------------------------------------------------------------
    # 子步骤封装
    # ------------------------------------------------------------------

    async def _generate_and_guard(
        self,
        event: TutorEvent,
        rich: RichContext,
    ) -> tuple[Optional[AsyncIterator[str]], str, list[Any], ConfidenceReport]:
        """
        生成 LLM 回答并经过 HallucinationGuard 校验。

        返回: (answer_stream, answer_text, citations, confidence_report)
        """
        # 非 QUESTION_ASKED 事件不需要 LLM 回答
        if event.type != TutorEventType.QUESTION_ASKED:
            return None, "", [], ConfidenceReport()

        # 懒加载 HallucinationGuard
        if self._hallucination_guard is None:
            from app.services.tutor_engine.hallucination_guard import HallucinationGuard
            self._hallucination_guard = HallucinationGuard()

        guard = self._hallucination_guard
        return await guard.process(event, rich)

    async def _generate_links(
        self,
        event: TutorEvent,
        rich: RichContext,
    ) -> list[Link]:
        """生成学习链接"""
        if self._link_recommender is None:
            from app.services.tutor_engine.link_recommender import LinkRecommender
            self._link_recommender = LinkRecommender()

        recommender = self._link_recommender
        return await recommender.recommend(event, rich, self.ledger)

    async def _advise_proactive(
        self,
        event: TutorEvent,
        rich: RichContext,
        envelope: ResponseEnvelope,
    ) -> list[Any]:
        """决策主动推送"""
        if self._proactive_advisor is None:
            from app.services.tutor_engine.proactive_advisor import ProactiveAdvisor
            self._proactive_advisor = ProactiveAdvisor()

        advisor = self._proactive_advisor
        return await advisor.advise(event, rich, envelope, self.ledger)

    # ------------------------------------------------------------------
    # 便捷方法（供调用方直接使用）
    # ------------------------------------------------------------------

    async def answer_question(
        self,
        student_id: str,
        question: str,
        course_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> ResponseEnvelope:
        """便捷方法：直接回答学生提问"""
        event = TutorEvent(
            type=TutorEventType.QUESTION_ASKED,
            student_id=student_id,
            course_id=course_id,
            payload={"question": question},
            context=EventContext(session_id=session_id or ""),
        )
        return await self.decide(event)

    async def on_struggle(
        self,
        student_id: str,
        struggle_metrics: dict[str, Any],
        course_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> ResponseEnvelope:
        """便捷方法：学生遇到困难"""
        event = TutorEvent(
            type=TutorEventType.STRUGGLE_DETECTED,
            student_id=student_id,
            course_id=course_id,
            payload={"struggle_metrics": struggle_metrics},
            context=EventContext(session_id=session_id or ""),
        )
        return await self.decide(event)

    async def on_login(
        self,
        student_id: str,
        course_id: Optional[str] = None,
    ) -> ResponseEnvelope:
        """便捷方法：学生登录问候"""
        event = TutorEvent(
            type=TutorEventType.LOGIN_GREETING,
            student_id=student_id,
            course_id=course_id,
            payload={},
            context=EventContext(),
        )
        return await self.decide(event)
