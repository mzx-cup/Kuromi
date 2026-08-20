# -*- coding: utf-8 -*-
"""记忆检索 v2 —— 双路召回 + RRF 融合（S1）。

替换 memory_retriever 的「拉 200 条全量 + 中文按单字重叠」打分：

    query → [Qdrant 向量 top20] ∥ [进程内倒排索引 top20]
          → RRF(k=60) 融合
          → rerank(confidence / access_count / confirmed 小幅加权)
          → top-k

实现选择（与设计稿的偏差，均为兼容性考虑）：
  - 关键词路径用「进程内倒排索引 + 每 user 60s TTL 缓存」而不是 SQLite FTS5+jieba：
    生产后端可能是 MySQL（FTS5 不可用），且 jieba 不在依赖里。倒排索引用
    中文 bigram + 英文词，单 user 500 条以内索引耗时 <5ms，等效收益。
  - 向量路径懒同步：查询时对比 Qdrant 已有 payload 的 content_hash 与
    DB 当前行，缺的补嵌、变了的更新；不阻塞写路径。
  - 任何异常由调用方（memory_retriever）回退旧实现。
"""
from __future__ import annotations

import hashlib
import logging
import re
import threading
import time
from typing import Any, Callable, Optional

logger = logging.getLogger("starlearn.memory.v2")

RRF_K = 60
_KEYWORD_TTL = 60.0  # 秒
_CANDIDATES = 20  # 每路召回的候选数
_MAX_INDEX_ROWS = 500  # 每 user 最多索引的行数

_EN_WORD = re.compile(r"[a-zA-Z0-9_]{2,}")
_CJK = re.compile(r"[一-鿿]")


def _tokenize(text: str) -> set[str]:
    """中文 bigram + 英文单词（比单字重叠精确，比分词轻量）。"""
    text = text.lower()
    tokens = set(_EN_WORD.findall(text))
    cjk = _CJK.findall(text)
    if cjk:
        for ch in cjk:
            tokens.add(ch)
        for a, b in zip(cjk, cjk[1:]):
            tokens.add(a + b)
    return tokens


def _content_hash(content: str) -> str:
    return hashlib.md5(content.encode("utf-8")).hexdigest()[:16]


def _stable_point_id(memory_id) -> int:
    return int(hashlib.md5(f"mem:{memory_id}".encode("utf-8")).hexdigest()[:15], 16)


