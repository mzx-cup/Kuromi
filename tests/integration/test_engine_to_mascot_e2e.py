"""End-to-end: engine → mascot API → SSE event."""
import pytest
from fastapi.testclient import TestClient


def _parse_sse(body: str) -> list[dict]:
    events = []
    for chunk in body.split("\n\n"):
        if not chunk.strip():
            continue
        evt = {"name": None, "data": None}
        for line in chunk.split("\n"):
            if line.startswith("event: "):
                evt["name"] = line[7:]
            elif line.startswith("data: "):
                import json
                try:
                    evt["data"] = json.loads(line[6:])
                except json.JSONDecodeError:
                    evt["data"] = line[6:]
        events.append(evt)
    return events


def test_e2e_engine_emits_5_proactive_actions(monkeypatch):
    from app.services.tutor_engine.models import (
        ResponseEnvelope, ProactiveAction, ActionType, MessagePriority
    )

    envelope = ResponseEnvelope(
        answer_text="answer with 5 actions",
        proactive_actions=[
            ProactiveAction(action_type=ActionType.REVIEW_REMINDER, priority=MessagePriority.HIGH, action_payload={"subject": "math"}),
            ProactiveAction(action_type=ActionType.PRACTICE_PROMPT, priority=MessagePriority.HIGH, action_payload={"course_id": "c1"}),
            ProactiveAction(action_type=ActionType.STUCK_RECOMMEND_EASIER, priority=MessagePriority.NORMAL, action_payload={"subject": "physics"}),
            ProactiveAction(action_type=ActionType.DEADLINE_URGENT, priority=MessagePriority.HIGH, action_payload={"goal_id": 1}),
            ProactiveAction(action_type=ActionType.HEALTH_REMINDER, priority=MessagePriority.LOW, action_payload={"minutes_studied": 60}),
        ],
    )

    class StubAdapter:
        async def decide(self, user_id, question):
            return envelope

    import app.api.mascot as m
    monkeypatch.setattr(m, "_mascot_adapter", StubAdapter())

    from main import app
    client = TestClient(app)
    with client.stream("POST", "/api/mascot/chat/stream", json={"student_id": "u1", "message": "x"}) as r:
        body = r.read().decode()
    parsed = _parse_sse(body)
    action_count = sum(1 for p in parsed if p["name"] == "proactive_action")
    assert action_count == 5, f"expected 5 proactive_action events, got {action_count}"


def test_e2e_capability_endpoint_uses_aggregator(monkeypatch):
    from app.services.tutor_engine.capability_aggregator import (
        CapabilityAggregator, CapabilityProfile, CognitiveStyle, FocusLevel
    )

    async def stub(self, user_id):
        return CapabilityProfile(
            user_id=user_id,
            knowledge_base={"math": 0.5},
            cognitive_style=CognitiveStyle(preferred_modality="visual", depth="deep"),
            focus_level=FocusLevel(avg_session_minutes=30, streak_days=3),
        )

    monkeypatch.setattr(CapabilityAggregator, "for_user", stub)
    from main import app
    client = TestClient(app)
    resp = client.get("/api/mascot/capability/u1")
    assert resp.status_code == 200
    body = resp.json()
    assert body["knowledge_base"]["math"] == 0.5
    assert body["focus_level"]["streak_days"] == 3
    assert body["user_id"] == "u1"
