# -*- coding: utf-8 -*-
"""EmbeddingService 降级链 + SemanticKB 语义检索单测。S1 验收。"""
from __future__ import annotations

import threading

import pytest

from app.services.kb.embedder import EmbeddingService, reset_embedder_for_tests
from app.services.kb.semantic_kb import SemanticKB, reset_semantic_kb_for_tests


# ---------------------------------------------------------------------------
# EmbeddingService
# ---------------------------------------------------------------------------

def test_hash_provider_when_no_local_no_api(monkeypatch):
    svc = EmbeddingService()
    monkeypatch.setattr(svc, "_api_configured", staticmethod(lambda: False))
    monkeypatch.setattr(svc, "_load_local_model", lambda: None)
    assert svc.provider == "hash"
    assert svc.is_semantic is False
    vec = svc.embed("勾股定理")
    assert len(vec) == 384
    assert abs(sum(x * x for x in vec) - 1.0) < 1e-6  # L2 归一化


def test_provider_pref_hash_short_circuits(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "hash")
    svc = EmbeddingService()
    assert svc.provider == "hash"


def test_api_provider_with_fake_endpoint(monkeypatch):
    svc = EmbeddingService()
    monkeypatch.setattr(svc, "_api_configured", staticmethod(lambda: True))
    monkeypatch.setattr(svc, "_load_local_model", lambda: None)

    def fake_embed_api(texts):
        # 与文本首字符相关的确定性伪语义向量（维度 8）
        return [svc._normalize([float(len(t) % 8), 1.0, 0.5, 0.0, 0.2, 0.1, 0.0, 0.3]) for t in texts]

    monkeypatch.setattr(svc, "_embed_api", fake_embed_api)
    assert svc.provider == "api"
    assert svc.is_semantic is True
    assert svc.dim == 8
    assert len(svc.embed("abc")) == 8


def test_api_failure_degrades_to_hash(monkeypatch):
    svc = EmbeddingService()
    monkeypatch.setattr(svc, "_api_configured", staticmethod(lambda: True))
    monkeypatch.setattr(svc, "_load_local_model", lambda: None)

    def boom(texts):
        raise RuntimeError("network down")

    monkeypatch.setattr(svc, "_embed_api", boom)
    assert svc.provider == "api"
    vec = svc.embed("test")  # 失败 → 内部降级 hash
    assert len(vec) == 384
    assert svc.provider == "hash"


def test_cache_returns_same_object():
    svc = EmbeddingService()
    v1 = svc.embed("同一句话")
    v2 = svc.embed("同一一句话")
    v3 = svc.embed("同一句话")
    assert v1 is v3  # 缓存命中（同对象）
    assert v1 is not v2


def test_thread_safety_of_singleton():
    from app.services.kb.embedder import get_embedder
    results = []
    errs = []

    def worker():
        try:
            results.append(len(get_embedder().embed("并发探测")))
        except Exception as e:  # pragma: no cover
            errs.append(e)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errs
    assert all(r == 384 for r in results)


# ---------------------------------------------------------------------------
# SemanticKB（fake qdrant + fake embedder）
# ---------------------------------------------------------------------------

class FakeQdrant:
    """最小 Qdrant 客户端替身：get_collection/create_collection/upsert/query_points。"""

    def __init__(self):
        self.collections: dict[str, list] = {}

    def get_collection(self, name):
        if name not in self.collections:
            raise KeyError(name)
        return name

    def create_collection(self, collection_name, vectors_config):
        self.collections[collection_name] = []

    def upsert(self, collection_name, points):
        by_id = {p.id: p for p in self.collections[collection_name]}
        for p in points:
            by_id[p.id] = p
        self.collections[collection_name] = list(by_id.values())

    def query_points(self, collection_name, query, limit=5, with_payload=True, **kw):
        points = self.collections.get(collection_name, [])
        scored = []
        for p in points:
            score = sum(a * b for a, b in zip(p.vector, query))
            scored.append((score, p))
        scored.sort(key=lambda t: -t[0])

        class _Pt:
            def __init__(self, score, payload):
                self.score = score
                self.payload = payload

        class _Res:
            pass

        res = _Res()
        res.points = [_Pt(s, p.payload) for s, p in scored[:limit] if s >= 0.35]
        return res


