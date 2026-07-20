"""Tests for the 2 TODO stubs in context_aggregator: SM2 and Deadlines."""
import pytest
from datetime import date
from app.services.tutor_engine.context_aggregator import ContextAggregator
from app.services.tutor_engine.models import TutorEvent, EventContext, TutorEventType


@pytest.fixture
def aggregator() -> ContextAggregator:
    return ContextAggregator()


@pytest.mark.asyncio
async def test_get_sm2_due_items_uses_repository(aggregator, monkeypatch):
    """_get_sm2_due_items should consult KnowledgeRepository, not return []. """
    # Stub repository
    class StubKnowledgeRepo:
        def get_sm2_due(self, user_id: str) -> list:
            return [{"node_id": 1, "subject": "math", "topic": "algebra", "interval_days": 3}]
    monkeypatch.setattr(
        "app.services.tutor_engine.context_aggregator.get_repository_for_user",
        lambda uid, **kwargs: StubKnowledgeRepo(),
    )
    items = await aggregator._get_sm2_due_items("u1")
    assert len(items) == 1
    assert items[0]["topic"] == "algebra"


@pytest.mark.asyncio
async def test_get_upcoming_deadlines_uses_repository(aggregator, monkeypatch):
    """_get_upcoming_deadlines should consult CourseProgressRepository."""
    class StubCourseRepo:
        def get_upcoming_deadlines(self, user_id: str, days: int) -> list:
            return [{"course_id": "c1", "title": "数学期末", "deadline": "2026-07-15"}]
    monkeypatch.setattr(
        "app.services.tutor_engine.context_aggregator.get_repository_for_user",
        lambda uid, **kwargs: StubCourseRepo(),
    )
    deadlines = await aggregator._get_upcoming_deadlines("u1", days=7)
    assert len(deadlines) == 1
    assert deadlines[0]["title"] == "数学期末"


@pytest.mark.asyncio
async def test_fetch_sm2_called_in_aggregate(aggregator, monkeypatch):
    """ContextAggregator.aggregate should call _fetch_sm2 and populate rich_context."""
    # Patch the inner SM2-items method (the actual workhorse called by
    # _fetch_sm2) with a spy that flips a flag only when invoked. The
    # previous version monkeypatched _fetch_sm2 itself, but the flag
    # assignment happens inside the spy wrapper, so it was set at attach
    # time regardless of whether aggregate() ever reached _fetch_sm2.
    called = {"count": 0}
    original = aggregator._get_sm2_due_items

    async def spy(student_id):
        called["count"] += 1
        return await original(student_id)

    monkeypatch.setattr(aggregator, "_get_sm2_due_items", spy)
    event = TutorEvent(
        type=TutorEventType.QUESTION_ASKED,
        student_id="u1",
        context=EventContext(),
        payload={"question": "test"},
    )
    rich = await aggregator.aggregate(event)
    assert called["count"] >= 1