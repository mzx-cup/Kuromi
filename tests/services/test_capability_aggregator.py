"""Tests for CapabilityAggregator: raw 6-dim data → CapabilityProfile."""
import pytest
from app.services.tutor_engine.capability_aggregator import CapabilityAggregator


class TestCapabilityAggregator:
    @pytest.mark.asyncio
    async def test_aggregate_combines_all_6_dims(self):
        agg = CapabilityAggregator()
        raw = {
            "knowledge_base": {"math": 0.72},
            "code_skill": {"python": 0.55},
            "cognitive_style": {"preferred_modality": "visual", "depth": "deep"},
            "focus_level": {"avg_session_minutes": 35, "streak_days": 7},
            "learning_goals": [{"id": 1, "title": "高考", "progress": 0.42}],
            "weakness": [{"subject": "physics", "mastery": 0.30}],
        }
        profile = await agg.from_raw(raw)
        assert profile.knowledge_base["math"] == pytest.approx(0.72)
        assert profile.weakness[0].subject == "physics"
        assert profile.focus_level.streak_days == 7

    @pytest.mark.asyncio
    async def test_aggregate_for_user_uses_repository(self, monkeypatch):
        from app.services.tutor_engine.capability_aggregator import CapabilityAggregator

        class StubCapRepo:
            async def aggregate_profile(self, user_id):
                return {
                    "knowledge_base": {"math": 0.5},
                    "code_skill": {},
                    "cognitive_style": {"preferred_modality": "visual", "depth": "deep"},
                    "focus_level": {"avg_session_minutes": 30, "streak_days": 3},
                    "learning_goals": [],
                    "weakness": [],
                }

        monkeypatch.setattr(
            "app.services.tutor_engine.capability_aggregator.get_repository_for_user",
            lambda uid, **kwargs: StubCapRepo(),
        )
        agg = CapabilityAggregator()
        profile = await agg.for_user("u1")
        assert profile.knowledge_base["math"] == pytest.approx(0.5)
        assert profile.focus_level.streak_days == 3

    @pytest.mark.asyncio
    async def test_empty_profile_is_valid(self):
        agg = CapabilityAggregator()
        profile = await agg.from_raw({
            "knowledge_base": {},
            "code_skill": {},
            "cognitive_style": {"preferred_modality": "visual", "depth": "deep"},
            "focus_level": {"avg_session_minutes": 0, "streak_days": 0},
            "learning_goals": [],
            "weakness": [],
        })
        assert profile.knowledge_base == {}
        assert profile.learning_goals == []