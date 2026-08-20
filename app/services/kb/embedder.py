# -*- coding: utf-8 -*-
"""Embedding 服务（三级降级链）。

设计（2026-08-20 统一设计 S1）：
    主选: 本地 bge-small-zh-v1.5（sentence-transformers / FlagEmbedding，
          懒加载——未安装时跳过，不引入硬依赖）
    备选: MiniMax embedding API（OpenAI 兼容 /embeddings）
    保底: hash_embed（现有实现，无语义但链路不中断）

用法::

    from app.services.kb.embedder import get_embedder
    emb = get_embedder()
    vec = emb.embed("一元二次方程的配方法")
    emb.is_semantic   # False 时调用方应跳过向量检索路径
"""
from __future__ import annotations

import hashlib
import logging
import threading
import time
from collections import OrderedDict
from typing import Sequence

from app.core.feature_flags import embedding_provider_pref
from app.services.kb.deterministic_embedder import hash_embed

logger = logging.getLogger("starlearn.embedder")

# 语义 provider 失败后的冷却时间（秒）：期间不再重试，直接走保底。
_PROVIDER_RETRY_COOLDOWN = 300.0
# embedding 缓存上限（条）。进程内 LRU。
_CACHE_LIMIT = 4096
# API 超时（秒）
_API_TIMEOUT = 3.0


