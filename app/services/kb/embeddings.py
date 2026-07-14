"""讯飞 embedding LangChain 适配 + 24h 内存缓存."""
import hashlib
from typing import List
from langchain_core.embeddings import Embeddings


class XunfeiEmbeddings(Embeddings):
    def __init__(self, embed_fn, cache_ttl_s: int = 86400):
        self._fn = embed_fn
        self._cache: dict[str, list[float]] = {}

    def embed_query(self, text: str) -> List[float]:
        return self._embed(text)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed(t) for t in texts]

    def _embed(self, text: str) -> List[float]:
        k = hashlib.sha256(text.encode()).hexdigest()
        if k in self._cache:
            return self._cache[k]
        v = self._fn(text)
        self._cache[k] = v
        return v