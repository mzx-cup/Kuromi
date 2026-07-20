"""SSE contract tests for /api/mascot/chat/stream — proactive_action event format."""
import json
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client_with_proactive(monkeypatch):
    from app.services.tutor_engine.models import (
        ResponseEnvelope, ProactiveAction, ActionType, MessagePriority
    )

    class StubAdapter:
        async def decide(self, user_id, question):
            return ResponseEnvelope(
                answer_text="streaming answer",
                proactive_actions=[
                    ProactiveAction(
                        action_type=ActionType.REVIEW_REMINDER,
                        priority=MessagePriority.HIGH,
                        action_payload={"subject": "math", "topic": "algebra"},
                    ),
                    ProactiveAction(
                        action_type=ActionType.HEALTH_REMINDER,
                        priority=MessagePriority.NORMAL,
                        action_payload={"minutes_studied": 45},
                    ),
                ],
            )

    import app.api.mascot as m
    monkeypatch.setattr(m, "_mascot_adapter", StubAdapter())
    from main import app
    return TestClient(app)


def _parse_sse(body: str) -> list[dict]:
    """Parse SSE body into list of {name, data} dicts."""
    events = []
    for chunk in body.split("\n\n"):
        if not chunk.strip():
            continue
        evt = {"name": None, "data": None}
        for line in chunk.split("\n"):
            if line.startswith("event: "):
                evt["name"] = line[7:]
            elif line.startswith("data: "):
                try:
                    evt["data"] = json.loads(line[6:])
                except json.JSONDecodeError:
                    evt["data"] = line[6:]
        events.append(evt)
    return events


def test_sse_response_event_format(client_with_proactive):
    with client_with_proactive.stream("POST", "/api/mascot/chat/stream", json={
        "student_id": "u1", "message": "test",
    }) as resp:
        body = resp.read().decode()
    parsed = _parse_sse(body)
    names = [p["name"] for p in parsed]
    assert "text_delta" in names, f"missing text_delta event; got {names}"
    assert "done" in names, f"missing done event; got {names}"
    assert names.count("proactive_action") == 2, f"expected 2 proactive_action events; got {names}"


def test_sse_proactive_action_payload_schema(client_with_proactive):
    with client_with_proactive.stream("POST", "/api/mascot/chat/stream", json={
        "student_id": "u1", "message": "test",
    }) as resp:
        body = resp.read().decode()
    parsed = _parse_sse(body)
    action_events = [p for p in parsed if p["name"] == "proactive_action"]
    assert len(action_events) == 2
    for evt in action_events:
        data = evt["data"]
        assert "type" in data
        assert "priority" in data
        assert "payload" in data
        # priority must be an int (MessagePriority.value)
        assert isinstance(data["priority"], int)
        # type must be a string (ActionType.value)
        assert isinstance(data["type"], str)


def test_sse_proactive_action_types_match_model(client_with_proactive):
    """The emitted type values must match ActionType enum strings."""
    with client_with_proactive.stream("POST", "/api/mascot/chat/stream", json={
        "student_id": "u1", "message": "test",
    }) as resp:
        body = resp.read().decode()
    parsed = _parse_sse(body)
    action_events = [p for p in parsed if p["name"] == "proactive_action"]
    types = {evt["data"]["type"] for evt in action_events}
    assert "review_reminder" in types
    assert "health_reminder" in types
