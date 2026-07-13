"""MascotEngineAdapter — bridge between mascot.py and TutorDecisionEngine.

Wraps TutorDecisionEngine.decide() with:
  - Timeout handling (default 30s)
  - Fallback to a simple chat path if engine fails
  - Translation of mascot request shape (user_id, question) to TutorEvent
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

from app.services.tutor_engine.engine import TutorDecisionEngine
from app.services.tutor_engine.models import (
    EventContext,
    ResponseEnvelope,
    TutorEvent,
    TutorEventType,
)

logger = logging.getLogger("starlearn.tutor.mascot_adapter")


class MascotEngineAdapter:
    def __init__(
        self,
        engine: Optional[TutorDecisionEngine] = None,
        timeout_seconds: float = 30.0,
        fallback_text: Optional[str] = None,
    ):
        self._engine = engine
        self.timeout_seconds = timeout_seconds
        # If env var MASCOT_FALLBACK_NO_LLM=1 is set, or fallback_text is provided,
        # we skip the LLM call in fallback_simple_chat to keep tests fast.
        self._fallback_text = fallback_text

    @property
    def engine(self) -> TutorDecisionEngine:
        if self._engine is None:
            self._engine = TutorDecisionEngine()
        return self._engine

    def _build_event(self, user_id: str, question: str) -> TutorEvent:
        return TutorEvent(
            type=TutorEventType.QUESTION_ASKED,
            student_id=str(user_id),
            context=EventContext(),
            payload={"question": question},
        )

    async def decide(self, user_id: str, question: str) -> ResponseEnvelope:
        event = self._build_event(user_id, question)
        try:
            envelope = await asyncio.wait_for(
                self.engine.decide(event),
                timeout=self.timeout_seconds,
            )
            return envelope
        except asyncio.TimeoutError:
            logger.warning(f"[MascotEngineAdapter] engine.decide timeout for user={user_id}")
            return await self.fallback_simple_chat(user_id, question)
        except Exception as e:
            logger.warning(f"[MascotEngineAdapter] engine.decide error for user={user_id}: {e}")
            return await self.fallback_simple_chat(user_id, question)

    def _should_skip_llm(self) -> bool:
        """Skip LLM call if explicitly configured (env var or constructor arg)."""
        if self._fallback_text is not None:
            return True
        return os.environ.get("MASCOT_FALLBACK_NO_LLM") == "1"

    async def fallback_simple_chat(self, user_id: str, question: str) -> ResponseEnvelope:
        """Last-resort chat path: direct LLM call without engine context.

        If MASCOT_FALLBACK_NO_LLM=1 is set in the environment, or fallback_text
        was provided to the constructor, skip the LLM call and return a canned
        response. This keeps tests fast and predictable.
        """
        if self._should_skip_llm():
            canned = self._fallback_text or "抱歉，AI 助手暂时不可用，请稍后再试。"
            return ResponseEnvelope(answer_text=canned)

        # Real LLM fallback path
        from llm_stream import call_llm_stream_with_log_messages
        try:
            text_parts: list[str] = []
            async for chunk in call_llm_stream_with_log_messages(
                messages=[{"role": "user", "content": question}],
            ):
                # The LLM stream yields dict events. Pull the final full_text
                # from the "done" event, otherwise accumulate content chunks.
                if isinstance(chunk, dict):
                    if chunk.get("type") == "done":
                        full_text = chunk.get("full_text")
                        if isinstance(full_text, str) and full_text:
                            return ResponseEnvelope(answer_text=full_text)
                    elif chunk.get("type") == "content_chunk":
                        content = chunk.get("content")
                        if isinstance(content, str):
                            text_parts.append(content)
                elif isinstance(chunk, str):
                    text_parts.append(chunk)

            return ResponseEnvelope(answer_text="".join(text_parts))
        except Exception as e:
            logger.error(f"[MascotEngineAdapter] fallback LLM failed: {e}")
            return ResponseEnvelope(answer_text=f"抱歉，AI 助手暂时不可用: {str(e)[:100]}")