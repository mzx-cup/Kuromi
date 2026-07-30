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
import os
from typing import Any, AsyncIterator, Optional

from app.core.trace import finish_span, start_span
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

# M3.2: 接入正式 JailbreakDetector（M2 阶段为内联正则，已替换）
from app.services.safety.jailbreak_detector import JailbreakDetector

_JAILBREAK_BLOCK_THRESHOLD = 0.7


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
        jailbreak_detector: Optional[JailbreakDetector] = None,
    ):
        self.aggregator = context_aggregator or ContextAggregator()
        self.ledger = action_ledger or ActionLedger()
        # M3.2: 越狱检测器（默认 L0 正则）
        self._jailbreak_detector = jailbreak_detector or JailbreakDetector(level="L0")

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

        # Trace span for observability. The span records per-phase attributes
        # (counts, timing, status) on the current root span via contextvar.
        span, token = start_span("tutor.decide")
        span.set_attribute("user_id", str(event.student_id))
        span.set_attribute("event_type", event.type.value)

        try:
            # === Step 1: 聚合上下文 ===
            trace.append("📚 ContextAggregator 并行聚合...")
            rich_context = await self.aggregator.aggregate(event)
            trace.append(f"   RAG: {len(rich_context.rag_results)} 条, "
                        f"Web: {len(rich_context.web_results)} 条, "
                        f"Memories: {len(rich_context.memories)} 条")
            context_count = (
                len(getattr(rich_context, "rag_results", []))
                + len(getattr(rich_context, "web_results", []))
                + len(getattr(rich_context, "memories", []))
            )
            span.set_attribute("context_count", context_count)

            # === Step 2: 生成回答 + 校验 ===
            trace.append("🧠 生成回答并校验...")
            import time
            llm_start = time.perf_counter()
            answer_stream, answer_text, citations, confidence = await self._generate_and_guard(
                event, rich_context
            )
            span.set_attribute("llm_latency_ms", (time.perf_counter() - llm_start) * 1000)
            envelope.answer_stream = answer_stream
            envelope.answer_text = answer_text
            envelope.citations = citations
            envelope.confidence_report = confidence
            trace.append(f"   置信度: {confidence.final_confidence:.2f}, "
                        f"引用: {len(citations)} 条, "
                        f"blocked: {confidence.blocked}")
            span.set_attribute("guard_final_confidence", confidence.final_confidence)
            if getattr(confidence, "blocked", False):
                span.set_status("error")
                span.set_attribute("error.type", "HallucinationBlocked")
                span.set_attribute(
                    "error.message",
                    f"guard blocked: confidence={confidence.final_confidence}"[:200],
                )

            # === Step 3: 生成学习链接 ===
            trace.append("🔗 生成学习链接...")
            links = await self._generate_links(event, rich_context)
            envelope.links = links
            trace.append(f"   链接: {len(links)} 条")
            span.set_attribute("links_count", len(links))

            # 记录链接暴露（用于后续去重）
            for link in links:
                topic = link.metadata.get("topic", link.title)
                self.ledger.record_exposure(event.student_id, topic, "link_click")

            # === Step 4: 决策主动推送 ===
            trace.append("📢 决策主动推送...")
            actions = await self._advise_proactive(event, rich_context, envelope)
            envelope.proactive_actions = actions
            trace.append(f"   推送: {len(actions)} 条")
            span.set_attribute("actions_count", len(actions))

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
            span.set_status("error")
            span.set_attribute("error.type", type(e).__name__)
            span.set_attribute("error.message", str(e)[:200])
            # 返回降级响应：空 envelope，让调用方回退到旧逻辑
            envelope.answer_text = "[系统处理中，请稍后再试]"
        finally:
            finish_span(span, token)

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

    # ------------------------------------------------------------------
    # M2.5: 模式路由 + 越狱拦截（接入 /api/v2/chat）
    # ------------------------------------------------------------------

    @staticmethod
    def _decision_engine_enabled() -> bool:
        return os.environ.get("ENABLE_DECISION_ENGINE", "false").lower() == "true"

    async def route(self, user_id: str, message: str, mode: str) -> dict:
        """根据用户输入 + 模式，决定走哪个 Agent（M2.5）。

        返回: {"agent": <agent_name>, "next_step": <step>}

        当 ENABLE_DECISION_ENGINE != "true" 时，回退到 legacy_socratic
        （保持对调用方的向后兼容）。
        """
        if not self._decision_engine_enabled():
            return {"agent": "legacy_socratic", "next_step": "ask_question"}

        mode_map = {
            "socratic": ("qa_agent", "ask_question"),
            "qa": ("qa_agent", "ask_question"),
            "recommend": ("recommend_agent", "generate_recommendation"),
            "audit": ("audit_agent", "check_output"),
            "evaluate": ("evaluate_agent", "evaluate_answer"),
        }
        agent, next_step = mode_map.get(mode, ("qa_agent", "ask_question"))
        return {"agent": agent, "next_step": next_step}

    async def process_chat_request(
        self,
        user_id: str,
        message: str,
        mode: str,
    ) -> dict:
        """主入口（M2.5）：先越狱检测 → 再路由到对应 Agent。

        返回:
          - blocked=False 时: {"blocked": False, "agent": ..., "next_step": ...}
          - blocked=True 时:  {"blocked": True, "reason": "jailbreak_detected", "pattern": ...}
        """
        # L0 越狱检测（接入正式 JailbreakDetector）
        jb_result = await self._jailbreak_detector.scan(message)
        if jb_result.risk_score >= _JAILBREAK_BLOCK_THRESHOLD:
            logger.warning(
                f"[TutorDecisionEngine] jailbreak blocked user={user_id} "
                f"pattern={jb_result.pattern} matched={jb_result.matched_text!r}"
            )
            return {
                "blocked": True,
                "reason": "jailbreak_detected",
                "pattern": jb_result.pattern,
                "agent": None,
                "next_step": None,
            }

        decision = await self.route(user_id=user_id, message=message, mode=mode)
        return {
            "blocked": False,
            "reason": None,
            "agent": decision["agent"],
            "next_step": decision["next_step"],
        }

    @staticmethod
    def _scan_jailbreak(text: str) -> tuple[float, str, str]:
        """兼容旧 API 的薄包装（不推荐使用）。"""
        import warnings

        warnings.warn(
            "TutorDecisionEngine._scan_jailbreak is deprecated; "
            "use self._jailbreak_detector.scan(text) instead",
            DeprecationWarning,
            stacklevel=2,
        )
        import asyncio

        async def _go():
            detector = JailbreakDetector(level="L0")
            result = await detector.scan(text)
            return result.risk_score, result.pattern, result.matched_text

        return asyncio.get_event_loop().run_until_complete(_go())
