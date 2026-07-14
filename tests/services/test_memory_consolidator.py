"""Memory consolidation — clustering (S6.1) + lifecycle (S6.1) + LLM extractor (S6.2).

S6.3 will append consolidator tests.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone


# ---------------------------------------------------------------------------
# clustering.py
# ---------------------------------------------------------------------------


def test_cluster_below_threshold_returns_empty():
    from app.services.memory.clustering import cluster
    events = [
        {"id": "e1", "embedding": [1, 0]},
        {"id": "e2", "embedding": [0, 1]},
    ]
    clusters = cluster(events, threshold=0.75)
    assert clusters == []


def test_cluster_groups_similar():
    from app.services.memory.clustering import cluster
    events = [
        {"id": f"e{i}", "embedding": [1 + i * 0.01, 0]} for i in range(5)
    ]
    clusters = cluster(events, threshold=0.75)
    assert len(clusters) == 1
    assert len(clusters[0]) == 5


def test_cluster_filters_singletons():
    """1 isolated event + 4-cluster of similar events → 1 cluster of 4 (singleton filtered)."""
    from app.services.memory.clustering import cluster
    events = [
        {"id": "lonely", "embedding": [0, 1]},  # orthogonal to the others
        {"id": "a", "embedding": [1, 0.01]},
        {"id": "b", "embedding": [1, 0.02]},
        {"id": "c", "embedding": [1, 0.03]},
        {"id": "d", "embedding": [1, 0.04]},
    ]
    clusters = cluster(events, threshold=0.75)
    # The orthogonal "lonely" event is a singleton → filtered out.
    # The remaining 4 are highly similar (cosine > 0.999) → 1 cluster.
    assert len(clusters) == 1
    assert len(clusters[0]) == 4


def test_cosine_zero_vector_safe():
    """Zero vector should not raise — epsilon guards the divide-by-zero."""
    from app.services.memory.clustering import _cosine
    result = _cosine([0, 0], [1, 1])
    # With epsilon, the value is finite and tiny (close to 0).
    assert isinstance(result, float)
    assert result == result  # not NaN
    assert abs(result) < 0.01


def test_cluster_empty_list():
    from app.services.memory.clustering import cluster
    assert cluster([], threshold=0.75) == []


def test_cluster_single_event_is_filtered():
    from app.services.memory.clustering import cluster
    assert cluster([{"id": "x", "embedding": [1, 0]}], threshold=0.75) == []


# ---------------------------------------------------------------------------
# lifecycle.py
# ---------------------------------------------------------------------------


def test_reinforce_increases_confidence_and_appends_evidence():
    from app.services.memory.lifecycle import reinforce

    semantic = {
        "status": "active",
        "confidence": 0.5,
        "evidence_ids": ["e1"],
        "last_reinforced_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }
    pattern = {"confidence": 0.8, "evidence_ids": ["e2", "e3"]}
    reinforce(semantic, pattern)

    # 0.5 + 0.8 * 0.1 = 0.58
    assert abs(semantic["confidence"] - 0.58) < 1e-9
    assert set(semantic["evidence_ids"]) == {"e1", "e2", "e3"}


def test_reinforce_caps_confidence_at_one():
    from app.services.memory.lifecycle import reinforce

    semantic = {
        "status": "active",
        "confidence": 0.95,
        "evidence_ids": [],
        "last_reinforced_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }
    pattern = {"confidence": 1.0, "evidence_ids": ["e1"]}
    reinforce(semantic, pattern)
    # 0.95 + 0.1 = 1.05 → capped at 1.0
    assert semantic["confidence"] == 1.0


def test_weaken_decreases_confidence_and_demotes_to_fading_below_0_3():
    from app.services.memory.lifecycle import weaken

    semantic = {
        "status": "active",
        "confidence": 0.35,
        "evidence_ids": [],
        "last_reinforced_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }
    weaken(semantic, pattern={})
    assert abs(semantic["confidence"] - 0.25) < 1e-9
    # Below 0.3 → fading
    assert semantic["status"] == "fading"


def test_weaken_floors_at_zero():
    from app.services.memory.lifecycle import weaken

    semantic = {
        "status": "active",
        "confidence": 0.05,
        "evidence_ids": [],
        "last_reinforced_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }
    weaken(semantic, pattern={})
    assert semantic["confidence"] == 0.0
    assert semantic["status"] == "fading"


def test_mark_fading_after_90d():
    from app.services.memory.lifecycle import mark_fading_if_stale, ACTIVE

    old = datetime(2026, 1, 1, tzinfo=timezone.utc)
    semantic = {
        "status": ACTIVE,
        "confidence": 0.6,
        "evidence_ids": [],
        "last_reinforced_at": old,
    }
    now = old + timedelta(days=91)
    mark_fading_if_stale(semantic, now=now)
    assert semantic["status"] == "fading"


def test_mark_fading_not_triggered_before_90d():
    from app.services.memory.lifecycle import mark_fading_if_stale, ACTIVE

    old = datetime(2026, 1, 1, tzinfo=timezone.utc)
    semantic = {
        "status": ACTIVE,
        "confidence": 0.6,
        "evidence_ids": [],
        "last_reinforced_at": old,
    }
    now = old + timedelta(days=89)
    mark_fading_if_stale(semantic, now=now)
    assert semantic["status"] == ACTIVE


def test_mark_retired_after_180d():
    from app.services.memory.lifecycle import (
        mark_retired_if_stale,
        FADING,
    )

    old = datetime(2026, 1, 1, tzinfo=timezone.utc)
    semantic = {
        "status": FADING,
        "confidence": 0.2,
        "evidence_ids": [],
        "last_reinforced_at": old,
    }
    now = old + timedelta(days=181)
    mark_retired_if_stale(semantic, now=now)
    assert semantic["status"] == "retired"


def test_mark_retired_not_triggered_for_active():
    """An active row older than 180d must NOT be retired in one step —
    it has to go through the fading stage first."""
    from app.services.memory.lifecycle import (
        mark_retired_if_stale,
        ACTIVE,
    )

    old = datetime(2026, 1, 1, tzinfo=timezone.utc)
    semantic = {
        "status": ACTIVE,
        "confidence": 0.6,
        "evidence_ids": [],
        "last_reinforced_at": old,
    }
    now = old + timedelta(days=365)
    mark_retired_if_stale(semantic, now=now)
    assert semantic["status"] == ACTIVE


def test_reinforce_reactivates_fading_when_confidence_above_0_5():
    from app.services.memory.lifecycle import reinforce, FADING

    semantic = {
        "status": FADING,
        "confidence": 0.48,
        "evidence_ids": ["e1"],
        "last_reinforced_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }
    # 0.48 + 0.8 * 0.1 = 0.56 > 0.5 → reactivated to active
    reinforce(semantic, pattern={"confidence": 0.8, "evidence_ids": ["e2"]})
    assert semantic["status"] == "active"


def test_reinforce_dedupes_evidence_ids():
    from app.services.memory.lifecycle import reinforce

    semantic = {
        "status": "active",
        "confidence": 0.5,
        "evidence_ids": ["e1", "e2"],
        "last_reinforced_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }
    reinforce(semantic, pattern={"confidence": 0.5, "evidence_ids": ["e2", "e3"]})
    # Order may vary (set dedup), but no duplicates and both old + new kept.
    assert sorted(semantic["evidence_ids"]) == ["e1", "e2", "e3"]


# ---------------------------------------------------------------------------
# llm_extractor.py (S6.2)
# ---------------------------------------------------------------------------


def test_extract_pattern_returns_statement_and_evidence():
    """Plan-required test: extract_pattern returns statement + evidence_ids."""
    from app.services.memory.llm_extractor import extract_pattern
    out = extract_pattern(user_id="u1", cluster=[
        {"id": "e1", "summary": "Q1: 函数概念"},
        {"id": "e2", "summary": "Q2: 函数定义"},
        {"id": "e3", "summary": "Q3: 复合函数"},
    ])
    assert "statement" in out
    assert set(out["evidence_ids"]) == {"e1", "e2", "e3"}


def test_extract_pattern_confidence_in_unit_interval():
    """confidence must be a float in [0.0, 1.0]."""
    from app.services.memory.llm_extractor import extract_pattern
    out = extract_pattern(user_id="u1", cluster=[
        {"id": "e1", "summary": "x"},
        {"id": "e2", "summary": "y"},
        {"id": "e3", "summary": "z"},
    ])
    assert isinstance(out["confidence"], float)
    assert 0.0 <= out["confidence"] <= 1.0


def test_extract_pattern_evidence_ids_match_cluster_ids():
    """evidence_ids must contain exactly the ids present in the cluster (set equality)."""
    from app.services.memory.llm_extractor import extract_pattern
    cluster = [
        {"id": "a", "summary": "alpha"},
        {"id": "b", "summary": "beta"},
        {"id": "c", "summary": "gamma"},
        {"id": "d", "summary": "delta"},
    ]
    out = extract_pattern(user_id="u1", cluster=cluster)
    assert set(out["evidence_ids"]) == {"a", "b", "c", "d"}
    assert len(out["evidence_ids"]) == len(cluster)


def test_extract_pattern_handles_empty_cluster():
    """Empty cluster: zero evidence, confidence collapses to 0.0 (nothing to extract)."""
    from app.services.memory.llm_extractor import extract_pattern
    out = extract_pattern(user_id="u1", cluster=[])
    assert out["evidence_ids"] == []
    assert out["confidence"] == 0.0
    # statement should still be a string (graceful degradation)
    assert isinstance(out["statement"], str)


def test_extract_pattern_statement_mentions_cluster_size():
    """Stub determinism: the statement must reference the cluster size so tests can assert it."""
    from app.services.memory.llm_extractor import extract_pattern
    cluster = [{"id": f"e{i}", "summary": f"item {i}"} for i in range(5)]
    out = extract_pattern(user_id="u1", cluster=cluster)
    # The plan stub says: f"用户在 {len(cluster)} 个事件中重复练习相关内容"
    assert str(len(cluster)) in out["statement"]