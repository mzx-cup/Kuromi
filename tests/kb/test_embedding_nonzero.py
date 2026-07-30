"""Tests for KB deterministic embedding (HIGH-1 fix).

验证:
  - hash_embed() 不返回全零向量
  - 相同文本 → 相同向量（缓存友好）
  - 不同文本 → 不同向量（cosine 有意义）
  - cosine_similarity() 对非零向量返回 [-1, 1] 范围
  - 相似文本 cosine > 不相似文本 cosine
"""
from __future__ import annotations

import math

import pytest


def test_hash_embed_returns_nonzero_vector():
    """hash_embed() 输出必须不全为零（修复 HIGH-1）。"""
    from app.services.kb.deterministic_embedder import hash_embed

    vec = hash_embed("勾股定理 a²+b²=c²")
    assert len(vec) == 384
    assert any(v != 0.0 for v in vec), "vector must not be all zeros"


def test_hash_embed_deterministic():
    """相同文本必须生成相同向量。"""
    from app.services.kb.deterministic_embedder import hash_embed

    v1 = hash_embed("hello world")
    v2 = hash_embed("hello world")
    assert v1 == v2


def test_hash_embed_different_for_different_texts():
    """不同文本应生成不同向量。"""
    from app.services.kb.deterministic_embedder import hash_embed

    v1 = hash_embed("勾股定理 a²+b²=c²")
    v2 = hash_embed("牛顿第二定律 F=ma")
    # 至少要有一些维度不同（不全等）
    assert v1 != v2


def test_cosine_similarity_in_valid_range():
    """cosine_similarity 对非零向量必须返回 [-1, 1]。"""
    from app.services.kb.deterministic_embedder import cosine_similarity

    a = [0.1] * 384
    b = [0.2] * 384
    sim = cosine_similarity(a, b)
    assert -1.0 <= sim <= 1.0
    assert not math.isnan(sim)
    assert not math.isinf(sim)


def test_cosine_similarity_returns_one_for_identical():
    """相同向量 cosine 必须为 1.0。"""
    from app.services.kb.deterministic_embedder import cosine_similarity, hash_embed

    v = hash_embed("test")
    assert abs(cosine_similarity(v, v) - 1.0) < 1e-6


def test_cosine_similarity_returns_zero_for_orthogonal():
    """正交向量 cosine 必须 ≈ 0。"""
    from app.services.kb.deterministic_embedder import cosine_similarity

    a = [1.0] + [0.0] * 383
    b = [0.0] * 383 + [1.0]
    sim = cosine_similarity(a, b)
    assert abs(sim) < 1e-6


def test_cosine_similarity_zero_vector_returns_zero():
    """全零向量 cosine 必须返回 0（避免 NaN）。"""
    from app.services.kb.deterministic_embedder import cosine_similarity

    a = [0.0] * 384
    b = [0.1] * 384
    sim = cosine_similarity(a, b)
    assert sim == 0.0
    assert not math.isnan(sim)


def test_similar_texts_have_higher_cosine():
    """相似文本 cosine 必须 > 不相似文本 cosine。"""
    from app.services.kb.deterministic_embedder import (
        cosine_similarity,
        hash_embed,
    )

    v_query = hash_embed("勾股定理")
    v_similar = hash_embed("勾股定理 a²+b²=c² 直角三角形")
    v_unrelated = hash_embed("Python 函数定义 def foo()")

    sim_related = cosine_similarity(v_query, v_similar)
    sim_unrelated = cosine_similarity(v_query, v_unrelated)

    assert sim_related > sim_unrelated, (
        f"similar texts should have higher cosine: "
        f"related={sim_related:.3f}, unrelated={sim_unrelated:.3f}"
    )


def test_embedding_dimension_is_384():
    """默认维度 384（与 Qdrant 现有配置匹配）。"""
    from app.services.kb.deterministic_embedder import hash_embed, EMBEDDING_DIM

    assert EMBEDDING_DIM == 384
    vec = hash_embed("test")
    assert len(vec) == EMBEDDING_DIM


def test_embedding_norm_is_reasonable():
    """embedding 向量 L2 norm 应该 > 0 且有限。"""
    from app.services.kb.deterministic_embedder import hash_embed

    vec = hash_embed("normal text input")
    norm = math.sqrt(sum(v * v for v in vec))
    assert norm > 0.0
    assert math.isfinite(norm)