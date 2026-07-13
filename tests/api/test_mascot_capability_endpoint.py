"""Contract tests for GET /api/mascot/capability/{user_id}."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    from app.services.tutor_engine.capability_aggregator import CapabilityProfile, CognitiveStyle, FocusLevel, LearningGoal, Weakness
    from app.services.tutor_engine.capability_aggregator import CapabilityAggregator

    async def stub_for_user(self, user_id):
        return CapabilityProfile(
            user_id=user_id,
            knowledge_base={"math": 0.72, "physics": 0.45},
            code_skill={"python": 0.55},
            cognitive_style=CognitiveStyle(preferred_modality="visual", depth="deep"),
            focus_level=FocusLevel(avg_session_minutes=35, streak_days=7),
            learning_goals=[LearningGoal(id=1, title="高考数学", progress=0.42)],
            weakness=[Weakness(subject="physics", topic="mechanics", mastery=0.30)],
        )

    monkeypatch.setattr(
        "app.services.tutor_engine.capability_aggregator.CapabilityAggregator.for_user",
        stub_for_user,
    )

    from main import app
    return TestClient(app)


def test_capability_endpoint_returns_200(client):
    resp = client.get("/api/mascot/capability/u_test")
    assert resp.status_code == 200


def test_capability_response_has_all_6_dims(client):
    resp = client.get("/api/mascot/capability/u_test")
    body = resp.json()
    for dim in ("knowledge_base", "code_skill", "cognitive_style", "focus_level", "learning_goals", "weakness"):
        assert dim in body, f"Missing dim: {dim}"


def test_capability_response_includes_user_id(client):
    resp = client.get("/api/mascot/capability/u_test")
    assert resp.json()["user_id"] == "u_test"


def test_capability_endpoint_does_not_500(client):
    """Without auth, must return 200 (not 500)."""
    resp = client.get("/api/mascot/capability/u_test")
    assert resp.status_code in (200, 401)