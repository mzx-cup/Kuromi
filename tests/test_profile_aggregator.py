# -*- coding: utf-8 -*-
"""Tests for profile_aggregator.aggregate_profile."""

import pytest
from app.services.profile_aggregator import aggregate_profile


class TestAggregateProfile:
    """Verify that aggregate_profile correctly aggregates user memories into profile data."""

    def test_empty_memories_returns_empty_profile(self):
        result = aggregate_profile([])
        assert result["learning_traits"] == []
        assert result["personality_traits"] == []
        assert result["goals_interests"] == []
        assert "last_updated" in result

    def test_aggregates_memories_by_category(self):
        memories = [
            {
                "id": "mem_001",
                "memory_type": "learning_trait",
                "content": "喜欢通过图表理解抽象概念",
                "confidence": 0.85,
                "access_count": 5,
                "confirmed": 1,
            },
            {
                "id": "mem_002",
                "memory_type": "personality",
                "content": "性格内向，先思考再提问",
                "confidence": 0.78,
                "access_count": 3,
                "confirmed": 0,
            },
            {
                "id": "mem_003",
                "memory_type": "goal",
                "content": "想学好机器学习",
                "confidence": 0.9,
                "access_count": 10,
                "confirmed": 1,
            },
        ]
        result = aggregate_profile(memories)
        assert len(result["learning_traits"]) == 1
        assert len(result["personality_traits"]) == 1
        assert len(result["goals_interests"]) == 1
        assert result["learning_traits"][0]["label"] == "喜欢通过图表理解抽象概念"
        assert result["personality_traits"][0]["label"] == "性格内向，先思考再提问"
        assert result["goals_interests"][0]["label"] == "想学好机器学习"

    def test_limits_traits_per_category_to_5(self):
        memories = [
            {
                "id": f"mem_{i:03d}",
                "memory_type": "interest",
                "content": f"兴趣{i}",
                "confidence": 0.5 + i * 0.05,
                "access_count": i,
                "confirmed": 0,
            }
            for i in range(10)
        ]
        result = aggregate_profile(memories)
        assert len(result["goals_interests"]) == 5

    def test_score_combines_confidence_and_access_count(self):
        # memory1: confidence=0.9, access=5, confirmed=1
        # score = 0.9*0.6 + min(5/10, 0.3) + 0.1 = 0.54 + 0.3 + 0.1 = 0.94
        # memory2: confidence=0.6, access=0, confirmed=0
        # score = 0.6*0.6 + 0 + 0 = 0.36
        memories = [
            {
                "id": "mem_high",
                "memory_type": "knowledge",
                "content": "高置信度知识",
                "confidence": 0.9,
                "access_count": 5,
                "confirmed": 1,
            },
            {
                "id": "mem_low",
                "memory_type": "knowledge",
                "content": "低置信度知识",
                "confidence": 0.6,
                "access_count": 0,
                "confirmed": 0,
            },
        ]
        result = aggregate_profile(memories)
        traits = result["learning_traits"]
        assert traits[0]["score"] > traits[1]["score"]
        assert traits[0]["memory_id"] == "mem_high"
        assert traits[1]["memory_id"] == "mem_low"

    def test_all_memory_types_mapped_correctly(self):
        memories = [
            {"id": "m1", "memory_type": "learning_trait", "content": "a", "confidence": 0.8, "access_count": 1, "confirmed": 0},
            {"id": "m2", "memory_type": "knowledge", "content": "b", "confidence": 0.8, "access_count": 1, "confirmed": 0},
            {"id": "m3", "memory_type": "personality", "content": "c", "confidence": 0.8, "access_count": 1, "confirmed": 0},
            {"id": "m4", "memory_type": "emotion", "content": "d", "confidence": 0.8, "access_count": 1, "confirmed": 0},
            {"id": "m5", "memory_type": "interaction", "content": "e", "confidence": 0.8, "access_count": 1, "confirmed": 0},
            {"id": "m6", "memory_type": "background", "content": "f", "confidence": 0.8, "access_count": 1, "confirmed": 0},
            {"id": "m7", "memory_type": "preference", "content": "g", "confidence": 0.8, "access_count": 1, "confirmed": 0},
            {"id": "m8", "memory_type": "interest", "content": "h", "confidence": 0.8, "access_count": 1, "confirmed": 0},
            {"id": "m9", "memory_type": "goal", "content": "i", "confidence": 0.8, "access_count": 1, "confirmed": 0},
        ]
        result = aggregate_profile(memories)
        assert len(result["learning_traits"]) == 2
        assert len(result["personality_traits"]) == 3
        assert len(result["goals_interests"]) == 4

    def test_output_structure(self):
        memories = [
            {
                "id": "mem_001",
                "memory_type": "learning_trait",
                "content": "喜欢视觉化学习",
                "confidence": 0.85,
                "access_count": 5,
                "confirmed": 1,
            },
        ]
        result = aggregate_profile(memories)
        trait = result["learning_traits"][0]
        assert "label" in trait
        assert "score" in trait
        assert "memory_id" in trait
        assert "memory_type" in trait
        assert "confidence" in trait
        assert "access_count" in trait

    def test_confirmed_bonus_applied(self):
        memories = [
            {
                "id": "mem_confirmed",
                "memory_type": "goal",
                "content": "已确认目标",
                "confidence": 0.8,
                "access_count": 0,
                "confirmed": 1,
            },
            {
                "id": "mem_unconfirmed",
                "memory_type": "goal",
                "content": "未确认目标",
                "confidence": 0.8,
                "access_count": 0,
                "confirmed": 0,
            },
        ]
        result = aggregate_profile(memories)
        traits = result["goals_interests"]
        confirmed_trait = next(t for t in traits if t["memory_id"] == "mem_confirmed")
        unconfirmed_trait = next(t for t in traits if t["memory_id"] == "mem_unconfirmed")
        assert confirmed_trait["score"] == pytest.approx(unconfirmed_trait["score"] + 0.1)

    def test_access_count_cap_at_3(self):
        # access_count=20 -> min(20/10, 0.3) = 0.3
        # access_count=2  -> min(2/10, 0.3) = 0.2
        memories = [
            {
                "id": "mem_high_access",
                "memory_type": "interest",
                "content": "高频访问兴趣",
                "confidence": 0.8,
                "access_count": 20,
                "confirmed": 0,
            },
            {
                "id": "mem_low_access",
                "memory_type": "interest",
                "content": "低频访问兴趣",
                "confidence": 0.8,
                "access_count": 2,
                "confirmed": 0,
            },
        ]
        result = aggregate_profile(memories)
        traits = result["goals_interests"]
        high = next(t for t in traits if t["memory_id"] == "mem_high_access")
        low = next(t for t in traits if t["memory_id"] == "mem_low_access")
        assert high["score"] > low["score"]
        # Both have same confidence, diff is access_count contribution:
        # high: 0.8*0.6 + 0.3 = 0.78
        # low:  0.8*0.6 + 0.2 = 0.68
        assert high["score"] == pytest.approx(0.78)
        assert low["score"] == pytest.approx(0.68)
