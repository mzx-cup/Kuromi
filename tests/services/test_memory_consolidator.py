"""Memory consolidation — clustering (S6.1) + lifecycle (S6.1) + LLM extractor (S6.2)
+ consolidator pipeline (S6.3).

S6.3 appends the 8 end-to-end tests for ``consolidate_user``.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch


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


# ---------------------------------------------------------------------------
# consolidator (S6.3)
# ---------------------------------------------------------------------------


class _FakeEpisode:
    """Stand-in for an ``EpisodicMemory`` row."""

    def __init__(self, id, user_id, summary, embedding):
        self.id = id
        self.user_id = user_id
        self.summary = summary
        self.embedding = embedding
        self.consolidated_into = None


class _FakeSemantic:
    """Stand-in for a ``SemanticMemory`` row with mutable state."""

    def __init__(
        self,
        id=None,
        user_id="u1",
        statement="",
        confidence=0.7,
        evidence_ids=None,
        last_reinforced_at=None,
        status="active",
    ):
        self.id = id
        self.user_id = user_id
        self.statement = statement
        self.confidence = confidence
        self.evidence_ids = list(evidence_ids or [])
        self.last_reinforced_at = last_reinforced_at
        self.status = status


def _make_episodes(n, *, base_emb):
    """Build n fake episodes with near-identical embeddings so they cluster."""
    events = []
    for i in range(n):
        emb = [base_emb[0] + i * 0.005, base_emb[1] + i * 0.005]
        e = _FakeEpisode(
            id=f"e{i + 1}", user_id="u1", summary=f"item {i + 1}", embedding=emb,
        )
        events.append(e)
    return events


def test_consolidator_skips_when_too_few_episodic():
    from app.services.memory import consolidator as con

    with patch.object(con, "OrmEpisodicMemoryRepository") as MockEpi, \
         patch.object(con, "OrmSemanticMemoryRepository"), \
         patch.object(con, "OrmMemoryConsolidationJobRepository"):
        MockEpi.return_value.recent_unconsolidated.return_value = [
            _FakeEpisode("e1", "u1", "a", [1, 0]),
            _FakeEpisode("e2", "u1", "b", [1, 0]),
        ]
        result = con.consolidate_user("u1")
    assert result["skipped"] is True
    assert "reason" in result
    assert result["episodic_count"] == 2


def test_consolidator_creates_new_semantic_when_no_similar():
    from app.services.memory import consolidator as con

    episodes = _make_episodes(3, base_emb=[1.0, 0.0])

    with patch.object(con, "OrmEpisodicMemoryRepository") as MockEpi, \
         patch.object(con, "OrmSemanticMemoryRepository") as MockSem, \
         patch.object(con, "OrmMemoryConsolidationJobRepository") as MockJob:
        MockEpi.return_value.recent_unconsolidated.return_value = episodes
        MockSem.return_value.find_similar.return_value = []
        MockJob.return_value.insert.return_value = 100

        result = con.consolidate_user("u1")

    assert result["skipped"] is False
    assert result["clusters_processed"] == 1
    assert result["new_semantics"] == 1
    assert result["reinforced"] == 0
    assert result["weakened"] == 0
    MockSem.return_value.insert.assert_called_once()


def test_consolidator_reinforces_existing_similar_semantic():
    from app.services.memory import consolidator as con

    episodes = _make_episodes(3, base_emb=[1.0, 0.0])
    existing = _FakeSemantic(id=11, user_id="u1", confidence=0.6)

    with patch.object(con, "OrmEpisodicMemoryRepository") as MockEpi, \
         patch.object(con, "OrmSemanticMemoryRepository") as MockSem, \
         patch.object(con, "OrmMemoryConsolidationJobRepository") as MockJob:
        MockEpi.return_value.recent_unconsolidated.return_value = episodes
        MockSem.return_value.find_similar.return_value = [existing]
        MockJob.return_value.insert.return_value = 200

        result = con.consolidate_user("u1")

    assert result["skipped"] is False
    assert result["new_semantics"] == 0
    # Pattern confidence 0.7 > 0.5 → reinforce.
    assert result["reinforced"] >= 1
    # The consolidator should have called ``update_fields`` with a confidence
    # boosted from 0.6 by 0.7 * 0.1 = 0.07 → ≥ 0.67.
    update_call = MockSem.return_value.update_fields.call_args
    persisted = update_call[0][1]  # second positional arg: fields dict
    assert persisted["confidence"] > 0.6
    MockEpi.return_value.mark_consolidated.assert_called()


def test_consolidator_weakens_contradicting_semantic():
    """Low-confidence pattern triggers weaken (S6.3 heuristic)."""
    from app.services.memory import consolidator as con

    episodes = _make_episodes(3, base_emb=[1.0, 0.0])
    existing = _FakeSemantic(id=22, confidence=0.5, status="active")

    def low_conf_extract(user_id, cluster):
        return {
            "statement": "contradicting pattern",
            "confidence": 0.2,  # < 0.5 → triggers weaken
            "evidence_ids": [c["id"] for c in cluster],
        }

    with patch.object(con, "OrmEpisodicMemoryRepository") as MockEpi, \
         patch.object(con, "OrmSemanticMemoryRepository") as MockSem, \
         patch.object(con, "OrmMemoryConsolidationJobRepository") as MockJob, \
         patch.object(con, "extract_pattern", side_effect=low_conf_extract):
        MockEpi.return_value.recent_unconsolidated.return_value = episodes
        MockSem.return_value.find_similar.return_value = [existing]
        MockJob.return_value.insert.return_value = 300

        result = con.consolidate_user("u1")

    assert result["skipped"] is False
    assert result["weakened"] >= 1
    assert existing.confidence < 0.5


def test_consolidator_marks_fading_after_90d_no_evidence():
    """A semantic last_reinforced 91d ago should be moved to fading.

    The cluster pattern's confidence is below the reinforce threshold (≤
    0.5), so the consolidator calls ``weaken`` — which does NOT refresh
    ``last_reinforced_at`` — and then applies the 90-day stale check.
    """
    from app.services.memory import consolidator as con

    episodes = _make_episodes(3, base_emb=[1.0, 0.0])
    long_ago = datetime.utcnow() - timedelta(days=91)
    existing = _FakeSemantic(
        id=33, confidence=0.6, status="active", last_reinforced_at=long_ago,
    )

    def low_conf_extract(user_id, cluster):
        return {
            "statement": "weak pattern",
            "confidence": 0.2,
            "evidence_ids": [c["id"] for c in cluster],
        }

    with patch.object(con, "OrmEpisodicMemoryRepository") as MockEpi, \
         patch.object(con, "OrmSemanticMemoryRepository") as MockSem, \
         patch.object(con, "OrmMemoryConsolidationJobRepository") as MockJob, \
         patch.object(con, "extract_pattern", side_effect=low_conf_extract):
        MockEpi.return_value.recent_unconsolidated.return_value = episodes
        MockSem.return_value.find_similar.return_value = [existing]
        MockJob.return_value.insert.return_value = 400

        result = con.consolidate_user("u1")

    assert result["skipped"] is False
    assert existing.status == "fading"


def test_consolidator_retires_after_180d():
    """A fading semantic last_reinforced 181d ago should be moved to retired."""
    from app.services.memory import consolidator as con

    episodes = _make_episodes(3, base_emb=[1.0, 0.0])
    long_ago = datetime.utcnow() - timedelta(days=181)
    existing = _FakeSemantic(
        id=44, confidence=0.2, status="fading", last_reinforced_at=long_ago,
    )

    def low_conf_extract(user_id, cluster):
        return {
            "statement": "weak pattern",
            "confidence": 0.2,
            "evidence_ids": [c["id"] for c in cluster],
        }

    with patch.object(con, "OrmEpisodicMemoryRepository") as MockEpi, \
         patch.object(con, "OrmSemanticMemoryRepository") as MockSem, \
         patch.object(con, "OrmMemoryConsolidationJobRepository") as MockJob, \
         patch.object(con, "extract_pattern", side_effect=low_conf_extract):
        MockEpi.return_value.recent_unconsolidated.return_value = episodes
        MockSem.return_value.find_similar.return_value = [existing]
        MockJob.return_value.insert.return_value = 500

        result = con.consolidate_user("u1")

    assert result["skipped"] is False
    assert existing.status == "retired"


def test_consolidator_partial_failure_does_not_block_other_clusters():
    """A failure inside one cluster's processing must not stop the others.

    Three distinct clusters (three orthogonal embedding directions). The
    second cluster's ``find_similar`` raises a simulated error; the first
    and third clusters must still each produce a SemanticMemory insert.
    """
    from app.services.memory import consolidator as con

    # 3 orthogonal clusters (cosine ≈ 0 between them). Each gets 3 events
    # so the cluster() filter keeps it.
    cluster_a = _make_episodes(3, base_emb=[1.0, 0.0])
    cluster_b = _make_episodes(3, base_emb=[0.0, 1.0])
    cluster_c = _make_episodes(3, base_emb=[0.5, 0.5])
    episodes = cluster_a + cluster_b + cluster_c

    with patch.object(con, "OrmEpisodicMemoryRepository") as MockEpi, \
         patch.object(con, "OrmSemanticMemoryRepository") as MockSem, \
         patch.object(con, "OrmMemoryConsolidationJobRepository") as MockJob:
        MockEpi.return_value.recent_unconsolidated.return_value = episodes
        sem_calls = {"count": 0}

        def find_similar_side_effect(*, user_id, statement):
            sem_calls["count"] += 1
            if sem_calls["count"] == 2:
                raise RuntimeError("simulated cluster B failure")
            return []

        MockSem.return_value.find_similar.side_effect = find_similar_side_effect
        MockJob.return_value.insert.return_value = 600

        result = con.consolidate_user("u1")

    assert result["skipped"] is False
    # cluster A and cluster C should both have inserted a SemanticMemory row.
    assert MockSem.return_value.insert.call_count == 2


def test_consolidator_concurrent_writes_dont_lose_clusters():
    """Two sequential consolidate_user calls on disjoint event sets both run cleanly."""
    from app.services.memory import consolidator as con

    set_a = _make_episodes(3, base_emb=[1.0, 0.01])
    set_b = _make_episodes(3, base_emb=[0.0, 1.0])

    with patch.object(con, "OrmEpisodicMemoryRepository") as MockEpi, \
         patch.object(con, "OrmSemanticMemoryRepository") as MockSem, \
         patch.object(con, "OrmMemoryConsolidationJobRepository") as MockJob:
        MockJob.return_value.insert.side_effect = [701, 702]

        for i, e in enumerate(set_a):
            e.id = f"a{i + 1}"
        MockEpi.return_value.recent_unconsolidated.return_value = set_a
        MockSem.return_value.find_similar.return_value = []
        r1 = con.consolidate_user("u1")
        assert r1["skipped"] is False
        first_inserts = MockSem.return_value.insert.call_count

        for i, e in enumerate(set_b):
            e.id = f"b{i + 1}"
        MockEpi.return_value.recent_unconsolidated.return_value = set_b
        r2 = con.consolidate_user("u1")
        assert r2["skipped"] is False
        second_inserts = MockSem.return_value.insert.call_count - first_inserts

    assert r1["clusters_processed"] == 1
    assert r2["clusters_processed"] == 1
    assert second_inserts >= 1
    assert MockJob.return_value.insert.call_count == 2