class MemorySearchV2:
    """双路召回记忆检索。可注入依赖做单测。"""

    def __init__(
        self,
        embedder: Any = None,
        qdrant_factory: Optional[Callable[[], Any]] = None,
        repo_factory: Optional[Callable[[], Any]] = None,
    ) -> None:
        self._embedder = embedder
        self._qdrant_factory = qdrant_factory
        self._repo_factory = repo_factory
        # {user_id: {"expires": t, "rows": [...], "index": {token: set(row_idx)}, "by_id": {...}}}
        self._kw_cache: dict[str, dict] = {}
        self._kw_lock = threading.Lock()
        self._vec_disabled = False  # Qdrant/embedder 不可用时一次性降级标记

    # ------------------------------------------------------------------
    # 依赖解析
    # ------------------------------------------------------------------

    def _get_embedder(self):
        if self._embedder is not None:
            return self._embedder
        from app.services.kb.embedder import get_embedder
        self._embedder = get_embedder()
        return self._embedder

    def _get_qdrant(self):
        if self._qdrant_factory is not None:
            return self._qdrant_factory()
        from app.services.kb.qdrant_client import QdrantClientSingleton
        return QdrantClientSingleton.get()

    def _get_repo(self):
        if self._repo_factory is not None:
            return self._repo_factory()
        from app.repositories.legacy.chat import DbPyChatRepository
        return DbPyChatRepository()

    @staticmethod
    def _collection_name(embedder) -> str:
        return f"mem_semantic_{embedder.dim}"

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    def search(
        self,
        user_id: str,
        query: str,
        limit: int = 8,
        min_confidence: float = 0.5,
        with_logs: bool = False,
    ):
        """返回 list[dict]（或 (list, logs)）。与旧实现的返回 dict 形状兼容。"""
        rows = self._user_rows(user_id)
        rows = [m for m in rows if float(m.get("confidence", 1.0)) >= min_confidence]
        if not rows or not query:
            return ([], []) if with_logs else []

        vec_hits: list[tuple[dict, int]] = []  # (row, rank0based)
        if self._vector_ok():
            try:
                vec_hits = self._vector_search(user_id, query, rows)
            except Exception as e:
                logger.info("[MemoryV2] 向量路径降级: %s", e)

        kw_hits: list[tuple[dict, int]] = self._keyword_search(query, rows)

        fused = self._rrf_fuse(vec_hits, kw_hits)
        top = fused[:limit]

        repo = self._get_repo()
        for m, _score, _paths in top:
            try:
                repo.bump_memory_access(int(m.get("id")))
            except Exception:
                pass

        memories = [m for m, _s, _p in top]
        if not with_logs:
            return memories
        logs = [
            {
                "memory_id": m.get("id"),
                "content": m.get("content", ""),
                "relevance_score": round(score, 4),
                "memory_type": m.get("memory_type", "fact"),
                "path": "+".join(paths) or "none",
            }
            for m, score, paths in top
        ]
        return memories, logs

    # ------------------------------------------------------------------
    # 数据源
    # ------------------------------------------------------------------

    def _user_rows(self, user_id: str) -> list[dict]:
        now = time.monotonic()
        with self._kw_lock:
            cached = self._kw_cache.get(user_id)
            if cached and now < cached["expires"]:
                return cached["rows"]
        rows = self._get_repo().get_memories(user_id, limit=_MAX_INDEX_ROWS)
        with self._kw_lock:
            index: dict[str, set[int]] = {}
            for i, m in enumerate(rows):
                for tok in _tokenize(m.get("content", "")):
                    index.setdefault(tok, set()).add(i)
            self._kw_cache[user_id] = {
                "expires": now + _KEYWORD_TTL,
                "rows": rows,
                "index": index,
            }
            # 防多 user 场景下缓存无限增长
            if len(self._kw_cache) > 256:
                stale = sorted(self._kw_cache.items(), key=lambda kv: kv[1]["expires"])[:64]
                for k, _v in stale:
                    self._kw_cache.pop(k, None)
        return rows

    def _keyword_search(self, query: str, rows: list[dict]) -> list[tuple[dict, int]]:
        # 对（可能已按 confidence 过滤的）rows 现算倒排索引；500 条以内 <5ms
        index: dict[str, set[int]] = {}
        for i, m in enumerate(rows):
            for tok in _tokenize(m.get("content", "")):
                index.setdefault(tok, set()).add(i)
        q_tokens = _tokenize(query)
        if not q_tokens:
            return []
        counts: dict[int, int] = {}
        for tok in q_tokens:
            for i in index.get(tok, ()):
                counts[i] = counts.get(i, 0) + 1
        ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:_CANDIDATES]
        return [(rows[i], rank) for rank, (i, _c) in enumerate(ranked)]

    # ------------------------------------------------------------------
    # 向量路径
    # ------------------------------------------------------------------

    def _vector_ok(self) -> bool:
        if self._vec_disabled:
            return False
        try:
            return self._get_embedder().is_semantic
        except Exception:
            return False

    def _vector_search(self, user_id: str, query: str, rows: list[dict]) -> list[tuple[dict, int]]:
        embedder = self._get_embedder()
        client = self._get_qdrant()
        name = self._collection_name(embedder)

        from qdrant_client.models import Filter, FieldCondition, MatchValue, PointStruct, VectorParams, Distance

        try:
            client.get_collection(name)
        except Exception:
            client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=embedder.dim, distance=Distance.COSINE),
            )

        # 懒同步：DB 行 vs 已有向量点
        current = {str(m.get("id")): m for m in rows}
        existing: dict[str, str] = {}
        offset = None
        while True:
            pts, offset = client.scroll(
                collection_name=name,
                scroll_filter=Filter(must=[FieldCondition(key="user_id", match=MatchValue(value=str(user_id)))]),
                limit=256,
                with_payload=True,
                offset=offset,
            )
            for p in pts:
                pid = str((p.payload or {}).get("memory_id", ""))
                if pid:
                    existing[pid] = (p.payload or {}).get("content_hash", "")
            if offset is None:
                break

        to_upsert = [
            (mid, m) for mid, m in current.items()
            if mid not in existing or existing[mid] != _content_hash(m.get("content", ""))
        ]
        if to_upsert:
            vectors = embedder.embed_batch([m.get("content", "") for _mid, m in to_upsert])
            points = [
                PointStruct(
                    id=_stable_point_id(mid),
                    vector=vectors[i],
                    payload={
                        "memory_id": mid,
                        "user_id": str(user_id),
                        "content": m.get("content", "")[:2000],
                        "content_hash": _content_hash(m.get("content", "")),
                    },
                )
                for i, (mid, m) in enumerate(to_upsert)
            ]
            client.upsert(collection_name=name, points=points)

        qvec = embedder.embed(query)
        result = client.query_points(
            collection_name=name,
            query=qvec,
            limit=_CANDIDATES,
            query_filter=Filter(must=[FieldCondition(key="user_id", match=MatchValue(value=str(user_id)))]),
            with_payload=True,
        ).points

        hits: list[tuple[dict, int]] = []
        for p in result.points:
            mid = str((p.payload or {}).get("memory_id", ""))
            row = current.get(mid)
            if row is None:
                continue  # 已删除的旧记忆，跳过
            if float(p.score or 0.0) < 0.30:
                continue
            hits.append((row, len(hits)))
        return hits

    # ------------------------------------------------------------------
    # 融合
    # ------------------------------------------------------------------

    @staticmethod
    def _rrf_fuse(
        vec_hits: list[tuple[dict, int]],
        kw_hits: list[tuple[dict, int]],
    ) -> list[tuple[dict, float, list[str]]]:
        """RRF(k=60) + 业务重排。返回 (row, score, paths) 降序。"""
        agg: dict[Any, dict] = {}
        for row, rank in vec_hits:
            key = row.get("id", row.get("content", ""))
            agg.setdefault(key, {"row": row, "rrf": 0.0, "paths": []})
            agg[key]["rrf"] += 1.0 / (RRF_K + rank + 1)
            if "vec" not in agg[key]["paths"]:
                agg[key]["paths"].append("vec")
        for row, rank in kw_hits:
            key = row.get("id", row.get("content", ""))
            agg.setdefault(key, {"row": row, "rrf": 0.0, "paths": []})
            agg[key]["rrf"] += 1.0 / (RRF_K + rank + 1)
            if "kw" not in agg[key]["paths"]:
                agg[key]["paths"].append("kw")

        out = []
        for item in agg.values():
            row = item["row"]
            # 业务重排：小幅加成（量级≈RRF 分差），只影响同档位排序
            score = item["rrf"]
            score += 0.004 * float(row.get("confidence", 1.0))
            score += 0.002 * min(int(row.get("access_count", 1)), 20) / 20.0
            if row.get("confirmed"):
                score += 0.003
            out.append((row, score, item["paths"]))
        out.sort(key=lambda t: t[1], reverse=True)
        return out


_singleton: MemorySearchV2 | None = None


def get_memory_search_v2() -> MemorySearchV2:
    global _singleton
    if _singleton is None:
        _singleton = MemorySearchV2()
    return _singleton


def reset_memory_search_v2_for_tests() -> None:
    global _singleton
    _singleton = None
