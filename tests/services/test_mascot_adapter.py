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
    async def test_decide_handles_timeout(self):
        """If engine.decide() times out, fallback_simple_chat is invoked."""
        import asyncio
        from app.services.tutor_engine.models import ResponseEnvelope

        class StubEngine:
            async def decide(self, event):
                await asyncio.sleep(100)  # would timeout

        # Pass a canned fallback text to avoid hitting real LLM in test
        adapter = MascotEngineAdapter(
            engine=StubEngine(),
            timeout_seconds=0.1,
            fallback_text="cached fallback reply",
        )
        # The fallback must return a valid envelope
        envelope = await adapter.decide("u1", "test")
        assert envelope is not None
        assert envelope.answer_text  # non-empty fallback text
        assert envelope.answer_text == "cached fallback reply"

    @pytest.mark.asyncio
    async def test_decide_fallback_on_engine_error(self):
        from app.services.tutor_engine.models import ResponseEnvelope

        class StubEngine:
            async def decide(self, event):
                raise RuntimeError("engine boom")

        adapter = MascotEngineAdapter(
            engine=StubEngine(),
            fallback_text="error fallback reply",
        )
        envelope = await adapter.decide("u1", "test")
        assert envelope is not None
        assert envelope.answer_text  # non-empty
        assert envelope.answer_text == "error fallback reply"