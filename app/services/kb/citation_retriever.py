"""VectorStoreRetriever subclass returning CitationHit(node_id, score, must_cite=True).

Used by the Socratic / citation pipeline to surface KB nodes that must be
attributed in any LLM answer. The retriever is decoupled from any concrete
vector store — callers inject an object exposing
``similarity_search_with_score(query, k=...)`` (langchain ``VectorStore``,
``Qdrant`` wrapper, or a fake for tests).

The ``must_cite=True`` flag is the contract the anti-hallucination guard
in S3 relies on: every hit returned here is a citation the answer must
include.
"""
from dataclasses import dataclass
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from typing import List


@dataclass(frozen=True)
class CitationHit:
    node_id: str
    title: str
    content: str
    score: float
    must_cite: bool = True


class CitationRetriever(BaseRetriever):
    vector_store: object  # injected; .similarity_search_with_score(query, k=...)

    def _get_relevant_documents(self, query: str, *, run_manager=None) -> List[Document]:
        raise NotImplementedError("Use retrieve() directly for typed hits")

    def retrieve(self, query: str, top_k: int = 5) -> List[CitationHit]:
        raw = self.vector_store.similarity_search_with_score(query, k=top_k)
        hits = []
        for d, score in raw:
            hits.append(CitationHit(
                node_id=d.get("id") if isinstance(d, dict) else d.metadata.get("id"),
                title=d.get("title") if isinstance(d, dict) else d.metadata.get("title", ""),
                content=d.get("content") if isinstance(d, dict) else d.page_content,
                score=float(score),
            ))
        return hits