class FakeEmbedder:
    """确定性伪语义 embedder：以关键词指示维度模拟语义相似。"""

    def __init__(self, vocab: dict[str, list[float]], dim=8):
        self.vocab = vocab
        self.dim = dim
        self.provider = "fake"
        self.is_semantic = True
        self._base = [0.05] * dim

    def embed(self, text):
        return self.embed_batch([text])[0]

    def embed_batch(self, texts):
        out = []
        for t in texts:
            vec = list(self._base)
            for kw, weights in self.vocab.items():
                if kw in t:
                    for i, w in enumerate(weights):
                        vec[i] = w
            out.append(EmbeddingService._normalize(vec))
        return out


KB = {
    "hadoop": {
        "content": "Hadoop 的核心是 HDFS 和 MapReduce",
        "source": "《大数据处理技术》P12",
        "textbook": "大数据处理技术",
        "chapterId": "ch2",
        "startPage": 12,
    },
    "sorting": {
        "content": "快速排序平均时间复杂度 O(n log n)",
        "source": "《实验指导书》P8",
        "textbook": "实验指导书",
        "chapterId": "ch1",
        "startPage": 8,
    },
}


def _make_kb(vocab):
    qdrant = FakeQdrant()
    embedder = FakeEmbedder(vocab)
    return SemanticKB(
        embedder=embedder,
        qdrant_factory=lambda: qdrant,
        kb_loader=lambda: dict(KB),
    ), qdrant


def test_semantic_kb_index_and_search():
    vocab = {
        "hadoop": [0.9, 0.1, 0, 0, 0, 0, 0, 0],
        "排序": [0, 0, 0.9, 0.1, 0, 0, 0, 0],
    }
    skb, qdrant = _make_kb(vocab)
    hits = skb.search("hadoop 集群架构", top_k=2)
    assert hits, "语义检索应命中"
    assert "Hadoop" in hits[0]["content"] or "hadoop" in hits[0]["key"]
    assert hits[0]["score"] >= 0.35
    assert skb._collection_name(skb._embedder) in qdrant.collections
    # 二次查询复用索引（指纹一致）
    hits2 = skb.search("排序算法", top_k=2)
    assert any("排序" in h["content"] for h in hits2)


def test_semantic_kb_unrelated_query_filtered():
    vocab = {"hadoop": [0.9, 0.1, 0, 0, 0, 0, 0, 0]}
    skb, _ = _make_kb(vocab)
    # "化学反应" 与 vocab 无交集 → 基础向量均匀分，与各文档点积 < 0.35 → 空
    assert skb.search("化学氧化还原反应") == []


def test_semantic_kb_hash_embedder_disables():
    class HashLike:
        provider = "hash"
        is_semantic = False
        dim = 384
        embed = None

        def embed_batch(self, texts):
            raise AssertionError("hash 模式不应建索引")

    skb = SemanticKB(embedder=HashLike(), qdrant_factory=FakeQdrant, kb_loader=lambda: dict(KB))
    assert skb.search("hadoop") == []
    assert skb.is_available() is False


def test_semantic_kb_qdrant_failure_returns_empty():
    class BoomQdrant:
        def get_collection(self, name):
            raise ConnectionError("qdrant down")

        def create_collection(self, *a, **kw):
            raise ConnectionError("qdrant down")

    vocab = {"hadoop": [0.9, 0.1, 0, 0, 0, 0, 0, 0]}
    skb = SemanticKB(
        embedder=FakeEmbedder(vocab),
        qdrant_factory=lambda: BoomQdrant(),
        kb_loader=lambda: dict(KB),
    )
    assert skb.search("hadoop") == []
