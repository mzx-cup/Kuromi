"""Verify /api/mascot/chat/stream uses MascotEngineAdapter and emits proactive_action events."""
import json
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    """Provide TestClient with a stubbed engine to avoid real LLM calls."""
    from app.services.tutor_engine.models import (
        ResponseEnvelope, ProactiveAction, ActionType, MessagePriority
    )

    class StubAdapter:
        async def decide(self, user_id, question):
            return ResponseEnvelope(
                answer_text=f"stub answer for: {question}",
                proactive_actions=[
                    ProactiveAction(
                        action_type=ActionType.REVIEW_REMINDER,
                        priority=MessagePriority.HIGH,
                        action_payload={"subject": "math", "topic": "algebra"},
                    )
                ],
            )

    import app.api.mascot as mascot_module
    monkeypatch.setattr(mascot_module, "_mascot_adapter", StubAdapter())

    from main import app
    return TestClient(app)


def test_mascot_chat_stream_emits_proactive_action_event(client):
    """The SSE response must include the new 'proactive_action' event."""
    with client.stream("POST", "/api/mascot/chat/stream", json={
        "student_id": "u1",
        "message": "test",
    }) as response:
        body = response.read().decode()
        events = body.split("\n\n")
    has_proactive = any('event: proactive_action' in e for e in events)
    assert has_proactive, "SSE response missing 'proactive_action' event"


def test_mascot_chat_stream_preserves_text_delta_event(client):
    """Backward-compat: the existing 'text_delta' event must still be present."""
    with client.stream("POST", "/api/mascot/chat/stream", json={
        "student_id": "u1",
        "message": "test",
    }) as response:
        body = response.read().decode()
        events = body.split("\n\n")
    has_delta = any('"text_delta"' in e or 'event: text_delta' in e for e in events)
    assert has_delta, "SSE response missing 'text_delta' event (backward compat broken)"


def test_mascot_chat_stream_proactive_action_payload_schema(client):
    """proactive_action event data must have type/priority/payload keys."""
    with client.stream("POST", "/api/mascot/chat/stream", json={
        "student_id": "u1",
        "message": "test",
    }) as response:
        body = response.read().decode()
    events = body.split("\n\n")
    action_events = [e for e in events if "proactive_action" in e]
    assert len(action_events) >= 1
    for e in action_events:
        for line in e.split("\n"):
            if line.startswith("data: "):
                payload = json.loads(line[6:])
                assert "type" in payload
                assert "priority" in payload
                assert "payload" in payload
                assert payload["type"] == "review_reminder"  # ActionType.REVIEW_REMINDER.value
                assert payload["priority"] == 1  # MessagePriority.HIGH.value