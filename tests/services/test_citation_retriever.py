"""CitationRetriever returns CitationHit dataclasses with must_cite=True."""
from app.services.kb.citation_retriever import CitationRetriever, CitationHit
from app.services.kb.qdrant_client import QdrantClientSingleton  # production vs injected; FakeVS used below


def test_citation_retriever_returns_tuples_with_must_cite_flag():
    class FakeVS:
        def similarity_search_with_score(self, q, k=5):
            return [
                ({"id": "KB-CON-0001", "title": "pythag", "content": "a²+b²=c²"}, 0.92),
                ({"id": "KB-CON-0002", "title": "trig", "content": "sin"}, 0.85),
            ]

    r = CitationRetriever(vector_store=FakeVS())
    hits = r.retrieve("勾股", top_k=2)
    assert len(hits) == 2
    assert all(isinstance(h, CitationHit) for h in hits)
    assert all(h.must_cite is True for h in hits)
    assert hits[0].node_id == "KB-CON-0001"