class EmbeddingService:
    """provider 链 embedding。线程安全；懒初始化。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._provider: str | None = None  # None = 未初始化
        self._model = None  # 本地模型对象
        self._dim: int | None = None
        self._failed_at: dict[str, float] = {}  # provider -> 最近失败时间
        self._cache: OrderedDict[str, list[float]] = OrderedDict()
        self._cache_lock = threading.Lock()

    # ------------------------------------------------------------------
    # 属性
    # ------------------------------------------------------------------

    @property
    def provider(self) -> str:
        """当前 provider 名：local / api / hash。触发懒初始化。"""
        if self._provider is None:
            self._init_provider()
        return self._provider or "hash"

    @property
    def dim(self) -> int:
        if self._dim is None:
            # 触发一次真实 embed 确定维度
            self.embed("dim_probe")
        return self._dim or 384

    @property
    def is_semantic(self) -> bool:
        """hash provider 无语义（SHA-256 雪崩），调用方据此跳过向量检索路径。"""
        return self.provider != "hash"

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    def embed(self, text: str) -> list[float]:
        """单条文本 → 向量（带 LRU 缓存）。"""
        if not text:
            text = " "
        key = f"{self.provider}:{len(text)}:{hashlib.md5(text.encode('utf-8')).hexdigest()}"
        with self._cache_lock:
            cached = self._cache.get(key)
            if cached is not None:
                self._cache.move_to_end(key)
                return cached

        vec = self.embed_batch([text])[0]
        with self._cache_lock:
            self._cache[key] = vec
            self._cache.move_to_end(key)
            while len(self._cache) > _CACHE_LIMIT:
                self._cache.popitem(last=False)
        return vec

    def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        """批量 embedding。失败时降级 hash（保底永不抛异常）。"""
        texts = [t if t else " " for t in texts]
        if not texts:
            return []
        provider = self.provider
        try:
            if provider == "local":
                return self._embed_local(texts)
            if provider == "api":
                return self._embed_api(texts)
        except Exception as e:
            logger.warning("[EmbeddingService] provider=%s 失败，降级 hash: %s", provider, e)
            self._mark_failed(provider)
            # 立即重新解析 provider（会降级）
            self._provider = None
            provider = self.provider
            if provider == "local":
                return self._embed_local(texts)
            if provider == "api":
                return self._embed_api(texts)
        return self._embed_hash(texts)

    # ------------------------------------------------------------------
    # provider 解析
    # ------------------------------------------------------------------

    def _init_provider(self) -> None:
        with self._lock:
            if self._provider is not None:
                return
            pref = embedding_provider_pref()
            if pref == "hash":
                self._provider = "hash"
                return
            chain = {
                "local": ["local", "api", "hash"],
                "api": ["api", "hash"],
                "auto": ["local", "api", "hash"],
            }[pref]
            now = time.monotonic()
            for name in chain:
                if name == "hash":
                    break
                if now - self._failed_at.get(name, -_PROVIDER_RETRY_COOLDOWN) < _PROVIDER_RETRY_COOLDOWN:
                    continue  # 冷却中，跳过
                if name == "local" and self._load_local_model() is not None:
                    self._provider = "local"
                    logger.info("[EmbeddingService] 使用本地 bge 模型: %s", self._local_model_name())
                    return
                if name == "api" and self._api_configured():
                    self._provider = "api"
                    logger.info("[EmbeddingService] 使用 MiniMax embedding API")
                    return
            self._provider = "hash"
            logger.info("[EmbeddingService] 使用 hash_embed（无语义，仅保底）")

    def _mark_failed(self, provider: str) -> None:
        self._failed_at[provider] = time.monotonic()

    @staticmethod
    def _local_model_name() -> str:
        import os
        return os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")

    def _load_local_model(self):
        """懒加载本地模型。未安装依赖/下载失败 → None（不抛异常）。"""
        if self._model is not None:
            return self._model
        name = self._local_model_name()
        model = None
        try:
            try:
                from sentence_transformers import SentenceTransformer  # type: ignore
                model = SentenceTransformer(name)
            except ImportError:
                from FlagEmbedding import FlagModel  # type: ignore
                model = FlagModel(name, use_fp16=False)
        except Exception as e:
            logger.info("[EmbeddingService] 本地模型不可用(%s): %s", name, e)
            return None
        self._model = model
        return model

    @staticmethod
    def _api_configured() -> bool:
        try:
            from config.config import settings
            return bool(settings.minimax_api_key)
        except Exception:
            return False

    # ------------------------------------------------------------------
    # providers
    # ------------------------------------------------------------------

    def _embed_local(self, texts: list[str]) -> list[list[float]]:
        model = self._load_local_model()
        if model is None:
            raise RuntimeError("local model unavailable")
        name = self._local_model_name()
        if name.lower().startswith("baai/bge"):
            # bge 系列官方推荐：查询侧加检索指令（对称检索可不加）
            vecs = model.encode(texts, normalize_embeddings=True)
        else:
            vecs = model.encode(texts)
        out = [self._normalize([float(x) for x in v]) for v in vecs]
        if self._dim is None:
            self._dim = len(out[0])
        return out

    def _embed_api(self, texts: list[str]) -> list[list[float]]:
        import httpx
        from config.config import settings

        api_model = None
        try:
            import os
            api_model = os.getenv("EMBEDDING_API_MODEL") or None
        except Exception:
            pass
        if not api_model:
            api_model = getattr(settings, "minimax_embedding_model", None) or "embo-01"

        # OpenAI 兼容格式；兼容 MiniMax 原生 {"texts": [...]} 响应/请求差异
        payload = {"model": api_model, "input": list(texts)}
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.minimax_api_key}",
        }
        with httpx.Client(timeout=_API_TIMEOUT) as client:
            resp = client.post(
                f"{settings.minimax_api_url.rstrip('/')}/embeddings",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        # OpenAI 格式: {"data": [{"embedding": [...]}]}
        # MiniMax 原生: {"vectors": [[...]]}
        vectors = None
        if isinstance(data, dict):
            if isinstance(data.get("data"), list):
                vectors = [item.get("embedding") for item in data["data"] if isinstance(item, dict)]
            elif isinstance(data.get("vectors"), list):
                vectors = data["vectors"]
        if not vectors or len(vectors) != len(texts):
            raise RuntimeError(f"embedding API 响应格式异常: {str(data)[:200]}")
        out = [self._normalize([float(x) for x in v]) for v in vectors]
        if self._dim is None:
            self._dim = len(out[0])
        return out

    def _embed_hash(self, texts: list[str]) -> list[list[float]]:
        if self._dim is None:
            self._dim = 384  # 与 deterministic_embedder.EMBEDDING_DIM 一致
        return [hash_embed(t) for t in texts]

    # ------------------------------------------------------------------
    # 工具
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize(vec: list[float]) -> list[float]:
        norm = sum(x * x for x in vec) ** 0.5
        if norm < 1e-12:
            return vec
        return [x / norm for x in vec]


_singleton: EmbeddingService | None = None
_singleton_lock = threading.Lock()


def get_embedder() -> EmbeddingService:
    """进程级单例。"""
    global _singleton
    if _singleton is None:
        with _singleton_lock:
            if _singleton is None:
                _singleton = EmbeddingService()
    return _singleton


def reset_embedder_for_tests() -> None:
    """测试用：重置单例与 provider 状态。"""
    global _singleton
    with _singleton_lock:
        _singleton = None
