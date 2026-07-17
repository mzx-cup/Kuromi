# -*- coding: utf-8 -*-
"""Tests for engine.decide() trace context integration.

NOTE: This test file was adapted from the Slice 2.1.4 template to match the
*actual* TutorDecisionEngine / models API in this repo:

  - ``TutorEvent`` uses ``type`` + ``student_id`` (not ``event_type`` / ``user_id``)
  - ``TutorEventType.QUESTION_ASKED`` triggers the LLM/guard path
  - ``ConfidenceReport`` exposes ``final_confidence`` + ``blocked`` (no ``risk_score``)
  - ``RichContext`` carries ``rag_results`` / ``web_results`` / ``memories``
  - Sub-modules are lazy-imported inside ``decide()`` helpers and stored on the
    instance (``engine.aggregator`` / ``engine._hallucination_guard`` /
    ``engine._link_recommender`` / ``engine._proactive_advisor``), so they are
    injected via instance attributes rather than module-level monkeypatch.
  - ``decide()`` preserves a "never raise" degradation contract — on a guard
    block or genuine error it returns a degraded envelope. The trace span still
    records ``status=error`` in that case, which is what the error test asserts.

Verifies that:
  - start_span creates a span logged with name=tutor.decide
  - Sub-module results are recorded as span attributes
  - On guard block, span.status=error and error.* attributes are set
"""
import asyncio
import logging

import pytest

from app.services.tutor_engine.engine import TutorDecisionEngine
from app.services.tutor_engine.models import (
    ActionType,
    ConfidenceReport,
    Link,
    Memory,
    MessagePriority,
    ProactiveAction,
    RAGResult,
    RichContext,
    SearchResult,
    TutorEvent,
    TutorEventType,
)


def _make_rich(event):
    """RichContext with 2 rag + 2 web + 1 memory => context_count == 5."""
    rich = RichContext(event=event)
    rich.rag_results = [
        RAGResult(source_id="c1", content="x", source_title="C1"),
        RAGResult(source_id="c2", content="y", source_title="C2"),
    ]
    rich.web_results = [
        SearchResult(title="w1", url="http://a"),
        SearchResult(title="w2", url="http://b"),
    ]
    rich.memories = [Memory(id="m1", content="mem")]
    return rich


class _FakeAggregator:
    async def aggregate(self, event):
        return _make_rich(event)


class _FakeGuard:
    def __init__(self, confidence):
        self._confidence = confidence

    async def process(self, event, rich):
        # (answer_stream, answer_text, citations, confidence_report)
        return None, "fake LLM response", [], self._confidence


class _FakeRecommender:
    async def recommend(self, event, rich, ledger):
        return [
            Link(type="internal", title="link1", url="http://l1"),
            Link(type="external", title="link2", url="http://l2"),
        ]


class _FakeAdvisor:
    async def advise(self, event, rich, envelope, ledger):
        return [
            ProactiveAction(
                action_type=ActionType.DAILY_GREETING,
                priority=MessagePriority.NORMAL,
            )
        ]


def _build_engine(confidence):
    engine = TutorDecisionEngine()
    engine.aggregator = _FakeAggregator()
    engine._hallucination_guard = _FakeGuard(confidence)
    engine._link_recommender = _FakeRecommender()
    engine._proactive_advisor = _FakeAdvisor()
    return engine


class TestEngineTraceAttributes:
    def test_engine_emits_span_with_attributes(self, caplog):
        """engine.decide() should record span attributes via contextvar."""
        engine = _build_engine(ConfidenceReport(final_confidence=0.15, blocked=False))
        event = TutorEvent(type=TutorEventType.QUESTION_ASKED, student_id="42")

        with caplog.at_level(logging.INFO, logger="starlearn.trace"):
            envelope = asyncio.run(engine.decide(event))

        assert envelope is not None
        assert any("span_end" in r.message for r in caplog.records)

        span_record = next(r for r in caplog.records if "span_end" in r.message)
        msg = span_record.message
        assert "name=tutor.decide" in msg
        assert "user_id=42" in msg
        assert "context_count=5" in msg
        assert "0.15" in msg
        assert "links_count=2" in msg
        assert "actions_count=1" in msg
        assert "status=ok" in msg

    def test_engine_records_error_status_on_guard_block(self, caplog):
        """When HallucinationGuard blocks, span.status=error + error.* attrs set.

        decide() preserves its degradation contract (returns an envelope rather
        than raising), so we assert via the emitted trace log line.
        """
        engine = _build_engine(ConfidenceReport(final_confidence=0.95, blocked=True))
        event = TutorEvent(type=TutorEventType.QUESTION_ASKED, student_id="42")

        with caplog.at_level(logging.INFO, logger="starlearn.trace"):
            envelope = asyncio.run(engine.decide(event))

        assert any("status=error" in r.message for r in caplog.records)
        span_record = next(r for r in caplog.records if "span_end" in r.message)
        assert "error.type=HallucinationBlocked" in span_record.message
        assert envelope.confidence_report.blocked is True
