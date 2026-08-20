# -*- coding: utf-8 -*-
"""KB 语义检索（真 embedding 版，S1）。

对 main.KNOWLEDGE_BASE 的静态关键词匹配做语义增强：
  - 首次查询时把 KNOWLEDGE_BASE 全量条目（+ knowledge_node 表 best-effort）
    用真实 embedding 写入 Qdrant ``kb_semantic_{dim}`` collection
  - 检索 = query 向量 top-k，返回带出处/深链的命中
  - 三重降级：embedder 非语义 / Qdrant 不可用 / 索引失败 → 返回 []，
    调用方（ContextAggregator._fetch_rag）继续走 legacy 关键词路径

与 ingestion.py 的 ``knowledge_nodes`` collection（hash 伪向量）互不干扰：
真向量用独立 collection，按维度命名避免冲突。
"""
from __future__ import annotations

import hashlib
import logging
import threading
import time
from typing import Any, Callable, Optional

logger = logging.getLogger("starlearn.kb.semantic")

# Qdrant 连续失败后的冷却：期间不再尝试建索引/查询（保护请求延迟）
_FAILURE_COOLDOWN = 120.0


def _md5_int(text: str) -> int:
    return int(hashlib.md5(text.encode("utf-8")).hexdigest()[:15], 16)


class SemanticKB:
    """KNOWLEDGE_BASE 语义检索。线程安全；注入点供测试。"""

    def __init__(
        self,
        embedder: Any = None,
        qdrant_factory: Optional[Callable[[], Any]] = None,
        kb_loader: Optional[Callable[[], dict]] = None,
    ) -> None:
        self._embedder = embedder
        self._qdrant_factory = qdrant_factory
        self._kb_loader = kb_loader
        self._lock = threading.Lock()
        self._indexed_for: Optional[str] = None  # "dim:count" 建好的指纹
        self._failed_at = -_FAILURE_COOLDOWN

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

    def _load_kb(self) -> dict:
        if self._kb_loader is not None:
            return self._kb_loader() or {}
        try:
            from main import KNOWLEDGE_BASE
            return KNOWLEDGE_BASE
        except Exception:
            return {}

    # ------------------------------------------------------------------
    # 索引
    # ------------------------------------------------------------------

    def _docs(self) -> list[dict]:
        """KNOWLEDGE_BASE + knowledge_node 表合并为统一 doc 列表。"""
        docs: list[dict] = []
        for key, entry in (self._load_kb() or {}).items():
            docs.append({
                "key": f"kb:{key}",
                "title": key,
                "content": entry.get("content", ""),
                "source": entry.get("source", ""),
                "textbook": entry.get("textbook", ""),
                "chapterId": entry.get("chapterId", ""),
                "startPage": entry.get("startPage", 1),
            })
        # knowledge_node 表 best-effort（邻接表节点也是 L1 声明锚定的数据源）
        try:
            from app.db.orm_models import KnowledgeNode  # type: ignore
            from app.db.session import get_sync_session  # type: ignore
            with get_sync_session() as session:
                nodes = session.query(KnowledgeNode).limit(500).all()
                for n in nodes:
                    title = getattr(n, "title", "") or getattr(n, "name", "")
                    content = getattr(n, "content", "") or ""
                    if not content:
                        continue
                    docs.append({
                        "key": f"node:{getattr(n, 'id', title)}",
                        "title": str(title),
                        "content": str(content),
                        "source": "知识图谱",
                        "textbook": "",
                        "chapterId": "",
                        "startPage": 1,
                    })
        except Exception:
            pass  # 无 knowledge_node 表/ORM 未启用时静默跳过
        return [d for d in docs if d["content"]]

    def _ensure_index(self) -> bool:
        """确保 Qdrant collection 已按当前 provider 维度建好。失败返回 False。"""
        embedder = self._get_embedder()
        if not embedder.is_semantic:
            return False
        if time.monotonic() - self._failed_at < _FAILURE_COOLDOWN:
            return False

        docs = self._docs()
        fingerprint = f"{embedder.provider}:{embedder.dim}:{len(docs)}"
        if self._indexed_for == fingerprint:
            return True

        with self._lock:
            if self._indexed_for == fingerprint:
                return True
            try:
                self._build_collection(embedder, docs)
                self._indexed_for = fingerprint
                logger.info("[SemanticKB] 索引就绪: %s (%d 条)", fingerprint, len(docs))
                return True
            except Exception as e:
                self._failed_at = time.monotonic()
                logger.warning("[SemanticKB] 建索引失败，冷却 %.0fs: %s", _FAILURE_COOLDOWN, e)
                return False

    def _build_collection(self, embedder, docs: list[dict]) -> None:
        from qdrant_client.models import PointStruct, VectorParams, Distance

        client = self._get_qdrant()
        name = self._collection_name(embedder)
        texts = [f"{d['title']} {d['content']}" for d in docs]
        vectors = embedder.embed_batch(texts)

        try:
            client.get_collection(name)
        except Exception:
            client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=embedder.dim, distance=Distance.COSINE),
            )

        points = [
            PointStruct(
                id=_md5_int(d["key"]),
                vector=vectors[i],
                payload={
                    "key": d["key"],
                    "title": d["title"],
                    "content": d["content"][:2000],
                    "source": d["source"],
                    "textbook": d["textbook"],
                    "chapterId": d["chapterId"],
                    "startPage": d["startPage"],
                },
            )
            for i, d in enumerate(docs)
        ]
        # 小库直接全量 upsert，幂等
        client.upsert(collection_name=name, points=points)

    @staticmethod
    def _collection_name(embedder) -> str:
        return f"kb_semantic_{embedder.dim}"

    # ------------------------------------------------------------------
    # 检索
    # ------------------------------------------------------------------

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """语义检索。降级条件命中时返回 []。"""
        if not query or not self._ensure_index():
            return []
        embedder = self._get_embedder()
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchText

            client = self._get_qdrant()
            qvec = embedder.embed(query)
            hits = client.query_points(
                collection_name=self._collection_name(embedder),
                query=qvec,
                limit=top_k,
                with_payload=True,
            ).points
            out = []
            for h in hits:
                p = h.payload or {}
                # 阈值：bge 余弦 <0.35 基本无语义关联，直接丢弃
                score = float(h.score or 0.0)
                if score < 0.35:
                    continue
                out.append({
                    "key": p.get("key", ""),
                    "title": p.get("title", ""),
                    "content": p.get("content", ""),
                    "source": p.get("source", ""),
                    "deep_link": self._deep_link(p),
                    "score": round(score, 4),
                })
            return out
        except Exception as e:
            self._failed_at = time.monotonic()
            logger.warning("[SemanticKB] 检索失败: %s", e)
            return []

    @staticmethod
    def _deep_link(payload: dict) -> str:
        try:
            from main import build_deep_link
            return build_deep_link(
                payload.get("textbook", ""),
                payload.get("chapterId", ""),
                int(payload.get("startPage") or 1),
            )
        except Exception:
            return ""

    def is_available(self) -> bool:
        """是否具备语义检索条件（不触发实际建索引）。"""
        try:
            return self._get_embedder().is_semantic
        except Exception:
            return False


_singleton: SemanticKB | None = None


def get_semantic_kb() -> SemanticKB:
    global _singleton
    if _singleton is None:
        _singleton = SemanticKB()
    return _singleton


def reset_semantic_kb_for_tests() -> None:
    global _singleton
    _singleton = None
