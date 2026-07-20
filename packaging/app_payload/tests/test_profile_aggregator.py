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


# ====== 🆕 pytest parametrize 改造：9 种记忆类型映射 ======

MEMORY_TYPE_MAPPING = [
    pytest.param("learning_trait", "learning_traits", id="learning_trait→learning"),
    pytest.param("knowledge",       "learning_traits", id="knowledge→learning"),
    pytest.param("personality",     "personality_traits", id="personality→personality"),
    pytest.param("emotion",         "personality_traits", id="emotion→personality"),
    pytest.param("interaction",     "personality_traits", id="interaction→personality"),
    pytest.param("background",      "goals_interests", id="background→goals"),
    pytest.param("preference",      "goals_interests", id="preference→goals"),
    pytest.param("interest",        "goals_interests", id="interest→goals"),
    pytest.param("goal",            "goals_interests", id="goal→goals"),
]


@pytest.mark.parametrize("memory_type,expected_category", MEMORY_TYPE_MAPPING)
def test_memory_type_mapped_to_correct_category(memory_type, expected_category):
    """参数化：验证 9 种记忆类型各自映射到正确的画像类别

    这是 pytest parametrize 的高级用法 — 把 9 个重复测试压缩为 1 个数据驱动测试。
    加新记忆类型只需在 MEMORY_TYPE_MAPPING 列表里加一行。
    """
    memories = [{
        "id": f"mem_{memory_type}",
        "memory_type": memory_type,
        "content": f"测试内容-{memory_type}",
        "confidence": 0.8,
        "access_count": 1,
        "confirmed": 0,
    }]
    result = aggregate_profile(memories)

    # 期望的类别应有 1 条记录，其他类别为空
    assert len(result[expected_category]) == 1, \
        f"类型 '{memory_type}' 应映射到 '{expected_category}'，实际为 {len(result[expected_category])} 条"
    assert result[expected_category][0]["memory_type"] == memory_type, \
        f"映射后的 memory_type 应为 '{memory_type}'"


# ====== 🆕 评分公式白盒测试 — 参数化 ======

SCORE_CALCULATION_CASES = [
    # (confidence, access_count, confirmed, expected_score, desc)
    pytest.param(0.9, 5, 1, 0.94, "高置信度+中频访问+已确认", id="high-confirmed"),
    pytest.param(0.6, 0, 0, 0.36, "低置信度+无访问+未确认", id="low-bare"),
    pytest.param(0.8, 20, 0, 0.78, "access_count达封顶上限", id="access-capped"),
    pytest.param(0.8, 2, 0, 0.68, "access_count未达封顶", id="access-uncapped"),
    pytest.param(0.8, 0, 1, 0.48 + 0.1, "仅确认加分", id="confirmed-only"),  # 0.48 + 0.1 = 0.58
    pytest.param(0.5, 0, 0, 0.30, "最低有效分数", id="minimal-score"),
    pytest.param(1.0, 10, 1, 1.00, "满分场景", id="full-score"),
]


@pytest.mark.parametrize("confidence,access_count,confirmed,expected_score,desc",
                          SCORE_CALCULATION_CASES)
def test_score_calculation_formula(confidence, access_count, confirmed, expected_score, desc):
    """白盒测试：参数化验证评分公式

    公式: score = confidence * 0.6 + min(access_count / 10, 0.3) + (confirmed ? 0.1 : 0)

    7 组数据覆盖了公式的每个组成部分的典型值。
    """
    from app.services.profile_aggregator import _calculate_score
    result = _calculate_score(confidence, access_count, confirmed)
    assert result == pytest.approx(expected_score, abs=1e-4), \
        f"场景 '{desc}'：期望 {expected_score}，实际 {result:.4f}"
