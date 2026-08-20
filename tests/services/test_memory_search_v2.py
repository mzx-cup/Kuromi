# -*- coding: utf-8 -*-
"""MemorySearchV2（双路召回 + RRF）单测。S1 验收。"""
from __future__ import annotations

import pytest

from app.services.memory_search import MemorySearchV2, _tokenize


class FakeRepo:
    def __init__(self, rows):
        self.rows = rows
        self.bumped = []

    def get_memories(self, user_id, memory_type=None, limit=20):
        return [dict(r) for r in self.rows[:limit]]

    def bump_memory_access(self, memory_id):
        self.bumped.append(memory_id)


def _row(mid, content, **kw):
    return {
        "id": mid,
        "user_id": "u1",
        "memory_type": "fact",
        "content": content,
        "confidence": kw.get("confidence", 1.0),
        "access_count": kw.get("access_count", 1),
        "confirmed": kw.get("confirmed", 0),
    }


ROWS = [
    _row(1, "学生喜欢用 Python 写算法题"),
    _row(2, "上次学到一元二次方程的配方法"),
    _row(3, "学生每天晚上九点学习大数据课程"),
    _row(4, "学生对 HDFS 分布式存储很感兴趣"),
]


class NoVecSearch(MemorySearchV2):
    """禁用向量路径的关键词版（等价 embedder 非 semantic 时的行为）。"""

    def _vector_ok(self):
        return False


# ---------------------------------------------------------------------------
# 分词
# ---------------------------------------------------------------------------

def test_tokenize_chinese_bigram_and_english():
    toks = _tokenize("HDFS 写入流程 write pipeline")
    assert "hdfs" in toks
    assert "write" in toks
    assert "写入" in toks
    assert "入流" in toks  # bigram
    assert "w" not in toks  # 单字母英文词不进索引


# ---------------------------------------------------------------------------
# 关键词路径（向量降级时）
# ---------------------------------------------------------------------------

def test_keyword_only_search_finds_relevant():
    s = NoVecSearch(repo_factory=lambda: FakeRepo(ROWS))
    hits = s.search("u1", "配方法 怎么推导", limit=3, min_confidence=0.5)
    assert hits, "关键词路径应有命中"
    assert any("配方法" in m["content"] for m in hits)


def test_keyword_search_empty_query_returns_empty():
    s = NoVecSearch(repo_factory=lambda: FakeRepo(ROWS))
    assert s.search("u1", "", limit=3, min_confidence=0.5) == []


def test_min_confidence_filters():
    rows = [ROWS[0], _row(9, "低置信记忆", confidence=0.2)]
    s = NoVecSearch(repo_factory=lambda: FakeRepo(rows))
    hits = s.search("u1", "低置信 记忆", limit=3, min_confidence=0.5)
    assert all(m["id"] != 9 for m in hits)


def test_bumps_access_for_returned_rows():
    repo = FakeRepo(ROWS)
    s = NoVecSearch(repo_factory=lambda: repo)
    s.search("u1", "配方法", limit=2, min_confidence=0.5)
    assert repo.bumped, "返回的记忆应 bump access_count"


# ---------------------------------------------------------------------------
# RRF 融合
# ---------------------------------------------------------------------------

class ScriptedVecSearch(MemorySearchV2):
    """向量路径脚本化返回，验证 RRF 融合逻辑。"""

    def __init__(self, repo, vec_ranked_ids):
        super().__init__(repo_factory=lambda: repo)
        self._vec_ids = vec_ranked_ids

    def _vector_ok(self):
        return True

    def _vector_search(self, user_id, query, rows):
        by_id = {m["id"]: m for m in rows}
        hits = []
        for rank, mid in enumerate(self._vec_ids):
            if mid in by_id:
                hits.append((by_id[mid], rank))
        return hits


def test_rrf_both_paths_ranks_dual_hit_first():
    # 关键词路径对 query "学习 大数据 课程" 命中 id=3
    # 向量路径脚本返回 [2, 3]（id=3 是双路命中）
    repo = FakeRepo(ROWS)
    s = ScriptedVecSearch(repo, vec_ranked_ids=[2, 3])
    hits = s.search("u1", "大数据课程", limit=3, min_confidence=0.5)
    assert hits
    # id=3 双路命中 RRF 最高
    assert hits[0]["id"] == 3
    memories, logs = s.search("u1", "大数据课程", limit=3, min_confidence=0.5, with_logs=True)
    assert logs[0]["memory_id"] == 3
    assert "vec" in logs[0]["path"] and "kw" in logs[0]["path"]


def test_rrf_vec_only_hit_still_returned():
    repo = FakeRepo(ROWS)
    # query 与 id=4 无字面重叠（英文之外），只能靠向量命中
    s = ScriptedVecSearch(repo, vec_ranked_ids=[4])
    hits = s.search("u1", "分布式文件系统原理", limit=3, min_confidence=0.5)
    assert any(m["id"] == 4 for m in hits), "向量单路命中也应返回"


# ---------------------------------------------------------------------------
# memory_retriever 集成：flag + 回退
# ---------------------------------------------------------------------------

def test_v2_flag_off_falls_back(monkeypatch):
    from app.services import memory_retriever

    monkeypatch.setenv("MEMORY_V2", "off")
    called = {"v2": False}

    class ExplodeV2:
        def search(self, *a, **kw):
            called["v2"] = True
            raise AssertionError("flag off 时不应调用 v2")

    monkeypatch.setattr(
        "app.services.memory_search.get_memory_search_v2", lambda: ExplodeV2()
    )
    # legacy 路径用空 repo → 返回 []
    monkeypatch.setattr(
        "app.repositories.legacy.chat.DbPyChatRepository",
        lambda *a, **kw: FakeRepo(ROWS),
    )
    result = memory_retriever._retrieve_memories_core("u1", "配方法", 3, 0.5)
    assert not called["v2"]
    assert isinstance(result, list)


def test_v2_exception_falls_back_to_legacy(monkeypatch):
    from app.services import memory_retriever

    monkeypatch.setenv("MEMORY_V2", "on")

    class ExplodeV2:
        def search(self, *a, **kw):
            raise RuntimeError("qdrant down")

    monkeypatch.setattr(
        "app.services.memory_search.get_memory_search_v2", lambda: ExplodeV2()
    )
    monkeypatch.setattr(
        "app.repositories.legacy.chat.DbPyChatRepository",
        lambda *a, **kw: FakeRepo(ROWS),
    )
    result = memory_retriever._retrieve_memories_core("u1", "配方法", 3, 0.5)
    # legacy 路径（字符重叠）也应召回 id=2
    assert any(m["id"] == 2 for m in result)
