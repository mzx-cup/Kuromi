"""Tests for MascotEngineAdapter: bridge between mascot.py and TutorDecisionEngine."""
import pytest
from app.services.tutor_engine.mascot_adapter import MascotEngineAdapter


class TestMascotEngineAdapter:
    @pytest.mark.asyncio
    async def test_decide_returns_envelope(self):
        from app.services.tutor_engine.models import ResponseEnvelope

        class StubEngine:
            async def decide(self, event):
                return ResponseEnvelope(answer_text="stub answer")

        adapter = MascotEngineAdapter(engine=StubEngine())
        envelope = await adapter.decide("u1", "test question")
        assert envelope.answer_text == "stub answer"

    @pytest.mark.asyncio
    async def test_decide_handles_timeout(self, monkeypatch):
        """If engine.decide() times out, fallback_simple_chat is invoked."""
        import asyncio
        from app.services.tutor_engine.models import ResponseEnvelope

        class StubEngine:
            async def decide(self, event):
                await asyncio.sleep(100)  # would timeout

        adapter = MascotEngineAdapter(
            engine=StubEngine(),
            timeout_seconds=0.1,
            fallback_text="cached fallback reply",
        )
        fallback_called = {"n": 0}
        original_fallback = adapter.fallback_simple_chat

        async def spy(user_id, question):
            fallback_called["n"] += 1
            return await original_fallback(user_id, question)

        monkeypatch.setattr(adapter, "fallback_simple_chat", spy)
        envelope = await adapter.decide("u1", "test")
        assert envelope is not None
        assert envelope.answer_text == "cached fallback reply"
        assert fallback_called["n"] == 1, "fallback_simple_chat must be invoked exactly once on timeout"

    @pytest.mark.asyncio
    async def test_decide_fallback_on_engine_error(self, monkeypatch):
        from app.services.tutor_engine.models import ResponseEnvelope

        class StubEngine:
            async def decide(self, event):
                raise RuntimeError("engine boom")

        adapter = MascotEngineAdapter(
            engine=StubEngine(),
            fallback_text="error fallback reply",
        )
        fallback_called = {"n": 0}
        original_fallback = adapter.fallback_simple_chat

        async def spy(user_id, question):
            fallback_called["n"] += 1
            return await original_fallback(user_id, question)

        monkeypatch.setattr(adapter, "fallback_simple_chat", spy)
        envelope = await adapter.decide("u1", "test")
        assert envelope is not None
        assert envelope.answer_text == "error fallback reply"
        assert fallback_called["n"] == 1, "fallback_simple_chat must be invoked exactly once on engine error"
